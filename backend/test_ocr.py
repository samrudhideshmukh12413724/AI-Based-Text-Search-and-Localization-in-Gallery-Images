"""First OCR checkpoint: read one image and print detected text."""

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# EasyOCR progress bars use Unicode; Windows console needs UTF-8.
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

from app.ocr import extract_text


def ensure_test_image(path: Path) -> None:
    if path.is_file():
        return

    image = Image.new("RGB", (640, 320), color="white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()

    y = 80
    for line in ("Government Scholarship", "Application 2026"):
        draw.text((60, y), line, fill="black", font=font)
        y += 60

    image.save(path, "JPEG", quality=95)


def main() -> None:
    image_path = Path(__file__).parent / "test.jpg"
    ensure_test_image(image_path)

    print(f"Running OCR on: {image_path.name}")
    print("-" * 40)

    text = extract_text(image_path)

    print("Detected text:")
    print(text if text else "(no text detected)")


if __name__ == "__main__":
    main()
