"""Comprehensive Phase 3B Evaluation Suite:
Measures Top-1, Top-3, Mean Similarity, IoU Localization (>=0.50 & >=0.75), Out-of-Domain Rejection, and Query Latency across 25 benchmark documents."""

import io
import json
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from app import database
from app.ocr import extract_text
from app.visual_detector import get_visual_detector
from app.visual_search import get_visual_search_engine
from app.semantic_search import build_embeddings_index

DATASET_DIR = ROOT_DIR.parent / "dataset" / "phase3b"

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

def ingest_phase3b_dataset():
    print("=" * 95)
    print("INGESTING 25-DOCUMENT PHASE 3B MULTI-MODAL BENCHMARK DATASET")
    print("=" * 95)

    database.init_db()
    v_detector = get_visual_detector()
    v_search = get_visual_search_engine()

    doc_files = sorted(DATASET_DIR.glob("*.jpg"))
    print(f"Ingesting {len(doc_files)} documents from {DATASET_DIR}...\n")

    t_start = time.perf_counter()
    for doc_path in doc_files:
        t0 = time.perf_counter()
        # 1. OCR Extraction
        text = extract_text(doc_path)

        # 2. QR / Structural Detection
        vis_res = v_detector.detect_visual_objects(str(doc_path))
        has_vis = 1 if vis_res.get("has_visual_objects", False) else 0

        # 3. Database Persistence
        saved = database.save_image(
            image_name=doc_path.name,
            image_path=str(doc_path.resolve()),
            extracted_text=text,
            original_ocr_text=text,
            category="phase3b_benchmark",
            has_visual_objects=has_vis,
            visual_metadata=vis_res
        )

        # 4. Visual Region Extraction & CLIP Embeddings
        indexed_count = v_search.index_document(saved["id"], doc_path.name, str(doc_path))

        dt = (time.perf_counter() - t0) * 1000
        print(f"  • Ingested {doc_path.name:<18} | Regions: {indexed_count:02d} | Time: {dt:6.1f} ms")

    # 5. Build Semantic Index
    build_embeddings_index()
    total_time = (time.perf_counter() - t_start)
    print(f"\nIngestion Complete in {total_time:.2f}s! All 25 documents indexed with text, semantic, and visual patch embeddings.")

