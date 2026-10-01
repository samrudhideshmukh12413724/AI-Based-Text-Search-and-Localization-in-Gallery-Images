"""OCR package public interface."""

from app.ocr.ocr_engine import (
    extract_text,
    extract_text_adaptive as extract_text_detailed,
    get_ocr_reader
)

__all__ = ["extract_text", "extract_text_detailed", "get_ocr_reader"]
