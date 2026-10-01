"""Backward-compatible wrapper routing to the modular adaptive OCR engine."""

from pathlib import Path
from typing import Union, List, Dict, Any, Optional
import numpy as np

from app.ocr.ocr_engine import (
    extract_text as _extract_text,
    extract_text_adaptive as _extract_text_adaptive,
    get_ocr_reader
)


def extract_text(
    image_path: Union[str, Path, np.ndarray],
    languages: Optional[List[str]] = None
) -> str:
    """
    Legacy compatible text extraction interface.
    Delegates to the modular Adaptive Dual-Pass OCR Engine.
    """
    return _extract_text(image_path, languages=languages)


def extract_text_detailed(
    image_path: Union[str, Path, np.ndarray],
    languages: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Detailed OCR extraction returning text, confidence, word bounding boxes, and quality report.
    """
    return _extract_text_adaptive(image_path, languages=languages)

