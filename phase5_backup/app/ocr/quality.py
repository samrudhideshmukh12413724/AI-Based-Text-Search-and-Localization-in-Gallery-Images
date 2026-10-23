"""Image Quality Assessment Module for Adaptive OCR.

Measures blur, brightness, contrast, and dynamic range to determine
whether image preprocessing (CLAHE, unsharp mask, gamma correction)
is required before OCR.
"""

from pathlib import Path
from typing import Union, Dict, Any
import cv2
import numpy as np


def assess_image_quality(image_input: Union[str, Path, np.ndarray]) -> Dict[str, Any]:
    """
    Evaluates blurriness, contrast, brightness, and dynamic range of an image.

    Returns:
        Dict with metrics and a boolean flag 'needs_preprocessing'.
    """
    if isinstance(image_input, (str, Path)):
        p = Path(image_input)
        if not p.is_file():
            raise FileNotFoundError(f"Image not found: {p}")
        img = cv2.imread(str(p))
        if img is None:
            raise ValueError(f"Failed to decode image: {p}")
    elif isinstance(image_input, np.ndarray):
        img = image_input
    else:
        raise TypeError(f"Expected str, Path, or np.ndarray, got {type(image_input)}")

    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # 1. Blur Detection (Variance of Laplacian)
    # Lower value means fewer high-frequency edges (blurry)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    blur_variance = float(laplacian.var())

    # 2. Brightness (Mean Pixel Luminance)
    brightness = float(np.mean(gray))

    # 3. Global Contrast (Standard Deviation of Intensities)
    contrast = float(np.std(gray))

    # 4. Dynamic Range (95th percentile - 5th percentile)
    p5, p95 = np.percentile(gray, (5, 95))
    dynamic_range = float(p95 - p5)

    # Diagnostic Thresholds
    is_blurry = blur_variance < 100.0
    is_dark = brightness < 60.0
    is_overexposed = brightness > 215.0
    is_low_contrast = contrast < 42.0 or dynamic_range < 75.0

    issues = []
    if is_blurry:
        issues.append("blurry")
    if is_dark:
        issues.append("dark")
    if is_overexposed:
        issues.append("overexposed")
    if is_low_contrast:
        issues.append("low_contrast")

    needs_preprocessing = len(issues) > 0

    return {
        "blur_variance": round(blur_variance, 2),
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "dynamic_range": round(dynamic_range, 2),
        "is_blurry": is_blurry,
        "is_dark": is_dark,
        "is_overexposed": is_overexposed,
        "is_low_contrast": is_low_contrast,
        "needs_preprocessing": needs_preprocessing,
        "issues": issues,
    }
