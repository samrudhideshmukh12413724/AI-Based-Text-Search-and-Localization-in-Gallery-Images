"""Document Tampering & Photo Edit Detection Module (Error Level Analysis - ELA).

Performs Error Level Analysis (ELA) to detect digital manipulation, photoshopped text,
cloned pixels, or spliced regions in uploaded document images.
"""

import io
from pathlib import Path
from typing import Union, Dict, Any
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance


def analyze_document_tampering(image_input: Union[str, Path, np.ndarray], quality: int = 90) -> Dict[str, Any]:
    """
    Performs JPEG Error Level Analysis (ELA) to detect photoshopped or edited image areas.
    
    1. Saves image in-memory at a fixed JPEG compression quality (default 90%).
    2. Computes pixel-by-pixel absolute difference (Error Level) between original and resaved image.
    3. Scales the error difference to produce an ELA heatmap.
    4. Computes a tamper suspicion score based on local error variance spikes.
    """
    try:
        # Load image into PIL Image format
        if isinstance(image_input, (str, Path)):
            p = Path(image_input)
            if not p.is_file():
                return {"is_analyzed": False, "tamper_score": 0.0, "status": "FILE_NOT_FOUND"}
            orig_img = Image.open(p).convert("RGB")
        elif isinstance(image_input, np.ndarray):
            rgb_arr = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
            orig_img = Image.fromarray(rgb_arr)
        else:
            return {"is_analyzed": False, "tamper_score": 0.0, "status": "INVALID_INPUT"}

        # 1. Save at target JPEG quality in memory
        buffer = io.BytesIO()
        orig_img.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)
        resaved_img = Image.open(buffer)

        # 2. Compute absolute difference (ELA)
        ela_img = ImageChops.difference(orig_img, resaved_img)

        # 3. Calculate error metrics
        extrema = ela_img.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        if max_diff == 0:
            max_diff = 1

        scale = 255.0 / max_diff
        enhanced_ela = ImageEnhance.Brightness(ela_img).enhance(scale)

        # Convert to numpy array to compute variance & suspicious localized edit spikes
        ela_np = np.array(enhanced_ela)
        mean_error = float(np.mean(ela_np))
        std_error = float(np.std(ela_np))
        max_error = float(np.max(ela_np))

        # Higher standard deviation and maximum error spikes indicate localized manipulation (e.g. edited text)
        tamper_score = min(1.0, round((std_error * 1.8 + (max_error / 255.0) * 30.0) / 100.0, 3))
        is_suspicious = tamper_score >= 0.55

        return {
            "is_analyzed": True,
            "tamper_score": tamper_score,
            "is_suspicious": is_suspicious,
            "status": "SUSPICIOUS_EDITS_DETECTED" if is_suspicious else "ORIGINAL_UNALTERED",
            "mean_error": round(mean_error, 2),
            "std_error": round(std_error, 2),
            "max_error": round(max_error, 2),
        }
    except Exception as e:
        return {"is_analyzed": False, "tamper_score": 0.0, "status": f"ERROR: {str(e)}"}
