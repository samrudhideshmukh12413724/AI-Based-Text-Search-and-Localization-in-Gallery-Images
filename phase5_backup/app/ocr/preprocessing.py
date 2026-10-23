"""Targeted Image Preprocessing for Adaptive OCR.

Applies OpenCV computer vision filters (CLAHE, unsharp masking,
gamma correction, and deskewing) tailored specifically to issues
diagnosed by the quality assessment module.
"""

from pathlib import Path
from typing import Union, Optional, Dict, Any
import cv2
import numpy as np

from app.ocr.quality import assess_image_quality


def adjust_gamma(gray_img: np.ndarray, gamma: float = 0.6) -> np.ndarray:
    """
    Non-linear gamma correction.
    gamma < 1.0 brightens dark images; gamma > 1.0 darkens washed-out images.
    """
    clamped_gamma = max(gamma, 0.01)
    table = np.array([((i / 255.0) ** clamped_gamma) * 255 for i in range(256)]).astype(np.uint8)
    return cv2.LUT(gray_img, table)


def apply_clahe(
    gray_img: np.ndarray,
    clip_limit: float = 2.5,
    tile_grid_size: tuple[int, int] = (8, 8)
) -> np.ndarray:
    """
    Contrast Limited Adaptive Histogram Equalization.
    Normalizes dynamic range if compressed, then enhances local contrast.
    """
    min_val, max_val = float(np.min(gray_img)), float(np.max(gray_img))
    if (max_val - min_val) < 180 and (max_val - min_val) > 5:
        norm = cv2.normalize(gray_img, None, 0, 255, cv2.NORM_MINMAX)
    else:
        norm = gray_img
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    return clahe.apply(norm)


def unsharp_mask(
    gray_img: np.ndarray,
    sigma: float = 1.2,
    strength: float = 1.5
) -> np.ndarray:
    """
    Unsharp masking to sharpen blurry text contours and character edges.
    Formula: Sharp = Original + strength * (Original - GaussianBlur)
    """
    blurred = cv2.GaussianBlur(gray_img, (0, 0), sigma)
    sharpened = cv2.addWeighted(gray_img, 1.0 + strength, blurred, -strength, 0)
    return sharpened


def deskew(gray_img: np.ndarray, max_angle: float = 15.0) -> np.ndarray:
    """
    Detects document orientation skew and rotates to align text horizontally.
    Only corrects slight rotations (|angle| between 1.0 and max_angle degrees).
    """
    # Threshold to find text contours
    thresh = cv2.adaptiveThreshold(
        gray_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 8
    )
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 100:
        return gray_img

    rect = cv2.minAreaRect(coords)
    angle = rect[-1]

    # Convert OpenCV minAreaRect angle to horizontal deviation
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Only deskew if rotation is meaningful and within safe bounds
    if abs(angle) < 1.0 or abs(angle) > max_angle:
        return gray_img

    (h, w) = gray_img.shape[:2]
    center = (w // 2, h // 2)
    m = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        gray_img, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return rotated


def preprocess_for_ocr(
    image_input: Union[str, Path, np.ndarray],
    quality_report: Optional[Dict[str, Any]] = None
) -> np.ndarray:
    """
    Applies adaptive corrections based on image quality diagnostic.

    Returns:
        Enhanced grayscale image optimized for EasyOCR text recognition.
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
        gray = img.copy()

    # If no report passed, assess quality on the fly
    if quality_report is None:
        quality_report = assess_image_quality(gray)

    issues = quality_report.get("issues", [])

    # If quality is clean and requires no preprocessing, return lightly normalized image
    if not issues:
        # Standard light normalization
        return cv2.convertScaleAbs(gray, alpha=1.1, beta=5)

    # Sequence of targeted adaptive enhancements
    processed = gray.copy()

    # 1. Dark Image Correction
    if "dark" in issues:
        processed = adjust_gamma(processed, gamma=0.55)

    # 2. Overexposed Image Correction
    elif "overexposed" in issues:
        processed = adjust_gamma(processed, gamma=1.35)

    # 3. Contrast Enhancement (CLAHE) for low contrast or dark images
    if "low_contrast" in issues or "dark" in issues:
        processed = apply_clahe(processed, clip_limit=2.5, tile_grid_size=(8, 8))

    # 4. Blur Sharpness Restoration (Unsharp Mask)
    if "blurry" in issues:
        processed = unsharp_mask(processed, sigma=1.2, strength=1.5)

    # 5. Orientation Deskewing
    processed = deskew(processed)

    return processed
