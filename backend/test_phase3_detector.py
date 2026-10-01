import sys
import io
import json
from pathlib import Path
import cv2
import numpy as np

# Set stdout to UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from app.visual_detector import get_visual_detector

PHASE3_DIR = ROOT_DIR.parent / "dataset" / "phase3"
GT_FILE = PHASE3_DIR / "ground_truth_phase3.json"
PREVIEW_DIR = PHASE3_DIR / "annotated_previews"
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)


def calculate_iou(boxA: dict, boxB: dict) -> float:
    """Calculate Intersection over Union (IoU) between two bounding boxes {x, y, width, height}."""
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

    if unionArea == 0:
        return 0.0
    return interArea / unionArea


def run_evaluation():
    print("=" * 85)
    print("PHASE 3: INDEPENDENT COMPUTER VISION DETECTOR BENCHMARK")
    print("=" * 85)

    with open(GT_FILE, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    detector = get_visual_detector()

    total_qr_images = 0
    detected_qr_images = 0

    total_non_qr_images = 0
    false_positives = 0

    total_qr_objects = 0
    matched_qr_objects = 0

    multi_qr_total = 0
    multi_qr_success = 0

    iou_scores = []

    results_table = []

    for filename, gt in ground_truth.items():
        rel_path = gt["relative_path"]
        img_path = PHASE3_DIR / rel_path
        has_qr_gt = gt["contains_qr"]
        gt_count = gt["count"]
        gt_objs = gt["objects"]

        res = detector.detect_visual_objects(img_path)
        pred_detected = res["detected"]
        pred_count = res["count"]
        pred_objs = res["objects"]

        # Save annotated image for visual inspection
        annotated = detector.draw_annotated_image(img_path, res)
        cv2.imwrite(str(PREVIEW_DIR / f"annotated_{filename}"), annotated)

        # Classification metrics
        if has_qr_gt:
            total_qr_images += 1
            total_qr_objects += gt_count

            if gt_count > 1:
                multi_qr_total += 1
                if pred_count == gt_count:
                    multi_qr_success += 1

            if pred_detected:
                detected_qr_images += 1

            # Match predicted boxes to ground truth boxes and compute IoU
            for gobj in gt_objs:
                gbox = gobj["bbox"]
                best_iou = 0.0
                for pobj in pred_objs:
                    pbox = pobj["bbox"]
                    iou = calculate_iou(gbox, pbox)
                    if iou > best_iou:
                        best_iou = iou

                iou_scores.append(best_iou)
                if best_iou >= 0.50:
                    matched_qr_objects += 1

            status = "[PASS]" if (pred_detected and pred_count == gt_count) else "[DIFF]"
            results_table.append((status, filename, f"QR ({gt_count})", f"Pred: {pred_count}", f"Mean IoU: {np.mean([iou_scores[-gt_count:]]):.3f}"))

        else:
            total_non_qr_images += 1
            if pred_detected:
                false_positives += 1
                status = "[FAIL - FP]"
            else:
                status = "[PASS - TN]"

            results_table.append((status, filename, "No QR (0)", f"Pred: {pred_count}", "N/A"))

    # Print Detailed Table
    print(f"\n{'Status':<12} | {'Filename':<36} | {'Ground Truth':<14} | {'Predicted':<12} | {'IoU'}")
    print("-" * 85)
    for status, fn, gt_str, pred_str, iou_str in results_table:
        print(f"{status:<12} | {fn:<36} | {gt_str:<14} | {pred_str:<12} | {iou_str}")

    # Compute Summary Statistics
    recall = (detected_qr_images / total_qr_images * 100) if total_qr_images > 0 else 0.0
    fpr = (false_positives / total_non_qr_images * 100) if total_non_qr_images > 0 else 0.0
    true_positives = detected_qr_images
    precision = (true_positives / (true_positives + false_positives) * 100) if (true_positives + false_positives) > 0 else 0.0
    mean_iou = np.mean(iou_scores) if iou_scores else 0.0
    multi_rate = (multi_qr_success / multi_qr_total * 100) if multi_qr_total > 0 else 0.0

    print("\n" + "=" * 85)
    print("PHASE 3 EVALUATION METRICS SUMMARY")
    print("=" * 85)
    print(f"Total Test Images                     : {len(ground_truth)}")
    print(f"  • Images containing QR Codes        : {total_qr_images}")
    print(f"  • Images without QR Codes           : {total_non_qr_images}")
    print(f"  • Multi-QR Documents (2+ codes)     : {multi_qr_total}")
    print("-" * 85)
    print(f"Detection Recall (Sensitivity)        : {recall:5.1f}%  ({detected_qr_images}/{total_qr_images})")
    print(f"False Positive Rate (FPR)             : {fpr:5.1f}%  ({false_positives}/{total_non_qr_images})")
    print(f"Detection Precision                   : {precision:5.1f}%  ({true_positives}/{true_positives + false_positives})")
    print(f"Mean Localization IoU (Bounding Box)  : {mean_iou:5.3f}   (Overlap with Ground Truth)")
    print(f"Multiple-Object Detection Rate        : {multi_rate:5.1f}%  ({multi_qr_success}/{multi_qr_total})")
    print("=" * 85)
    print(f"\nAnnotated verification images written to:\n{PREVIEW_DIR}")


if __name__ == "__main__":
    run_evaluation()
