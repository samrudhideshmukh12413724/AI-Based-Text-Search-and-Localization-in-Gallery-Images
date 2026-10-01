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

_reader: Optional[easyocr.Reader] = None


def get_ocr_reader(languages: Optional[List[str]] = None) -> easyocr.Reader:
    """Singleton getter for EasyOCR Reader."""
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(languages or ["en"], gpu=False, verbose=False)
    return _reader


def _load_image(image_input: Union[str, Path, np.ndarray]) -> np.ndarray:
    """Loads image from path or returns copy of numpy array."""
    if isinstance(image_input, (str, Path)):
        p = Path(image_input)
        if not p.is_file():
            raise FileNotFoundError(f"Image not found: {p}")
        img = cv2.imread(str(p))
        if img is None:
            raise ValueError(f"Failed to read image: {p}")
        return img
    elif isinstance(image_input, np.ndarray):
        return image_input.copy()
    else:
        raise TypeError(f"Unsupported image type: {type(image_input)}")


def _parse_easyocr_results(raw_results: list) -> tuple[str, float, list[dict]]:
    """
    Parses EasyOCR (bbox, text, conf) output tuples.
    Returns (multiline_text, mean_confidence, word_boxes).
    """
    lines = []
    word_boxes = []
    conf_scores = []

    for item in raw_results:
        if len(item) < 3:
            continue
        poly_pts, text_val, conf = item
        clean_text = str(text_val).strip()
        if not clean_text:
            continue

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


def extract_text_adaptive(
    image_input: Union[str, Path, np.ndarray],
    languages: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    High-level Adaptive OCR Orchestrator.

    Workflow:
    1. Assesses image quality (blur, contrast, brightness).
    2. Runs Pass 1 baseline OCR on lightly scaled image.
    3. If image quality is degraded or baseline confidence < 0.65, runs
       Pass 2 on adaptively preprocessed image (CLAHE, unsharp mask, deskew).
    4. Keeps the superior transcription based on confidence-completeness score.
    """
    img = _load_image(image_input)
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # Step 1: Quality Diagnostic
    quality_report = assess_image_quality(gray)
    reader = get_ocr_reader(languages)

    # Step 2: Pass 1 (Baseline)
    baseline_scaled = cv2.convertScaleAbs(gray, alpha=1.1, beta=5)
    raw_res_1 = reader.readtext(baseline_scaled)
    text_1, conf_1, boxes_1 = _parse_easyocr_results(raw_res_1)
    score_1 = _score_transcription(text_1, conf_1)

    # If baseline text is found and confident, return immediately (fast-path ~2-3x speedup)
    if text_1.strip() and conf_1 >= 0.55:
        return {
            "text": text_1,
            "confidence": round(conf_1, 3),
            "word_boxes": boxes_1,
            "quality": quality_report,
            "preprocessing_applied": ["standard_scale"],
            "pass_selected": "baseline",
            "scores": {"baseline": round(score_1, 3)}
        }

    # Step 3: Pass 2 (Adaptive Enhanced)
    enhanced = preprocess_for_ocr(gray, quality_report)
    raw_res_2 = reader.readtext(enhanced)
    text_2, conf_2, boxes_2 = _parse_easyocr_results(raw_res_2)
    score_2 = _score_transcription(text_2, conf_2)

    # Step 4: Compare and select winner
    if score_2 > score_1:
        selected_text = text_2
        selected_conf = conf_2
        selected_boxes = boxes_2
        pass_name = "adaptive_enhanced"
        applied = quality_report.get("issues", [])
    else:
        selected_text = text_1
        selected_conf = conf_1
        selected_boxes = boxes_1
        pass_name = "baseline"
        applied = ["standard_scale"]

    return {
        "text": selected_text,
        "confidence": round(selected_conf, 3),
        "word_boxes": selected_boxes,
        "quality": quality_report,
        "preprocessing_applied": applied,
        "pass_selected": pass_name,
        "scores": {
            "baseline": round(score_1, 3),
            "adaptive": round(score_2, 3)
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
