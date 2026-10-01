import sys
import io
import json
from pathlib import Path
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent
PHASE3_DIR = ROOT_DIR.parent / "dataset" / "phase3"
API_URL = "http://127.0.0.1:8000/detect-visual"

def test_detect_visual_endpoint():
    print("=" * 85)
    print("PHASE 3: DAY 2 — FASTAPI /detect-visual ENDPOINT VERIFICATION")
    print("=" * 85)

    test_samples = [
        ("Single QR Document", PHASE3_DIR / "positive" / "doc_qr_01_scholarship.jpg", True, 1),
        ("Multi-QR Document (3 QRs)", PHASE3_DIR / "multi_qr" / "doc_multi_03_conference_badge.jpg", True, 3),
        ("Negative Document (No QR)", PHASE3_DIR / "negative" / "doc_neg_01_cleanliness_notice.jpg", False, 0),
        ("Small QR Edge Case", PHASE3_DIR / "difficult" / "doc_diff_01_small_qr.jpg", True, 1),
    ]

    all_passed = True

    for label, img_path, expected_detected, expected_count in test_samples:
        print(f"\nTesting: {label} -> {img_path.name}")
        if not img_path.exists():
            print(f"  [ERROR] File not found: {img_path}")
            all_passed = False
            continue

        with open(img_path, "rb") as f:
            files = {"file": (img_path.name, f, "image/jpeg")}
            response = requests.post(API_URL, files=files)

        if response.status_code != 200:
            print(f"  [FAIL] HTTP Status: {response.status_code} - {response.text}")
            all_passed = False
            continue

        data = response.json()
        detected = data.get("detected")
        count = data.get("count")
        objects = data.get("objects", [])
        dims = data.get("image_dimensions", {})

        print(f"  HTTP 200 OK | Dimensions: {dims.get('width')}x{dims.get('height')}")
        print(f"  Detected: {detected} (Expected: {expected_detected}) | Count: {count} (Expected: {expected_count})")

        for idx, obj in enumerate(objects, 1):
            bbox = obj.get("bbox", {})
            norm = obj.get("normalized_bbox", {})
            loc = obj.get("location_desc", "")
            payload = obj.get("data", "")
            print(f"    Object #{idx}: [{obj.get('label')}] at ({bbox.get('x')}, {bbox.get('y')}) size {bbox.get('width')}x{bbox.get('height')} px")
            print(f"      Location: {loc} | Payload: {payload}")

        if detected == expected_detected and count == expected_count:
            print("  >>> [PASS] Output perfectly matches ground-truth specification!")
        else:
            print("  >>> [FAIL] Output mismatch!")
            all_passed = False

    print("\n" + "=" * 85)
    if all_passed:
        print("ALL FASTAPI /detect-visual TEST CASES PASSED SUCCESSFULLY (100%)!")
    else:
        print("SOME TEST CASES FAILED!")
    print("=" * 85)

if __name__ == "__main__":
    test_detect_visual_endpoint()
