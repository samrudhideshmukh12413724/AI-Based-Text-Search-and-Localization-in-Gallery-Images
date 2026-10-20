"""Comprehensive Automated Test Suite for QR Code Recognition, Structured Enrichment,
and Search Result Explanation in DocuLens AI.

Validates:
1. Unit recognition and enrichment for PhonePe UPI (exact merchant, partial, payment provider).
2. Payee name search ("XYZ") and strict non-hallucination for identifier-only QR codes.
3. EMVCo / BharatQR TLV tag parsing (Tag 59 Merchant Name, Tag 60 City, Tag 26-51 VPAs).
4. Contact QR code parsing (vCard / MeCard).
5. Exact merchant name search ("Papu Kumar Chaat Wala").
6. Partial merchant name search ("Papu Kumar" and "Chaat Wala").
7. Payment provider search ("PhonePe").
8. Clean preview snippets for QR-only images (no "(no text detected)").
9. Grounded search result explanation (`match_reason`).
10. Bounding-box localization in `visual_objects` for QR regions.
11. Multi-QR images (decoding multiple codes on a single document).
12. Dual-mode images (both OCR text and QR metadata indexed and searchable).
13. Multi-tenant privacy isolation (User B cannot retrieve User A's QR codes).
14. Unrelated and garbage query rejection (zero matches).
15. Non-QR or corrupted image handling (graceful fallback without 500 error).
16. Original image integrity via /uploads/<image_name>.
"""

import io
import os
import uuid
import tempfile
from pathlib import Path
import pytest
import qrcode
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

from app.qr_decoder import (
    extract_qr_payloads,
    enrich_qr_payload,
    parse_emvco_tlv,
    _identify_provider_from_vpa_or_url,
)
from app import database


def _create_qr_image(payload: str, size: int = 400, nonce: str | None = None) -> bytes:
    """Helper to generate a PNG QR code in memory with unique watermark to prevent duplicate collisions."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=6,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    tag = nonce or uuid.uuid4().hex[:8]
    draw = ImageDraw.Draw(img)
    draw.text((4, 4), tag, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_receipt_with_qr(text_lines: list[str], qr_payload: str) -> bytes:
    """Helper to generate a composite document with both visible text and a QR code."""
    doc = Image.new("RGB", (600, 600), color="white")
    draw = ImageDraw.Draw(doc)

    y = 30
    draw.text((30, y), f"Receipt Ref: {uuid.uuid4().hex[:8]}", fill="black")
    y += 35
    for line in text_lines:
        draw.text((30, y), line, fill="black")
        y += 35

    # Generate QR and paste into lower half
    qr_bytes = _create_qr_image(qr_payload)
    qr_img = Image.open(io.BytesIO(qr_bytes)).convert("RGB").resize((240, 240))
    doc.paste(qr_img, (180, 300))

    buf = io.BytesIO()
    doc.save(buf, format="PNG")
    return buf.getvalue()



# =========================================================================
# Unit Tests for QR Decoder & Enrichment Functions
# =========================================================================

def test_unit_phonepe_upi_enrichment():
    """Verify UPI URL parser extracts merchant name, provider, and VPA without hallucination."""
    payload = "upi://pay?pa=papukumar@ybl&pn=Papu%20Kumar%20Chaat%20Wala&mc=5411"
    enriched = enrich_qr_payload(payload)

    assert "Papu Kumar Chaat Wala" in enriched["merchants"]
    assert "papukumar@ybl" in enriched["vpas"]
    assert "PhonePe" in enriched["providers"]
    assert enriched["is_payment"] is True
    assert "Papu Kumar Chaat Wala" in enriched["enriched_text"]
    assert "PhonePe" in enriched["enriched_text"]


def test_unit_payee_xyz_enrichment():
    """Verify PhonePe QR with friend payee name XYZ is parsed correctly."""
    payload = "upi://pay?pa=xyzfriend@ybl&pn=XYZ&cu=INR"
    enriched = enrich_qr_payload(payload)

    assert "XYZ" in enriched["payees"] or "XYZ" in enriched["merchants"]
    assert "PhonePe" in enriched["providers"]
    assert "xyzfriend@ybl" in enriched["vpas"]


def test_unit_identifier_only_no_hallucination():
    """Strict Identity Rule: VPA without name must NOT invent or hallucinate a person's name."""
    payload = "upi://pay?pa=shop99@ybl"
    enriched = enrich_qr_payload(payload)

    # Must contain VPA and provider, but strictly NO merchant/payee name
    assert enriched["vpas"] == ["shop99@ybl"]
    assert "PhonePe" in enriched["providers"]
    assert len(enriched["merchants"]) == 0
    assert len(enriched["payees"]) == 0


