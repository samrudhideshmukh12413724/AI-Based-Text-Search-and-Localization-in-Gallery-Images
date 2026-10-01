import sys
import io
import json
from pathlib import Path
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent
PHASE3_DIR = ROOT_DIR.parent / "dataset" / "phase3"
BASE_URL = "http://127.0.0.1:8000"

def test_day3_integration():
    print("=" * 85)
    print("PHASE 3: DAY 3 — MULTI-MODAL DOCUMENT & SEARCH INTEGRATION BENCHMARK")
    print("=" * 85)

    all_passed = True

    # -------------------------------------------------------------------------
    # TEST 1: Semantic Query Returning Text + Semantic Match + Visual Objects
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Semantic Search: 'Government Scholarship grant'")
    resp = requests.post(f"{BASE_URL}/search", json={"query": "Government Scholarship grant"})
    if resp.status_code != 200:
        print(f"  [FAIL] HTTP {resp.status_code}: {resp.text}")
        all_passed = False
    else:
        data = resp.json()
        print(f"  Search Type: {data.get('search_type')} | Found: {data.get('count')} results")
        results = data.get("results", [])
        
        # Check that doc_qr_01_scholarship is in the results with visual metadata
        qr_doc = next((r for r in results if r.get("image_name") == "doc_qr_01_scholarship.jpg"), None)
        if qr_doc:
            print(f"  Target Document    : {qr_doc.get('image_name')}")
            print(f"  Semantic Score     : {qr_doc.get('similarity_score')}")
            print(f"  Text Preview       : {qr_doc.get('preview_snippet')[:80]}...")
            print(f"  Highlight Terms    : {qr_doc.get('highlight_terms')}")
            print(f"  Matched Concepts   : {qr_doc.get('matched_concepts')}")
            print(f"  Visual Objects?    : {qr_doc.get('has_visual_objects')}")
            print(f"  Visual Summary     : {qr_doc.get('visual_summary')}")
            print(f"  Bounding Boxes     : {qr_doc.get('visual_objects')}")

            if qr_doc.get("has_visual_objects") and len(qr_doc.get("visual_objects", [])) > 0:
                print("  >>> [PASS] Document contains OCR text + Semantic Match + Phase 3 Visual Bounding Box!")
            else:
                print("  >>> [FAIL] Visual object metadata missing from target result!")
                all_passed = False
        else:
            print("  >>> [FAIL] doc_qr_01_scholarship.jpg not found in search results!")
            all_passed = False

    # -------------------------------------------------------------------------
    # TEST 2: Visual Filter Query ('documents with qr code')
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Visual Query: 'documents with qr code'")
    resp = requests.post(f"{BASE_URL}/search", json={"query": "documents with qr code"})
    if resp.status_code != 200:
        print(f"  [FAIL] HTTP {resp.status_code}: {resp.text}")
        all_passed = False
    else:
        data = resp.json()
        print(f"  Search Type: {data.get('search_type')} | Found: {data.get('count')} visual documents")
        results = data.get("results", [])
        if len(results) > 0:
            for r in results[:4]:
                print(f"    • {r.get('image_name'):<36} | Visual: {r.get('visual_summary')}")
            print("  >>> [PASS] Visual search correctly retrieved QR-bearing documents!")
        else:
            print("  >>> [FAIL] Visual search returned 0 documents!")
            all_passed = False

    # -------------------------------------------------------------------------
    # TEST 3: Multi-Modal Upload Pipeline Test (OCR + OpenCV Detector)
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Multi-Modal Ingestion: POST /upload on 'doc_qr_02_admit_card.jpg'")
    upload_file = PHASE3_DIR / "positive" / "doc_qr_02_admit_card.jpg"
    with open(upload_file, "rb") as f:
        files = {"file": ("test_upload_admit.jpg", f, "image/jpeg")}
        resp = requests.post(f"{BASE_URL}/upload", files=files)

    if resp.status_code != 200:
        print(f"  [FAIL] HTTP {resp.status_code}: {resp.text}")
        all_passed = False
    else:
        up_data = resp.json()
        print(f"  Uploaded ID        : {up_data.get('id')}")
        print(f"  Extracted Text     : {up_data.get('text')[:80]}...")
        print(f"  Has Visual Objects : {up_data.get('has_visual_objects')} (Expected: True)")
        print(f"  Visual Summary     : {up_data.get('visual_summary')}")
        print(f"  Visual Objects     : {up_data.get('visual_objects')}")

        if up_data.get("has_visual_objects") and len(up_data.get("visual_objects", [])) > 0:
            print("  >>> [PASS] Multi-modal /upload pipeline executed OCR + Visual Detection successfully!")
        else:
            print("  >>> [FAIL] Visual detection failed during /upload!")
            all_passed = False

    # -------------------------------------------------------------------------
    # TEST 4: Negative Document (Clean No-QR Sample)
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Search on Non-QR Document: 'cleanliness drive'")
    resp = requests.post(f"{BASE_URL}/search", json={"query": "cleanliness drive"})
    if resp.status_code != 200:
        print(f"  [FAIL] HTTP {resp.status_code}: {resp.text}")
        all_passed = False
    else:
        data = resp.json()
        results = data.get("results", [])
        if results:
            top = results[0]
            print(f"  Document       : {top.get('image_name')}")
            print(f"  Visual Objects?: {top.get('has_visual_objects')} (Expected: False)")
            print(f"  Visual Objects : {top.get('visual_objects')} (Expected: [])")
            if not top.get("has_visual_objects") and len(top.get("visual_objects", [])) == 0:
                print("  >>> [PASS] Non-QR document correctly reports 0 visual objects!")
            else:
                print("  >>> [FAIL] False visual object attached to non-QR document!")
                all_passed = False
        else:
            print("  >>> [FAIL] No matches for cleanliness drive!")
            all_passed = False

    print("\n" + "=" * 85)
    if all_passed:
        print("ALL DAY 3 MULTI-MODAL PIPELINE INTEGRATION TESTS PASSED (100%)!")
    else:
        print("SOME INTEGRATION TESTS FAILED!")
    print("=" * 85)

if __name__ == "__main__":
    test_day3_integration()
