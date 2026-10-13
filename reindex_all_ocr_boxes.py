"""Re-index OCR Word Bounding Boxes for All Existing Images in SQLite Database."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import database
from app.ocr.ocr_engine import extract_text_adaptive

def reindex_boxes():
    database.init_db()
    images = database.list_images()
    print(f"Re-indexing OCR word bounding boxes for {len(images)} stored images...")

    updated_count = 0
    for img in images:
        img_id = img["id"]
        img_path = img["image_path"]
        if Path(img_path).exists():
            try:
                ocr_res = extract_text_adaptive(img_path)
                word_boxes = ocr_res.get("word_boxes", [])
                if word_boxes:
                    database.update_image_ocr_boxes(img_id, word_boxes)
                    updated_count += 1
                    print(f"  [+] Image ID {img_id} ({img['image_name']}): Saved {len(word_boxes)} word bounding boxes.")
            except Exception as e:
                print(f"  [-] Image ID {img_id} failed: {e}")

    print(f"\nSuccessfully populated OCR word bounding boxes for {updated_count} / {len(images)} images!")

if __name__ == "__main__":
    reindex_boxes()