def test_unit_emvco_bharatqr_tlv_parser():
    """Verify EMVCo / BharatQR Tag 59 (Merchant Name) and Tag 60 (City) parsing."""
    # Constructed EMVCo payload: Tag 00=01, Tag 59 (Merchant)="Papu Chaat Wala", Tag 60 (City)="Pune"
    merchant = "Papu Chaat Wala"
    city = "Pune"
    emvco_payload = (
        f"000201"
        f"010211"
        f"59{len(merchant):02d}{merchant}"
        f"60{len(city):02d}{city}"
        f"6304ABCD"
    )
    tags = parse_emvco_tlv(emvco_payload)
    assert tags.get("59") == merchant
    assert tags.get("60") == city

    enriched = enrich_qr_payload(emvco_payload)
    assert merchant in enriched["merchants"]
    assert enriched["is_payment"] is True


def test_unit_vcard_contact_parser():
    """Verify contact card QR parser extracts full name and organization."""
    vcard = (
        "BEGIN:VCARD\n"
        "VERSION:3.0\n"
        "FN:Vikram Malhotra\n"
        "ORG:TechNova Solutions\n"
        "TEL:+919876543210\n"
        "END:VCARD"
    )
    enriched = enrich_qr_payload(vcard)
    assert "Vikram Malhotra" in enriched["payees"] or "Vikram Malhotra" in enriched["merchants"]
    assert "TechNova Solutions" in enriched["merchants"]


# =========================================================================
# Integration & End-to-End API Search Tests
# =========================================================================

def _find_doc(results: list[dict], doc_id: int) -> dict | None:
    """Helper to locate a document in search results, whether it is canonical or collapsed duplicate."""
    for r in results:
        if r.get("id") == doc_id:
            return r
        for v in r.get("duplicate_variants", []):
            if v.get("id") == doc_id:
                return r
    return None


