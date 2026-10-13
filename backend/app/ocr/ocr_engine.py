"""Adaptive Dual-Pass OCR Engine.

Executes quality-aware, confidence-weighted OCR using EasyOCR.
Compares baseline vs adaptively preprocessed images to maximize
word confidence and character completeness while preserving
word-level bounding boxes and diagnostic metadata.
"""

from pathlib import Path
from typing import Union, List, Dict, Any, Optional
import cv2
import easyocr
import numpy as np

from app.ocr.quality import assess_image_quality
from app.ocr.preprocessing import preprocess_for_ocr

from PIL import Image, ImageOps

_readers: Dict[tuple, easyocr.Reader] = {}


def get_ocr_reader(languages: Optional[List[str]] = None) -> easyocr.Reader:
    """Singleton getter for EasyOCR Reader with multi-language caching."""
    global _readers
    target_langs = tuple(sorted(languages)) if languages else ("en",)
    if target_langs not in _readers:
        try:
            _readers[target_langs] = easyocr.Reader(list(target_langs), gpu=False, verbose=False)
        except Exception:
            _readers[target_langs] = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _readers[target_langs]


def _load_image(image_input: Union[str, Path, np.ndarray]) -> np.ndarray:
    """Loads image from path or returns copy of numpy array with EXIF orientation correction."""
    if isinstance(image_input, (str, Path)):
        p = Path(image_input)
        if not p.is_file():
            raise FileNotFoundError(f"Image not found: {p}")
        try:
            pil_img = Image.open(p)
            pil_img = ImageOps.exif_transpose(pil_img)
            img = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
        except Exception:
            img = cv2.imread(str(p))
        if img is None:
            raise ValueError(f"Failed to read image: {p}")
        return img
    elif isinstance(image_input, np.ndarray):
        return image_input.copy()
    else:
        raise TypeError(f"Unsupported image type: {type(image_input)}")


DEVANAGARI_DIGITS_MAP = str.maketrans("०१२३४५६७८९", "0123456789")


def _parse_easyocr_results(raw_results: list) -> tuple[str, float, list[dict]]:
    """
    Parses EasyOCR (bbox, text, conf) output tuples.
    Normalizes Devanagari digits to standard digits for consistent search.
    Returns (multiline_text, mean_confidence, word_boxes).
    """
    lines = []
    word_boxes = []
    conf_scores = []

    for item in raw_results:
        if len(item) < 3:
            continue
        poly_pts, text_val, conf = item
        raw_text = str(text_val).strip()
        if not raw_text:
            continue

        # Normalize Devanagari numerals (०-९ -> 0-9)
        clean_text = raw_text.translate(DEVANAGARI_DIGITS_MAP)

        lines.append(clean_text)
        conf_scores.append(float(conf))

        # Convert polygon points [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] to bounding box [x, y, w, h]
        try:
            pts = np.array(poly_pts, dtype=np.int32)
            x, y, w, h = cv2.boundingRect(pts)
            word_boxes.append({
                "text": clean_text,
                "confidence": round(float(conf), 3),
                "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}
            })
        except Exception:
            word_boxes.append({
                "text": clean_text,
                "confidence": round(float(conf), 3),
                "bbox": {}
            })

    full_text = "\n".join(lines)
    mean_conf = float(np.mean(conf_scores)) if conf_scores else 0.0
    return full_text, mean_conf, word_boxes


def _score_transcription(text: str, mean_conf: float) -> float:
    """
    Quality heuristic scoring a transcription candidate.
    Balances recognition confidence with completeness (character count).
    """
    alnum_chars = sum(1 for c in text if c.isalnum())
    if alnum_chars == 0 or mean_conf <= 0:
        return 0.0
    return mean_conf * float(np.log1p(alnum_chars))


