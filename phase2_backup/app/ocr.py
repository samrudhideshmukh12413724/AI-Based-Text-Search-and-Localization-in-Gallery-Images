"""Extract text from an image using OpenCV preprocessing + EasyOCR."""

from pathlib import Path

import cv2
import easyocr
import numpy as np

_reader: easyocr.Reader | None = None


def _get_reader(languages: list[str] | None = None) -> easyocr.Reader:
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(languages or ["en"], gpu=False, verbose=False)
    return _reader


def _load_image(image_path: Path) -> np.ndarray:
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Image not found or unreadable: {image_path}")
    return image


def extract_text(image_path: str | Path, languages: list[str] | None = None) -> str:
    """
    Read text from an image file.

    OpenCV loads the image; EasyOCR performs text recognition.
    """
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")

    image = _load_image(path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    enhanced = cv2.convertScaleAbs(gray, alpha=1.2, beta=10)

    reader = _get_reader(languages)
    results = reader.readtext(enhanced)

    lines = [text.strip() for _, text, _ in results if text.strip()]
    return "\n".join(lines)