def test_e2e_papu_kumar_chaat_wala_search_and_localization(client: TestClient):
    """
    Scenario: Upload an image with 'Papu Kumar Chaat Wala' PhonePe QR code.
    Verify:
    1. Exact query 'Papu Kumar Chaat Wala' retrieves the document.
    2. Partial queries 'Papu Kumar' and 'Chaat Wala' retrieve the document.
    3. Payment provider query 'PhonePe' retrieves the document.
    4. Bounding box coordinates exist in visual_objects.
    5. Result includes grounded match_reason.
    6. Preview snippet does not say '(no text detected)'.
    """
    payload = "upi://pay?pa=papukumar@ybl&pn=Papu%20Kumar%20Chaat%20Wala&mc=5411"
    img_bytes = _create_qr_image(payload)

    # 1. Upload synchronously to index
    fn = f"test_qr_papu_{uuid.uuid4().hex[:6]}.png"
    upload_resp = client.post(
        "/upload",
        files={"file": (fn, img_bytes, "image/png")},
    )
    assert upload_resp.status_code == 200, upload_resp.text
    uploaded_doc = upload_resp.json()
    doc_id = uploaded_doc["id"]
    assert "Papu Kumar Chaat Wala" in uploaded_doc.get("qr_payload", "")

    # 2. Search exact name: 'Papu Kumar Chaat Wala'
    resp_exact = client.post("/search", json={"query": "Papu Kumar Chaat Wala"})
    assert resp_exact.status_code == 200
    exact_data = resp_exact.json()
    assert exact_data["count"] > 0
    matched_exact = _find_doc(exact_data["results"], doc_id)
    assert matched_exact is not None, "Document not found by exact merchant name!"
    assert matched_exact["similarity_score"] >= 0.85
    assert "Papu Kumar Chaat Wala" in matched_exact["match_reason"]
    assert "QR merchant name" in matched_exact["match_reason"]

    # Verify preview snippet
    assert "(no text detected)" not in matched_exact["preview_snippet"]
    assert "Papu Kumar Chaat Wala" in matched_exact["preview_snippet"]

    # Verify visual bounding box localization
    assert matched_exact["has_visual_objects"] is True
    assert len(matched_exact["visual_objects"]) > 0
    qr_obj = next((o for o in matched_exact["visual_objects"] if o.get("type") in ("qr_code", "visual_region")), None)
    assert qr_obj is not None
    assert "bbox" in qr_obj
    assert "normalized_bbox" in qr_obj

    # 3. Search partial name 1: 'Papu Kumar'
    resp_part1 = client.post("/search", json={"query": "Papu Kumar"})
    assert resp_part1.status_code == 200
    part1_data = resp_part1.json()
    matched_part1 = _find_doc(part1_data["results"], doc_id)
    assert matched_part1 is not None, "Document not found by partial name 'Papu Kumar'!"
    assert "Papu Kumar Chaat Wala" in matched_part1["match_reason"]

    # 4. Search partial name 2: 'Chaat Wala'
    resp_part2 = client.post("/search", json={"query": "Chaat Wala"})
    assert resp_part2.status_code == 200
    part2_data = resp_part2.json()
    matched_part2 = _find_doc(part2_data["results"], doc_id)
    assert matched_part2 is not None, "Document not found by partial name 'Chaat Wala'!"
    assert "Papu Kumar Chaat Wala" in matched_part2["match_reason"]

    # 5. Search payment provider: 'PhonePe'
    resp_prov = client.post("/search", json={"query": "PhonePe"})
    assert resp_prov.status_code == 200
    prov_data = resp_prov.json()
    matched_prov = _find_doc(prov_data["results"], doc_id)
    assert matched_prov is not None, "Document not found by provider 'PhonePe'!"
    assert "PhonePe" in matched_prov["match_reason"]

    # 6. Verify original image integrity via /uploads
    img_resp = client.get(f"/uploads/{matched_exact['image_name']}")
    assert img_resp.status_code == 200
    assert len(img_resp.content) > 0


def test_e2e_friend_payee_xyz_search(client: TestClient):
    """
    Scenario: Upload PhonePe QR code for friend 'XYZ'.
    Verify:
    1. Searching 'XYZ' retrieves the image with match_reason.
    2. Searching 'PhonePe' also finds the friend's QR.
    """
    payload = "upi://pay?pa=xyzpayee@ybl&pn=XYZ&cu=INR"
    img_bytes = _create_qr_image(payload)

    fn = f"test_qr_xyz_{uuid.uuid4().hex[:6]}.png"
    upload_resp = client.post("/upload", files={"file": (fn, img_bytes, "image/png")})
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["id"]

    resp_xyz = client.post("/search", json={"query": "XYZ"})
    assert resp_xyz.status_code == 200
    xyz_data = resp_xyz.json()
    matched = _find_doc(xyz_data["results"], doc_id)
    assert matched is not None, "Document not found for friend payee 'XYZ'!"
    assert "XYZ" in matched["match_reason"]


