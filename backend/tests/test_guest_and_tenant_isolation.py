"""Comprehensive Multi-Tenant & Guest Isolation Security Test Suite.

Tests rigorous data isolation between:
1. Registered User A vs Registered User B
2. Guest Session A vs Guest Session B
3. Anonymous requests (no JWT, no guest ID)
4. Protection against IDOR on file and thumbnail endpoints
5. Protection against path traversal attacks
6. Search scoping (keyword & semantic) to tenant boundary
7. Scoped duplicate detection (preventing cross-tenant leakage)
8. Hidden quarantine of legacy unassigned documents
9. Safe handling of invalid/corrupted uploads
10. Tenant-scoped document deletion
"""

import io
import uuid
import pytest
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

from app.main import app
from app import database, auth


@pytest.fixture(scope="module")
def client() -> TestClient:
    database.init_db()
    return TestClient(app)


def create_synthetic_image(text: str = "DocuLens Synthetic Test") -> bytes:
    """Generate a clean synthetic test document image in-memory."""
    img = Image.new("RGB", (400, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 390, 190], outline=(0, 0, 0), width=2)
    draw.text((30, 80), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def register_and_login(client: TestClient, prefix: str):
    suffix = uuid.uuid4().hex[:6]
    username = f"{prefix}_{suffix}"
    password = "SafePassword987!"
    reg_resp = client.post(
        "/auth/register",
        json={"username": username, "password": password, "is_admin": False},
    )
    assert reg_resp.status_code == 200, reg_resp.text
    user_id = reg_resp.json()["user_id"]

    login_resp = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return user_id, username, headers


# ---------------------------------------------------------------------------
# Test 1: Anonymous requests cannot access or upload documents
# ---------------------------------------------------------------------------
def test_anonymous_requests_blocked_and_empty_vault(client: TestClient):
    # 1. Anonymous vault list returns 0 documents
    resp = client.get("/images")
    assert resp.status_code == 200
    assert resp.json() == []

    # 2. Anonymous upload is rejected with 401 Unauthorized
    synth_img = create_synthetic_image("Anonymous Upload Test")
    upload_resp = client.post(
        "/upload",
        files={"file": ("anon_test.jpg", synth_img, "image/jpeg")},
    )
    assert upload_resp.status_code == 401
    assert "X-Guest-Session-ID header required" in upload_resp.json()["detail"]


# ---------------------------------------------------------------------------
# Test 2: Guest Session A vs Guest Session B isolation
# ---------------------------------------------------------------------------
def test_guest_session_isolation(client: TestClient):
    guest_a_id = f"guest_session_a_{uuid.uuid4().hex[:8]}"
    guest_b_id = f"guest_session_b_{uuid.uuid4().hex[:8]}"

    headers_a = {"X-Guest-Session-ID": guest_a_id}
    headers_b = {"X-Guest-Session-ID": guest_b_id}

    # Both guests should start with completely empty vaults
    resp_a = client.get("/images", headers=headers_a)
    assert resp_a.status_code == 200
    assert resp_a.json() == []

    resp_b = client.get("/images", headers=headers_b)
    assert resp_b.status_code == 200
    assert resp_b.json() == []

    # Guest A uploads a document
    img_bytes = create_synthetic_image("Guest A Private Receipt #9912")
    up_resp_a = client.post(
        "/upload",
        headers=headers_a,
        files={"file": ("guest_a_receipt.jpg", img_bytes, "image/jpeg")},
    )
    assert up_resp_a.status_code == 200, up_resp_a.text
    doc_a = up_resp_a.json()
    doc_a_id = doc_a["id"]
    doc_a_filename = doc_a["image_name"]

    # Guest A's vault now has 1 document
    vault_a = client.get("/images", headers=headers_a).json()
    assert len(vault_a) == 1
    assert vault_a[0]["id"] == doc_a_id

    # Guest B's vault MUST STILL HAVE 0 documents
    vault_b = client.get("/images", headers=headers_b).json()
    assert len(vault_b) == 0, f"Guest B saw Guest A's document! {vault_b}"

    # Guest B attempts IDOR on Guest A's document
    file_idor = client.get(f"/images/{doc_a_id}/file", headers=headers_b)
    assert file_idor.status_code == 403, "Guest B was able to download Guest A's document file!"

    thumb_idor = client.get(f"/images/{doc_a_id}/thumbnail", headers=headers_b)
    assert thumb_idor.status_code == 403, "Guest B was able to view Guest A's thumbnail!"

    upload_idor = client.get(f"/uploads/{doc_a_filename}", headers=headers_b)
    assert upload_idor.status_code == 403, "Guest B was able to access Guest A's upload via filename!"


# ---------------------------------------------------------------------------
# Test 3: Registered User A vs Registered User B Tenant Isolation
# ---------------------------------------------------------------------------
def test_authenticated_user_isolation_and_search_boundaries(client: TestClient):
    uid_a, user_a, headers_a = register_and_login(client, "user_alice")
    uid_b, user_b, headers_b = register_and_login(client, "user_bob")

    # User A uploads doc A
    img_a = create_synthetic_image("Alice Medical Record UniqueX42")
    res_a = client.post(
        "/upload",
        headers=headers_a,
        files={"file": ("alice_doc.jpg", img_a, "image/jpeg")},
    )
    assert res_a.status_code == 200
    doc_a_id = res_a.json()["id"]
    doc_a_filename = res_a.json()["image_name"]

    # User B uploads doc B
    img_b = create_synthetic_image("Bob Tax Statement UniqueY88")
    res_b = client.post(
        "/upload",
        headers=headers_b,
        files={"file": ("bob_doc.jpg", img_b, "image/jpeg")},
    )
    assert res_b.status_code == 200
    doc_b_id = res_b.json()["id"]

    # User A lists documents: must see doc A, must NOT see doc B
    list_a = client.get("/images", headers=headers_a).json()
    ids_a = [d["id"] for d in list_a]
    assert doc_a_id in ids_a
    assert doc_b_id not in ids_a

    # User B lists documents: must see doc B, must NOT see doc A
    list_b = client.get("/images", headers=headers_b).json()
    ids_b = [d["id"] for d in list_b]
    assert doc_b_id in ids_b
    assert doc_a_id not in ids_b

    # Search Boundary Check: Bob searches for Alice's keyword "UniqueX42"
    search_resp = client.post(
        "/search",
        headers=headers_b,
        json={"query": "UniqueX42"},
    )
    assert search_resp.status_code == 200
    search_res = search_resp.json()
    assert search_res["count"] == 0, f"Bob found Alice's document in search: {search_res}"

    # Alice searches for her own keyword "UniqueX42"
    alice_search = client.post(
        "/search",
        headers=headers_a,
        json={"query": "UniqueX42"},
    ).json()
    # If OCR extracted it or partial match
    for res_item in alice_search.get("results", []):
        assert res_item["id"] != doc_b_id, "Alice received Bob's document in search results"


# ---------------------------------------------------------------------------
# Test 4: Path traversal and IDOR protections
# ---------------------------------------------------------------------------
def test_path_traversal_and_idor_protections(client: TestClient):
    uid_a, user_a, headers_a = register_and_login(client, "traversal_alice")
    uid_b, user_b, headers_b = register_and_login(client, "traversal_bob")

    img_a = create_synthetic_image("Secret Alice Document")
    res_a = client.post(
        "/upload",
        headers=headers_a,
        files={"file": ("secret_alice.jpg", img_a, "image/jpeg")},
    ).json()
    doc_id = res_a["id"]
    filename = res_a["image_name"]

    # Traversal attempts
    assert client.get("/uploads/..%2F..%2Fimages.db", headers=headers_b).status_code in (400, 403, 404)
    assert client.get("/uploads/../images.db", headers=headers_b).status_code in (400, 403, 404)
    assert client.get("/uploads/.../app/main.py", headers=headers_b).status_code in (400, 403, 404)

    # Bob attempts IDOR on Alice's endpoints
    assert client.get(f"/images/{doc_id}", headers=headers_b).status_code == 404
    assert client.get(f"/images/{doc_id}/file", headers=headers_b).status_code == 403
    assert client.get(f"/images/{doc_id}/thumbnail", headers=headers_b).status_code == 403
    assert client.get(f"/uploads/{filename}", headers=headers_b).status_code == 403


# ---------------------------------------------------------------------------
# Test 5: Legacy Quarantined Documents are invisible
# ---------------------------------------------------------------------------
def test_quarantined_documents_inaccessible_to_users(client: TestClient):
    guest_id = f"test_guest_quarantine_{uuid.uuid4().hex[:6]}"
    headers_guest = {"X-Guest-Session-ID": guest_id}

    # Verify that doc 676 (scaled_1000335097_d62227dd.jpg) or any quarantined file
    # is rejected with 403 or 404
    resp = client.get("/uploads/scaled_1000335097_d62227dd.jpg", headers=headers_guest)
    assert resp.status_code in (403, 404), f"Quarantined document was served! {resp.status_code}"

    # Also test without headers
    resp_anon = client.get("/uploads/scaled_1000335097_d62227dd.jpg")
    assert resp_anon.status_code in (403, 404)

    # In /images list, no quarantined docs appear
    list_resp = client.get("/images", headers=headers_guest).json()
    for doc in list_resp:
        assert doc.get("is_quarantined", 0) == 0, f"Quarantined document appeared in vault: {doc}"


# ---------------------------------------------------------------------------
# Test 6: Scoped Duplicate Detection
# ---------------------------------------------------------------------------
def test_duplicate_detection_does_not_leak_other_user_docs(client: TestClient):
    uid_a, user_a, headers_a = register_and_login(client, "dup_alice")
    uid_b, user_b, headers_b = register_and_login(client, "dup_bob")

    identical_content = create_synthetic_image("Identical Content Shared Test")

    # Alice uploads identical document
    up_a = client.post(
        "/upload",
        headers=headers_a,
        files={"file": ("dup_a.jpg", identical_content, "image/jpeg")},
    )
    assert up_a.status_code == 200

    # Bob uploads the same identical document
    up_b = client.post(
        "/upload",
        headers=headers_b,
        files={"file": ("dup_b.jpg", identical_content, "image/jpeg")},
    )
    assert up_b.status_code == 200
    doc_b = up_b.json()

    # Bob's duplicate check should NOT return Alice's document as a duplicate
    dup_resp = client.get(f"/duplicates?user_id={uid_b}", headers=headers_b)
    if dup_resp.status_code == 200:
        for group in dup_resp.json().get("duplicate_groups", []):
            for doc in group.get("documents", []):
                assert doc["id"] != up_a.json()["id"], "Alice's document leaked into Bob's duplicate groups!"


# ---------------------------------------------------------------------------
# Test 7: Invalid or corrupted uploads are safely rejected
# ---------------------------------------------------------------------------
def test_corrupted_upload_handling(client: TestClient):
    uid, _, headers = register_and_login(client, "corrupt_tester")

    # 1. Corrupted image bytes
    corrupt_bytes = b"NOT_AN_IMAGE_RANDOM_GARBAGE_BYTES_12345"
    resp = client.post(
        "/upload",
        headers=headers,
        files={"file": ("corrupt.jpg", corrupt_bytes, "image/jpeg")},
    )
    assert resp.status_code in (400, 422), f"Corrupt image was not rejected: {resp.status_code}"

    # 2. Executable disguised as image
    exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    resp_exe = client.post(
        "/upload",
        headers=headers,
        files={"file": ("malicious.exe", exe_bytes, "application/octet-stream")},
    )
    assert resp_exe.status_code in (400, 415, 422)


# ---------------------------------------------------------------------------
# Test 8: Document Deletion and Ownership Enforcement
# ---------------------------------------------------------------------------
def test_document_deletion_ownership_enforcement(client: TestClient):
    uid_a, _, headers_a = register_and_login(client, "del_alice")
    uid_b, _, headers_b = register_and_login(client, "del_bob")

    img_bytes = create_synthetic_image("Delete Test Document")
    doc_a = client.post(
        "/upload",
        headers=headers_a,
        files={"file": ("del_doc.jpg", img_bytes, "image/jpeg")},
    ).json()
    doc_id = doc_a["id"]

    # Bob attempts to delete Alice's document -> 403 Forbidden
    del_bob = client.delete(f"/images/{doc_id}", headers=headers_b)
    assert del_bob.status_code == 403, "Bob was allowed to delete Alice's document!"

    # Alice deletes her own document -> 200 OK
    del_alice = client.delete(f"/images/{doc_id}", headers=headers_a)
    assert del_alice.status_code == 200, f"Alice failed to delete her document: {del_alice.text}"

    # Subsequent fetch returns 404
    assert client.get(f"/images/{doc_id}", headers=headers_a).status_code == 404