def _scale_for_ocr(gray_img: np.ndarray, max_dim: int = 1600) -> np.ndarray:
    """Resizes large images so max dimension is 1600px, speeding up CPU OCR by ~3-4x."""
    h, w = gray_img.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(gray_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return gray_img


def _unrotate_poly(pts: np.ndarray, ori: str, H_sc: int, W_sc: int) -> np.ndarray:
    """Un-rotates polygon points back to the unrotated scaled image coordinate frame."""
    x = pts[:, 0]
    y = pts[:, 1]
    if ori == "0":
        return pts.copy()
    elif ori == "90_cw":
        # in 90 CW: x_rot = H_sc - 1 - y_orig, y_rot = x_orig
        x_unrot = y
        y_unrot = H_sc - 1 - x
        return np.stack([x_unrot, y_unrot], axis=1)
    elif ori == "90_ccw":
        # in 90 CCW: x_rot = y_orig, y_rot = W_sc - 1 - x_orig
        x_unrot = W_sc - 1 - y
        y_unrot = x
        return np.stack([x_unrot, y_unrot], axis=1)
    elif ori == "180":
        x_unrot = W_sc - 1 - x
        y_unrot = H_sc - 1 - y
        return np.stack([x_unrot, y_unrot], axis=1)
    return pts.copy()


def _box_iou(b1: dict, b2: dict) -> float:
    """Computes Intersection over Union between two axis-aligned bounding boxes."""
    x1, y1, w1, h1 = b1["x"], b1["y"], b1["width"], b1["height"]
    x2, y2, w2, h2 = b2["x"], b2["y"], b2["width"], b2["height"]
    xi1 = max(x1, x2)
    yi1 = max(y1, y2)
    xi2 = min(x1 + w1, x2 + w2)
    yi2 = min(y1 + h1, y2 + h2)
    inter_w = max(0, xi2 - xi1)
    inter_h = max(0, yi2 - yi1)
    inter_area = inter_w * inter_h
    if inter_area == 0:
        return 0.0
    union_area = (w1 * h1) + (w2 * h2) - inter_area
    return inter_area / float(union_area) if union_area > 0 else 0.0


def extract_text_adaptive(
    image_input: Union[str, Path, np.ndarray],
    languages: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    High-level Multi-Orientation Adaptive OCR Orchestrator.

    Workflow:
    1. Assesses image quality (blur, contrast, brightness).
    2. Scales large images to 1600px max dimension for fast processing.
    3. Runs OCR across 0° (native) and 90° CW (fanned passes, tickets, landscape phone shots).
    4. Automatically evaluates 90° CCW and 180° if initial passes detect sparse text.
    5. Un-rotates all polygon bounding boxes back to the original full-size image canvas.
    6. Selectively deduplicates overlapping detections without dropping different nearby words.
    7. Supports multilingual Marathi/Devanagari text extraction.
    8. Preserves word-level bounding boxes and confidence for in-image yellow highlighting.
    """
    from difflib import SequenceMatcher
    from app.translation import is_devanagari

    img = _load_image(image_input)
    H_orig, W_orig = img.shape[:2]

    # Step 1: Scale down huge camera photos for fast CPU processing (preserves aspect ratio)
    scale = 1600.0 / max(H_orig, W_orig) if max(H_orig, W_orig) > 1600 else 1.0
    if scale < 1.0:
        scaled = cv2.resize(img, (int(W_orig * scale), int(H_orig * scale)), interpolation=cv2.INTER_AREA)
    else:
        scaled = img.copy()
    H_sc, W_sc = scaled.shape[:2]

    # Assess quality for diagnostic metadata
    if len(scaled.shape) == 3:
        scaled_gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
    else:
        scaled_gray = scaled.copy()
    quality_report = assess_image_quality(scaled_gray)

    # Determine languages and reader
    use_mr = bool(languages and "mr" in languages)
    reader = get_ocr_reader(["en", "mr"] if use_mr else (languages or ["en"]))

    # Passes to evaluate: 0 deg first, then 90 CW
    orientations = [
        ("0", scaled),
        ("90_cw", cv2.rotate(scaled, cv2.ROTATE_90_CLOCKWISE)),
    ]

    all_raw_boxes = []
    preprocessing_applied = ["multi_orientation_0_90cw"]

    for ori_name, ori_img in orientations:
        try:
            raw_res = reader.readtext(
                ori_img,
                text_threshold=0.45,
                low_text=0.25,
                link_threshold=0.30,
                slope_ths=0.35,
            )
            for item in raw_res:
                if len(item) < 3:
                    continue
                poly_pts, text_val, conf = item
                clean_text = str(text_val).strip().translate(DEVANAGARI_DIGITS_MAP)
                if not clean_text or float(conf) < 0.20:
                    continue
                pts = np.array(poly_pts, dtype=np.float32)
                unrot_pts = _unrotate_poly(pts, ori_name, H_sc, W_sc)
                orig_pts = unrot_pts / scale
                x, y, w, h = cv2.boundingRect(orig_pts.astype(np.int32))
                all_raw_boxes.append({
                    "text": clean_text,
                    "confidence": round(float(conf), 3),
                    "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                    "orientation": ori_name
                })
        except Exception as e:
            print(f"[OCR Engine] Error on orientation {ori_name}: {e}")

    # If very few genuine words detected, test remaining orientations (90 CCW and 180)
    real_words = [b["text"] for b in all_raw_boxes if len(b["text"]) >= 2 and any(c.isalnum() for c in b["text"])]
    if len(real_words) < 4:
        for ori_name, ori_code in [("90_ccw", cv2.ROTATE_90_COUNTERCLOCKWISE), ("180", cv2.ROTATE_180)]:
            try:
                ori_img = cv2.rotate(scaled, ori_code)
                raw_res = reader.readtext(
                    ori_img,
                    text_threshold=0.45,
                    low_text=0.25,
                    link_threshold=0.30,
                    slope_ths=0.35,
                )
                for item in raw_res:
                    if len(item) < 3:
                        continue
                    poly_pts, text_val, conf = item
                    clean_text = str(text_val).strip().translate(DEVANAGARI_DIGITS_MAP)
                    if not clean_text or float(conf) < 0.20:
                        continue
                    pts = np.array(poly_pts, dtype=np.float32)
                    unrot_pts = _unrotate_poly(pts, ori_name, H_sc, W_sc)
                    orig_pts = unrot_pts / scale
                    x, y, w, h = cv2.boundingRect(orig_pts.astype(np.int32))
                    all_raw_boxes.append({
                        "text": clean_text,
                        "confidence": round(float(conf), 3),
                        "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                        "orientation": ori_name
                    })
                preprocessing_applied.append(f"orientation_{ori_name}")
            except Exception as e:
                print(f"[OCR Engine] Error on orientation {ori_name}: {e}")

    # Check if Devanagari text is detected or if Marathi scan should be run
    devanagari_present = any(is_devanagari(b["text"]) for b in all_raw_boxes)
    if not use_mr and (devanagari_present or (languages is None and len(real_words) < 5)):
        try:
            reader_mr = get_ocr_reader(["en", "mr"])
            raw_res_mr = reader_mr.readtext(
                scaled,
                text_threshold=0.45,
                low_text=0.25,
                link_threshold=0.30,
                slope_ths=0.35,
            )
            for item in raw_res_mr:
                if len(item) < 3:
                    continue
                poly_pts, text_val, conf = item
                clean_text = str(text_val).strip().translate(DEVANAGARI_DIGITS_MAP)
                if not clean_text or float(conf) < 0.20:
                    continue
                if is_devanagari(clean_text):
                    pts = np.array(poly_pts, dtype=np.float32)
                    orig_pts = pts / scale
                    x, y, w, h = cv2.boundingRect(orig_pts.astype(np.int32))
                    all_raw_boxes.append({
                        "text": clean_text,
                        "confidence": round(float(conf), 3),
                        "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                        "orientation": "0_mr"
                    })
            preprocessing_applied.append("marathi_scan")
        except Exception as mr_err:
            print(f"[OCR Engine] Marathi scan note: {mr_err}")

    # Deduplicate overlapping boxes: only drop if bounding boxes overlap AND text is same/similar
    all_raw_boxes.sort(key=lambda b: -b["confidence"])
    merged_boxes = []
    for b in all_raw_boxes:
        is_dupe = False
        for mb in merged_boxes:
            iou = _box_iou(b["bbox"], mb["bbox"])
            if iou > 0.40:
                t1, t2 = b["text"].lower(), mb["text"].lower()
                if t1 == t2 or SequenceMatcher(None, t1, t2).ratio() > 0.65:
                    is_dupe = True
                    break
        if not is_dupe:
            merged_boxes.append(b)

    # Sort merged boxes by reading order: top-to-bottom, left-to-right
    merged_boxes.sort(key=lambda b: (b["bbox"]["y"] // 40, b["bbox"]["x"]))

    # Construct clean multiline text
    text_lines = [b["text"] for b in merged_boxes]
    full_text = "\n".join(text_lines)
    mean_conf = float(np.mean([b["confidence"] for b in merged_boxes])) if merged_boxes else 0.0

    return {
        "text": full_text,
        "confidence": round(mean_conf, 3),
        "word_boxes": merged_boxes,
        "quality": quality_report,
        "preprocessing_applied": preprocessing_applied,
        "pass_selected": "multi_orientation_fusion",
        "scores": {
            "total_boxes": len(merged_boxes),
            "mean_confidence": round(mean_conf, 3),
        }
    }


def extract_text(
    image_input: Union[str, Path, np.ndarray],
    languages: Optional[List[str]] = None
) -> str:
    """
    Drop-in backward compatible wrapper returning multiline text string.
    """
    res = extract_text_adaptive(image_input, languages=languages)
    return res["text"]

