"""Automated Multi-Modal Fusion Benchmark Test Suite:
Validates that ONE search box concurrently evaluates Text Retrieval and Visual Retrieval (CLIP).
Confirms that composite documents (e.g. Aadhaar, Student ID) return BOTH yellow text highlights
and precision visual bounding box overlays on the same unified result card.
"""

import sys
import io
import json
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from app.main import app, SearchRequest, search_images

def compute_iou(boxA, boxB):
    if not boxA or not boxB:
        return 0.0
    xA = max(boxA["x"], boxB["x"])
    yA = max(boxA["y"], boxB["y"])
    xB = min(boxA["x"] + boxA["width"], boxB["x"] + boxB["width"])
    yB = min(boxA["y"] + boxA["height"], boxB["y"] + boxB["height"])

    interW = max(0, xB - xA)
    interH = max(0, yB - yA)
    interArea = interW * interH

    boxAArea = boxA["width"] * boxA["height"]
    boxBArea = boxB["width"] * boxB["height"]
    unionArea = boxAArea + boxBArea - interArea

    return interArea / unionArea if unionArea > 0 else 0.0

def run_fusion_benchmark():
    print("=" * 105)
    print("PARALLEL MULTI-MODAL FUSION BENCHMARK (ONE SEARCH BOX: TEXT + VISUAL)")
    print("=" * 105)

    test_cases = [
        {
            "id": "TC-01",
            "query": "Aadhaar",
            "expected_top1": "doc_composite_01_aadhaar.jpg",
            "expected_type": "multimodal",
            "expect_text_highlight": True,
            "expect_visual_box": True,
            "description": "Aadhaar search should retrieve composite application with text highlight + card bbox",
        },
        {
            "id": "TC-02",
            "query": "Samrudhi Deshmukh",
            "expected_top1": "doc_composite_01_aadhaar.jpg",
            "expected_type": ["keyword", "semantic", "multimodal"],
            "expect_text_highlight": True,
            "expect_visual_box": False,
            "description": "Applicant name search should retrieve document with yellow highlight on name",
        },
        {
            "id": "TC-03",
            "query": "student identity card",
            "expected_top1": "doc_composite_02_student_id.jpg",
            "expected_type": "multimodal",
            "expect_text_highlight": True,
            "expect_visual_box": True,
            "description": "Identity card query should match text instruction + embedded student ID card",
        },
        {
            "id": "TC-04",
            "query": "signature",
            "expected_top1": None,  # Any signature doc
            "expected_type": ["visual", "multimodal"],
            "expect_text_highlight": False,
            "expect_visual_box": True,
            "description": "Visual query 'signature' should pinpoint signature bounding box",
        },
        {
            "id": "TC-05",
            "query": "official circular stamp seal",
            "expected_top1": None,
            "expected_type": "visual",
            "expect_text_highlight": False,
            "expect_visual_box": True,
            "description": "Visual query 'stamp' should pinpoint official seal bounding box",
        },
        {
            "id": "TC-06",
            "query": "scholarship",
            "expected_top1": None,
            "expected_type": ["keyword", "semantic", "multimodal"],
            "expect_text_highlight": True,
            "expect_visual_box": False,
            "description": "Standard keyword query should maintain yellow text highlighting",
        },
        {
            "id": "TC-07",
            "query": "mango farming in tropical climate",
            "expected_top1": None,
            "expected_type": None,
            "expect_count": 0,
            "description": "Out-of-domain query must be rejected (0 results)",
        },
    ]

    all_passed = True
    print(f"{'ID':<6} | {'Query':<32} | {'Top-1 Document':<28} | {'Type':<11} | {'Score':<6} | {'Status'}")
    print("-" * 105)

    for tc in test_cases:
        t0 = time.perf_counter()
        req = SearchRequest(query=tc["query"])
        resp = search_images(req)
        dt_ms = (time.perf_counter() - t0) * 1000

        results = resp.get("results", [])
        total_count = resp.get("count", 0)

        # OOD case
        if tc.get("expect_count") == 0:
            status = "PASS" if total_count == 0 else f"FAIL (Got {total_count})"
            if total_count != 0:
                all_passed = False
            print(f"{tc['id']:<6} | {tc['query']:<32} | {'None (Rejected)':<28} | {'-':<11} | {'-':<6} | {status} ({dt_ms:.1f}ms)")
            continue

        if not results:
            print(f"{tc['id']:<6} | {tc['query']:<32} | {'No matches found':<28} | {'-':<11} | {'-':<6} | FAIL ({dt_ms:.1f}ms)")
            all_passed = False
            continue

        top1 = results[0]
        top1_name = top1.get("image_name", "")
        top1_type = top1.get("search_type", "")
        top1_score = top1.get("similarity_score", 0.0)

        pass_top1 = True
        if tc.get("expected_top1"):
            pass_top1 = (top1_name == tc["expected_top1"])

        pass_type = True
        if tc.get("expected_type"):
            if isinstance(tc["expected_type"], list):
                pass_type = top1_type in tc["expected_type"]
            else:
                pass_type = (top1_type == tc["expected_type"])

        pass_hl = True
        if tc.get("expect_text_highlight"):
            hl_terms = top1.get("highlight_terms", [])
            pass_hl = len(hl_terms) > 0

        pass_vis = True
        if tc.get("expect_visual_box"):
            vis_objs = top1.get("visual_objects", [])
            pass_vis = top1.get("has_visual_objects", False) and len(vis_objs) > 0

        is_pass = pass_top1 and pass_type and pass_hl and pass_vis
        status = "PASS" if is_pass else "FAIL"
        if not is_pass:
            all_passed = False

        print(f"{tc['id']:<6} | {tc['query']:<32} | {top1_name:<28} | {top1_type:<11} | {top1_score:<6.3f} | {status} ({dt_ms:.1f}ms)")

        # Print detailed diagnosis
        if top1_type == "multimodal" or top1.get("has_visual_objects"):
            vis_objs = top1.get("visual_objects", [])
            first_box = vis_objs[0].get("bbox", {}) if vis_objs else {}
            print(f"       ↳ 🟨 Text Highlights: {top1.get('highlight_terms', [])}")
            print(f"       ↳ 🔲 Visual Box: {first_box} ({vis_objs[0].get('location_desc', 'Embedded') if vis_objs else ''})")
            print(f"       ↳ 📝 Snippet Preview: {top1.get('preview_snippet', '')[:70]}...")

    print("=" * 105)
    if all_passed:
        print(">>> ALL MULTI-MODAL FUSION BENCHMARK TESTS PASSED (100% ACCURACY) <<<")
    else:
        print(">>> SOME TESTS FAILED — CHECK DETAILS ABOVE <<<")
    print("=" * 105)

if __name__ == "__main__":
    run_fusion_benchmark()