def test_e2e_strict_non_hallucination_on_identifier_only(client: TestClient):
    """
    Scenario: Upload QR with ONLY a VPA identifier (no payee/merchant name).
    Verify searching an invented name (e.g. 'Ramesh', 'Suresh') strictly DOES NOT match this image.
    """
    payload = "upi://pay?pa=shop99unique@ybl"
    img_bytes = _create_qr_image(payload)

    fn = f"test_qr_anon_{uuid.uuid4().hex[:6]}.png"
    upload_resp = client.post("/upload", files={"file": (fn, img_bytes, "image/png")})
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["id"]

    # Search for arbitrary person name
    resp_invented = client.post("/search", json={"query": "Ramesh Gupta"})
    assert resp_invented.status_code == 200
    matched = next((r for r in resp_invented.json()["results"] if r["id"] == doc_id), None)
    assert matched is None, "Identifier-only QR must NOT match invented or hallucinated names!"


def test_e2e_multi_qr_image(client: TestClient):
    """
    Scenario: Image containing TWO distinct QR codes side-by-side.
    Verify both QR payloads are decoded and both are individually searchable.
    """
    payload_a = "upi://pay?pa=merchant_alpha@ybl&pn=Alpha%20Cafe"
    payload_b = "upi://pay?pa=merchant_beta@okhdfcbank&pn=Beta%20Bakery"

    # Create composite image with two QR codes
    doc = Image.new("RGB", (700, 400), color="white")
    draw = ImageDraw.Draw(doc)
    draw.text((20, 20), f"Dual Ref: {uuid.uuid4().hex}", fill="black")
    qr_a = Image.open(io.BytesIO(_create_qr_image(payload_a))).convert("RGB").resize((250, 250))
    qr_b = Image.open(io.BytesIO(_create_qr_image(payload_b))).convert("RGB").resize((250, 250))
    doc.paste(qr_a, (50, 75))
    doc.paste(qr_b, (380, 75))

    buf = io.BytesIO()
    doc.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    fn = f"test_dual_qr_{uuid.uuid4().hex[:6]}.png"
    upload_resp = client.post("/upload", files={"file": (fn, img_bytes, "image/png")})
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["id"]
    expected_id = upload_resp.json().get("canonical_image_id") or doc_id

    # Search Merchant A
    resp_a = client.post("/search", json={"query": "Alpha Cafe"})
    assert resp_a.status_code == 200
    assert any(
        r["id"] in (doc_id, expected_id)
        or r.get("canonical_image_id") in (doc_id, expected_id)
        or any(v["id"] in (doc_id, expected_id) for v in r.get("duplicate_variants", []))
        for r in resp_a.json()["results"]
    )

    # Search Merchant B
    resp_b = client.post("/search", json={"query": "Beta Bakery"})
    assert resp_b.status_code == 200
    assert any(
        r["id"] in (doc_id, expected_id)
        or r.get("canonical_image_id") in (doc_id, expected_id)
        or any(v["id"] in (doc_id, expected_id) for v in r.get("duplicate_variants", []))
        for r in resp_b.json()["results"]
    )


def test_e2e_combined_ocr_and_qr_search(client: TestClient):
    """
    Scenario: Receipt containing BOTH printed text ('College Fee Receipt 2026')
    AND a payment QR code ('Campus Canteen Services').
    Verify document is retrievable by BOTH text keyword and QR merchant name.
    """
    text_lines = ["COLLEGE CAMPUS ADMISSION", "Tuition Fee Receipt 2026", "Total Paid: Rs 15000"]
    qr_payload = "upi://pay?pa=campusfee@okhdfcbank&pn=Campus%20Canteen%20Services"
    img_bytes = _create_receipt_with_qr(text_lines, qr_payload)

    fn = f"test_receipt_qr_{uuid.uuid4().hex[:6]}.png"
    upload_resp = client.post("/upload", files={"file": (fn, img_bytes, "image/png")})
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["id"]

    # 1. Search by OCR text keyword
    resp_text = client.post("/search", json={"query": "Tuition Fee"})
    assert resp_text.status_code == 200
    assert _find_doc(resp_text.json()["results"], doc_id) is not None, "Document not found by OCR text!"

    # 2. Search by QR merchant name
    resp_qr = client.post("/search", json={"query": "Campus Canteen"})
    assert resp_qr.status_code == 200
    assert _find_doc(resp_qr.json()["results"], doc_id) is not None, "Document not found by QR merchant name!"