def run_evaluation():
    print("\n" + "=" * 95)
    print("PHASE 3B EVALUATION: LOCALIZED VISUAL-REGION RETRIEVAL BENCHMARK")
    print("=" * 95)

    v_search = get_visual_search_engine()
    gt_path = DATASET_DIR / "ground_truth_phase3b.json"
    with open(gt_path, "r", encoding="utf-8") as f:
        ground_truth_list = json.load(f)
        ground_truth = {item["file_name"]: item for item in ground_truth_list}

    # Evaluation query suite
    eval_suite = [
        # Signatures
        {"query": "a handwritten signature", "category": "signature", "expected_prefix": "doc_sign_"},
        {"query": "authorized signature of registrar", "category": "signature", "expected_prefix": "doc_sign_"},
        {"query": "signature ink stroke", "category": "signature", "expected_prefix": "doc_sign_"},
        # Official Stamps / Seals
        {"query": "an official circular stamp seal", "category": "stamp", "expected_prefix": "doc_stamp_"},
        {"query": "university red seal verification", "category": "stamp", "expected_prefix": "doc_stamp_"},
        {"query": "official attestation stamp", "category": "stamp", "expected_prefix": "doc_stamp_"},
        # Photographs
        {"query": "student portrait photograph", "category": "photo", "expected_prefix": "doc_photo_"},
        {"query": "photo identification card", "category": "photo", "expected_prefix": "doc_photo_"},
        {"query": "candidate face photo", "category": "photo", "expected_prefix": "doc_photo_"},
        # QR Codes
        {"query": "QR code verification matrix", "category": "qr_code", "expected_prefix": "doc_qr_"},
        {"query": "scannable digital QR barcode", "category": "qr_code", "expected_prefix": "doc_qr_"},
        {"query": "QR matrix code", "category": "qr_code", "expected_prefix": "doc_qr_"},
        # Out-of-Domain Negative Controls
        {"query": "mango farming agriculture", "category": "out_of_domain", "expected_prefix": None},
        {"query": "italian pizza recipe", "category": "out_of_domain", "expected_prefix": None},
        {"query": "car engine repair service", "category": "out_of_domain", "expected_prefix": None},
    ]

    total_visual_queries = 0
    top1_correct = 0
    top3_correct = 0
    iou_50_count = 0
    iou_75_count = 0
    similarity_scores = []
    latencies = []
    out_of_domain_rejected = 0
    total_ood = 0

    print(f"{'Query':<36} | {'Target Type':<12} | {'Top-1 Match':<16} | {'Score':<6} | {'IoU':<6} | {'Top-1':<5} | {'Top-3':<5} | {'Latency'}")
    print("-" * 115)

    for item in eval_suite:
        q = item["query"]
        cat = item["category"]
        expected_prefix = item["expected_prefix"]

        t0 = time.perf_counter()
        results = v_search.search(q, top_k=5, threshold=0.245)
        dt_ms = (time.perf_counter() - t0) * 1000
        latencies.append(dt_ms)

        if cat != "out_of_domain":
            total_visual_queries += 1
            if results:
                top1_doc = results[0]["image_name"]
                top1_score = results[0]["similarity_score"]
                similarity_scores.append(top1_score)

                is_top1 = top1_doc.startswith(expected_prefix)
                if is_top1:
                    top1_correct += 1

                # Top-3 check
                top3_docs = [r["image_name"] for r in results[:3]]
                is_top3 = any(d.startswith(expected_prefix) for d in top3_docs)
                if is_top3:
                    top3_correct += 1

                # Localization IoU
                best_reg = results[0].get("best_region", {})
                pred_bbox = best_reg.get("bbox", {})
                gt_bbox = ground_truth.get(top1_doc, {}).get("bbox")
                iou = compute_iou(pred_bbox, gt_bbox) if gt_bbox else 0.0

                if iou >= 0.50:
                    iou_50_count += 1
                if iou >= 0.75:
                    iou_75_count += 1

                t1_str = "PASS" if is_top1 else "FAIL"
                t3_str = "PASS" if is_top3 else "FAIL"
                print(f"{q:<36} | {cat:<12} | {top1_doc:<16} | {top1_score:5.3f} | {iou:4.2f} | {t1_str:<5} | {t3_str:<5} | {dt_ms:5.1f} ms")
                print(f"   ↳ BBox: {pred_bbox} ({best_reg.get('location_desc')})")
            else:
                print(f"{q:<36} | {cat:<12} | {'None':<16} | {'-':<6} | {'-':<6} | {'FAIL':<5} | {'FAIL':<5} | {dt_ms:5.1f} ms")
        else:
            total_ood += 1
            if not results:
                out_of_domain_rejected += 1
                print(f"{q:<36} | {cat:<12} | {'None (Clean)':<16} | {'-':<6} | {'N/A':<6} | {'PASS':<5} | {'PASS':<5} | {dt_ms:5.1f} ms")
            else:
                score = results[0]["similarity_score"]
                print(f"{q:<36} | {cat:<12} | {results[0]['image_name']:<16} | {score:5.3f} | {'N/A':<6} | {'WARN':<5} | {'WARN':<5} | {dt_ms:5.1f} ms")

    print("=" * 115)
    top1_acc = (top1_correct / total_visual_queries) * 100 if total_visual_queries > 0 else 0
    top3_acc = (top3_correct / total_visual_queries) * 100 if total_visual_queries > 0 else 0
    iou50_acc = (iou_50_count / total_visual_queries) * 100 if total_visual_queries > 0 else 0
    iou75_acc = (iou_75_count / total_visual_queries) * 100 if total_visual_queries > 0 else 0
    mean_sim = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0
    avg_lat = sum(latencies) / len(latencies)
    ood_acc = (out_of_domain_rejected / total_ood) * 100 if total_ood > 0 else 0

    print("\n" + "=" * 85)
    print("PHASE 3B QUANTITATIVE BENCHMARK EVALUATION SUMMARY")
    print("=" * 85)
    print(f"1. Benchmark Dataset Size: 25 documents (5 Signatures, 5 Stamps, 5 Photos, 5 QRs, 5 Text-only)")
    print(f"2. Evaluated Visual Query Categories: Signatures, Official Stamps/Seals, Photographs, QR Codes")
    print(f"3. Top-1 Retrieval Accuracy: {top1_correct}/{total_visual_queries} ({top1_acc:.1f}%) [Target: >=90%]")
    print(f"4. Top-3 Retrieval Accuracy: {top3_correct}/{total_visual_queries} ({top3_acc:.1f}%)")
    print(f"5. Spatial Localization IoU >= 0.50: {iou_50_count}/{total_visual_queries} ({iou50_acc:.1f}%)")
    print(f"6. Spatial Localization IoU >= 0.75: {iou_75_count}/{total_visual_queries} ({iou75_acc:.1f}%)")
    print(f"7. Mean Visual Similarity Score: {mean_sim:.4f}")
    print(f"8. Out-of-Domain Rejection Rate: {out_of_domain_rejected}/{total_ood} ({ood_acc:.1f}%)")
    print(f"9. Average Visual Query Latency: {avg_lat:.1f} ms (CPU inference)")
    print("=" * 85)

if __name__ == "__main__":
    ingest_phase3b_dataset()
    run_evaluation()
