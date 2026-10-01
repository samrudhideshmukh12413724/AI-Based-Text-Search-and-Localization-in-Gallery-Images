import sys
import io
import shutil
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from app import database
from app.ocr import extract_text
from app.visual_detector import get_visual_detector
from app.semantic_search import build_embeddings_index

UPLOADS_DIR = ROOT_DIR / "uploads"
PHASE3_DATASET = ROOT_DIR.parent / "dataset" / "phase3"

def ingest_phase3_dataset():
    print("=" * 85)
    print("INGESTING PHASE 3 DATASET INTO SQLITE & VECTOR INDEX")
    print("=" * 85)

    database.init_db()
    detector = get_visual_detector()

    categories = ["positive", "negative", "multi_qr", "difficult"]
    total_ingested = 0

    for cat in categories:
        folder = PHASE3_DATASET / cat
        if not folder.exists():
            continue

        for img_path in sorted(folder.glob("*.jpg")):
            dest_path = UPLOADS_DIR / img_path.name
            shutil.copy(img_path, dest_path)

            # 1. OCR
            text = extract_text(dest_path)
            if not text.strip():
                text = "(no text detected)"

            # 2. Visual Detection
            vis_res = detector.detect_visual_objects(dest_path)
            has_vis = 1 if vis_res.get("detected") else 0

            # 3. Save to DB
            row = database.save_image(
                image_name=img_path.name,
                image_path=str(dest_path),
                extracted_text=text,
                original_ocr_text=text,
                cleaned_text=text,
                category=cat.upper(),
                has_visual_objects=has_vis,
                visual_metadata=vis_res,
            )

            total_ingested += 1
            obj_cnt = vis_res.get("count", 0)
            print(f"  [{cat.upper():<9}] {img_path.name:<36} -> OCR: {len(text):4d} chars | QR: {obj_cnt} found")

    print("\nRebuilding Vector Embeddings Index...")
    indexed_count = build_embeddings_index()
    print(f"Successfully Indexed {indexed_count} total documents in embeddings database.")
    print("=" * 85)

if __name__ == "__main__":
    ingest_phase3_dataset()
