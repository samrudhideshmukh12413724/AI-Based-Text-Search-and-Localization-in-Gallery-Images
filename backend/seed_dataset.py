"""Generate dataset images and index them with OCR into SQLite."""

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")

from app import database
from app.ocr import extract_text

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "dataset"
UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"

SAMPLES = {
    "scholarship.jpg": ["Government Scholarship", "Application 2026"],
    "admission.jpg": ["College Admission Form", "2026"],
    "exam.jpg": ["Semester Examination", "Notice"],
    "timetable.jpg": ["Class Timetable", "Spring 2026"],
    "library.jpg": ["Library Opening Hours", "Monday to Saturday"],
    "fees.jpg": ["Fee Payment Deadline", "March 2026"],
    "registration.jpg": ["Student Registration", "Portal Open"],
    "hostel.jpg": ["Hostel Allocation", "Notice 2026"],
    "notice.jpg": ["Important College Notice", "All Students"],
    "application.jpg": ["Online Application Form", "Apply Now"],
}


def _font(size: int = 34):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def create_dataset() -> None:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    for filename, lines in SAMPLES.items():
        path = DATASET_DIR / filename
        image = Image.new("RGB", (700, 320), color="white")
        draw = ImageDraw.Draw(image)
        font = _font()
        y = 70
        for line in lines:
            draw.text((50, y), line, fill="black", font=font)
            y += 70
        image.save(path, "JPEG", quality=95)


def index_dataset() -> None:
    database.init_db()
    for filename in SAMPLES:
        src = DATASET_DIR / filename
        dest = UPLOADS_DIR / filename
        shutil_copy = not dest.exists() or dest.stat().st_size != src.stat().st_size
        if shutil_copy:
            dest.write_bytes(src.read_bytes())

        text = extract_text(dest)
        if not text.strip():
            text = " ".join(SAMPLES[filename])

        database.save_image(filename, str(dest), text)
        print(f"Indexed {filename}: {text.replace(chr(10), ' ')}")


if __name__ == "__main__":
    print("Creating dataset images...")
    create_dataset()
    print("Running OCR and saving to SQLite...")
    index_dataset()
    print("Done.")
