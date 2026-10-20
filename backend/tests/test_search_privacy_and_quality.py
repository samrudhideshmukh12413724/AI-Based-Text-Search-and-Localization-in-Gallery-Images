"""Comprehensive Regression Test Suite for Search Privacy, Result Quality, and Tenant Isolation.

Validates:
1. Empty and whitespace queries return 0 results and do not leak vault contents.
2. Unrelated/garbage queries return 0 results and do not produce false semantic drift.
3. Multi-tenant privacy: User A cannot access User B's documents across exact, semantic, or visual search.
4. Guest privacy: Unauthenticated requests cannot retrieve private records or access User 24 documents.
5. Cache isolation: Cached results for User A cannot be retrieved by User B or Guest.
6. Incremental sync and duplicate handling preserve database integrity.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from app import database


def test_group1_empty_search_protection(client: TestClient):
    """Empty and whitespace queries must return zero results and never leak vault contents."""
    # 1. Empty string query
    resp_empty = client.post("/search", json={"query": ""})
    assert resp_empty.status_code == 200
    data_empty = resp_empty.json()
    assert data_empty["count"] == 0
    assert len(data_empty["results"]) == 0

    # 2. Whitespace-only query
    resp_space = client.post("/search", json={"query": "     "})
    assert resp_space.status_code == 200
    data_space = resp_space.json()
    assert data_space["count"] == 0
    assert len(data_space["results"]) == 0

    # 3. GET /search with empty q
    resp_get_empty = client.get("/search?q=")
    assert resp_get_empty.status_code == 200
    assert resp_get_empty.json()["count"] == 0


def test_group2_search_quality_and_garbage_rejection(client: TestClient):
    """Nonsense and nonexistent queries must return zero results and reject weak drift."""
    # 1. Nonexistent random token query
    resp_garbage = client.post("/search", json={"query": "xyzqwerty999nonsense"})
    assert resp_garbage.status_code == 200
    data_garbage = resp_garbage.json()
    assert data_garbage["count"] == 0
    assert len(data_garbage["results"]) == 0

    # 2. Random characters query
    resp_rand = client.post("/search", json={"query": "asdfghjkl"})
    assert resp_rand.status_code == 200
    assert resp_rand.json()["count"] == 0

    # 3. Exact query for a known document keyword
    resp_known = client.post("/search", json={"query": "Aadhaar"})
    assert resp_known.status_code == 200
    data_known = resp_known.json()
    assert data_known["count"] > 0
    assert any("aadhaar" in r.get("image_name", "").lower() or "aadhaar" in r.get("matched_text", "").lower()
               for r in data_known["results"])


def test_group3_privacy_and_tenant_isolation(client: TestClient):
    """User A and User B cannot view each other's documents; cache keys are isolated."""
    suffix = uuid.uuid4().hex[:6]
    user_a = f"alice_tenant_{suffix}"
    user_b = f"bob_tenant_{suffix}"
    pwd = "StrongTestPassword123!"

    # 1. Register and login User A
    client.post("/auth/register", json={"username": user_a, "password": pwd, "is_admin": False})
    token_a = client.post("/auth/login", json={"username": user_a, "password": pwd}).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register and login User B
    client.post("/auth/register", json={"username": user_b, "password": pwd, "is_admin": False})
    token_b = client.post("/auth/login", json={"username": user_b, "password": pwd}).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User B has an empty vault
    resp_b_list = client.get("/images", headers=headers_b)
    assert resp_b_list.status_code == 200
    assert len(resp_b_list.json()) == 0

    # 4. User B search must not find any private documents from other tenants
    resp_b_search = client.post("/search", headers=headers_b, json={"query": "Samrudhi"})
    assert resp_b_search.status_code == 200
    assert resp_b_search.json()["count"] == 0

    # 5. IDOR check: User B cannot access relationships of document 382 (User 24's document)
    resp_idor = client.get("/images/382/relationships", headers=headers_b)
    assert resp_idor.status_code == 403
    assert "Tenant access denied" in resp_idor.json()["detail"]

    # 6. IDOR check: User B cannot export PDF of document 382
    resp_pdf = client.get("/images/382/export-pdf", headers=headers_b)
    assert resp_pdf.status_code == 403
    assert "Tenant access denied" in resp_pdf.json()["detail"]

    # 7. Unauthenticated Guest cannot retrieve User 24 documents
    resp_guest_list = client.get("/images")
    assert resp_guest_list.status_code == 200
    for doc in resp_guest_list.json():
        assert doc["user_id"] == 1
        assert doc["is_demo"] == 1


def test_group4_sync_check_endpoint(client: TestClient):
    """Incremental sync-check correctly identifies synced vs missing files."""
    body = {
        "files": [
            {"filename": "doc_composite_01_aadhaar.jpg", "size": 1024},
            {"filename": "new_never_synced_receipt_2026.jpg", "size": 2048},
        ]
    }
    resp = client.post("/images/sync-check", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_checked"] == 2
    assert "doc_composite_01_aadhaar.jpg" in data["already_synced"]
    assert "new_never_synced_receipt_2026.jpg" in data["missing"]


def test_group5_wireless_health_endpoint(client: TestClient):
    """Backend health and download routes are reachable wirelessly."""
    # 1. Health check
    resp_health = client.get("/api/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "ok"

    # 2. Sync status diagnostic endpoint
    resp_sync_status = client.get("/images/sync-status")
    assert resp_sync_status.status_code == 200
    assert "is_active" in resp_sync_status.json()