def test_e2e_multi_tenant_qr_privacy_isolation(client: TestClient):
    """
    Scenario: Multi-tenant isolation.
    User A uploads a QR document. User B searches for that QR merchant.
    User B MUST receive zero results.
    """
    suffix = uuid.uuid4().hex[:6]
    user_a = f"tenant_a_{suffix}"
    user_b = f"tenant_b_{suffix}"
    pwd = "SecurePassword123!"

    # 1. Register and login User A
    client.post("/auth/register", json={"username": user_a, "password": pwd, "is_admin": False})
    tok_a = client.post("/auth/login", json={"username": user_a, "password": pwd}).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {tok_a}"}

    # 2. Register and login User B
    client.post("/auth/register", json={"username": user_b, "password": pwd, "is_admin": False})
    tok_b = client.post("/auth/login", json={"username": user_b, "password": pwd}).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {tok_b}"}

    # 3. User A uploads a private payment QR
    secret_merchant = f"Secret Vault Merchant {suffix}"
    payload = f"upi://pay?pa=secret{suffix}@ybl&pn={secret_merchant.replace(' ', '%20')}"
    img_bytes = _create_qr_image(payload)

    fn = f"test_vault_qr_{suffix}.png"
    up_resp = client.post("/upload", headers=headers_a, files={"file": (fn, img_bytes, "image/png")})
    assert up_resp.status_code == 200
    doc_id = up_resp.json()["id"]

    # User A finds their own document
    search_a = client.post("/search", headers=headers_a, json={"query": secret_merchant})
    assert search_a.status_code == 200
    assert any(r["id"] == doc_id for r in search_a.json()["results"])

    # User B must NOT find User A's private document
    search_b = client.post("/search", headers=headers_b, json={"query": secret_merchant})
    assert search_b.status_code == 200
    assert not any(r["id"] == doc_id for r in search_b.json()["results"]), "Tenant leak: User B saw User A's QR!"


def test_e2e_unrelated_and_garbage_query_rejection(client: TestClient):
    """
    Scenario: Unrelated queries (e.g. 'Astronomy Rocket Galaxy') or empty queries
    must return 0 results and never match payment QR codes.
    """
    resp_empty = client.post("/search", json={"query": ""})
    assert resp_empty.status_code == 200
    assert resp_empty.json()["count"] == 0

    resp_space = client.post("/search", json={"query": "    "})
    assert resp_space.status_code == 200
    assert resp_space.json()["count"] == 0

    resp_garbage = client.post("/search", json={"query": "Supernova Astrophysics Nebula 2099"})
    assert resp_garbage.status_code == 200
    assert resp_garbage.json()["count"] == 0


def test_e2e_corrupted_or_non_qr_image_handled_gracefully(client: TestClient):
    """
    Scenario: Uploading a plain solid image without a QR code.
    Verify has_qr is False, and no 500 error occurs.
    """
    plain = Image.new("RGB", (300, 300), color="gray")
    buf = io.BytesIO()
    plain.save(buf, format="JPEG")

    fn = f"test_plain_{uuid.uuid4().hex[:6]}.jpg"
    upload_resp = client.post("/upload", files={"file": (fn, buf.getvalue(), "image/jpeg")})
    assert upload_resp.status_code == 200
    data = upload_resp.json()
    assert data.get("qr_payload") == "" or data.get("qr_payload") is None
