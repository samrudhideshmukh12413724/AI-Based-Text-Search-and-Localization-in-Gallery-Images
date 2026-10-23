"""Dedicated Handwriting Recognition & Enhancement Engine.

Provides:
1. Classical ink-contrast stroke enhancement (bilateral filter + adaptive contrast)
   to isolate handwritten pen strokes from lined notebook or textured document backgrounds.
2. Handwriting-calibrated EasyOCR parameter profiles (higher slope tolerance, lower low_text,
   and adaptive cursive link thresholds).
3. Optional deep-learning Transformer handwriting recognition via Microsoft TrOCR
   (microsoft/trocr-small-handwritten) with lazy loading and graceful offline fallback.
4. Full Unicode Devanagari (Hindi/Marathi) and English text & bounding box preservation.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import cv2
import numpy as np


def enhance_handwritten_ink(img: np.ndarray) -> np.ndarray:
    """
    Isolates and enhances handwritten pen/pencil strokes:
    - Bilateral filtering removes paper fiber, ruled lines, and texture while preserving stroke edges.
    - CLAHE equalizes variable hand-pressure across words.
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # Bilateral filter preserves sharp ink edges while smoothing textured paper
    filtered = cv2.bilateralFilter(gray, d=7, sigmaColor=45, sigmaSpace=45)

    # Local adaptive contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8))
    enhanced = clahe.apply(filtered)

    return enhanced


def read_handwriting_with_easyocr(
    reader,
    enhanced_gray: np.ndarray,
    scale: float = 1.0,
    devanagari_digits_map: Optional[dict] = None,
) -> List[Dict[str, Any]]:
    """
    Executes EasyOCR using handwriting-calibrated thresholds.
    Tolerates slanted cursive text, uneven stroke weights, and wavy baselines.
    """
    boxes = []
    try:
        raw_res = reader.readtext(
            enhanced_gray,
            text_threshold=0.18,   # Capture lighter pen strokes
            low_text=0.08,         # Lower bound for faint cursive loops
            link_threshold=0.32,   # Connect disconnected handwritten cursive strokes
            slope_ths=0.75,        # Tolerate steep handwriting slants
            width_ths=0.85,        # Accommodate wide handwriting character spacing
            contrast_ths=0.03,
            adjust_contrast=0.7,
        )
        for item in raw_res:
            if len(item) < 3:
                continue
            poly_pts, text_val, conf = item
            raw_text = str(text_val).strip()
            if devanagari_digits_map:
                raw_text = raw_text.translate(devanagari_digits_map)
            if not raw_text or float(conf) < 0.12:
                continue

            pts = np.array(poly_pts, dtype=np.float32)
            orig_pts = pts / scale
            x, y, w, h = cv2.boundingRect(orig_pts.astype(np.int32))

            boxes.append({
                "text": raw_text,
                "confidence": round(float(conf), 3),
                "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                "is_handwritten": True,
            })
    except Exception as e:
        print(f"[Handwriting Engine] EasyOCR error: {e}")
    return boxes


_trocr_instance = None


class TrOCRRecognizer:
    """Lazy-loaded Microsoft TrOCR handwriting transcription model."""

    def __init__(self, model_name: str = "microsoft/trocr-small-handwritten"):
        self.model_name = model_name
        self.processor = None
        self.model = None
        self._load_attempted = False
        self._available = False

    def ensure_loaded(self) -> bool:
        if self._load_attempted:
            return self._available
        self._load_attempted = True
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            import torch

            print(f"[TrOCR] Loading handwriting model '{self.model_name}' on CPU...")
            self.processor = TrOCRProcessor.from_pretrained(self.model_name)
            self.model = VisionEncoderDecoderModel.from_pretrained(self.model_name)
            self.model.eval()
            self._available = True
            print("[TrOCR] Successfully loaded handwriting model.")
        except Exception as e:
            print(f"[TrOCR] Model not loaded (using EasyOCR handwriting pipeline): {e}")
            self._available = False
        return self._available

    def recognize_crop(self, crop_bgr: np.ndarray) -> Optional[str]:
        """Transcribes a cropped handwritten line/word using Vision-Encoder-Decoder."""
        if not self.ensure_loaded() or crop_bgr is None or crop_bgr.size == 0:
            return None
        try:
            from PIL import Image as PILImg
            import torch

            rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
            pil_img = PILImg.fromarray(rgb)
            pixel_values = self.processor(images=pil_img, return_tensors="pt").pixel_values

            with torch.no_grad():
                generated_ids = self.model.generate(pixel_values, max_new_tokens=32)

            pred_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return pred_text.strip()
        except Exception as e:
            print(f"[TrOCR] Inference error on crop: {e}")
            return None


def get_trocr_recognizer() -> TrOCRRecognizer:
    global _trocr_instance
    if _trocr_instance is None:
        _trocr_instance = TrOCRRecognizer()
    return _trocr_instance
