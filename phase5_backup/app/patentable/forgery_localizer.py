"""PATENTABLE INNOVATION 2 (2026): Real-Time Spatial Forgery Field Localization Engine.

Combines JPEG Error Level Analysis (ELA) variance maps with OCR word bounding boxes
to pinpoint specific forged, photoshopped, or digitally manipulated text fields.
"""

import io
from pathlib import Path
from typing import Union, Dict, Any, List
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance


def localize_forged_text_fields(image_input: Union[str, Path, np.ndarray], word_boxes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Overlays ELA pixel variance onto OCR word bounding boxes to locate specific forged text fields.
    """
    try:
        if isinstance(image_input, (str, Path)):
            p = Path(image_input)
            if not p.is_file():
                return {"is_analyzed": False, "forged_fields": []}
            orig_img = Image.open(p).convert("RGB")
        elif isinstance(image_input, np.ndarray):
            rgb_arr = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
            orig_img = Image.fromarray(rgb_arr)
        else:
            return {"is_analyzed": False, "forged_fields": []}

        # 1. Compute ELA difference map
        buf = io.BytesIO()
        orig_img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        resaved_img = Image.open(buf)

        ela_img = ImageChops.difference(orig_img, resaved_img)
        ela_np = np.array(ela_img)
        gray_ela = cv2.cvtColor(ela_np, cv2.COLOR_RGB2GRAY)

        img_h, img_w = gray_ela.shape[:2]
        global_mean = float(np.mean(gray_ela))
        global_std = float(np.std(gray_ela))

        forged_fields: List[Dict[str, Any]] = []

        # 2. Evaluate ELA error variance inside each OCR word bounding box
        for box in word_boxes:
            text = box.get("text", "")
            bbox = box.get("bbox", {})
            x = bbox.get("x", 0)
            y = bbox.get("y", 0)
            w = bbox.get("width", 0)
            h = bbox.get("height", 0)

            if w > 0 and h > 0 and x >= 0 and y >= 0 and (x + w) <= img_w and (y + h) <= img_h:
                roi = gray_ela[y:y+h, x:x+w]
                if roi.size > 0:
                    roi_mean = float(np.mean(roi))
                    roi_max = float(np.max(roi))

                    # Localized error variance significantly above global mean indicates photo edit / manipulation
                    if roi_mean > global_mean + 1.8 * global_std or roi_max > 180.0:
                        suspicion_level = "HIGH" if roi_max > 200.0 else "MEDIUM"
                        forged_fields.append({
                            "text": text,
                            "bbox": bbox,
                            "local_error_mean": round(roi_mean, 2),
                            "local_error_max": round(roi_max, 2),
                            "suspicion_level": suspicion_level,
                            "reason": f"Localized pixel error spike ({roi_mean:.1f} > global avg {global_mean:.1f})",
                        })

        return {
            "is_analyzed": True,
            "total_words_inspected": len(word_boxes),
            "forged_fields_detected_count": len(forged_fields),
            "forged_fields": forged_fields,
            "status": "FORGERY_SUSPECTS_FOUND" if forged_fields else "NO_FORGERY_DETECTED",
        }
    except Exception as e:
        return {"is_analyzed": False, "error": str(e), "forged_fields": []}
