"""Ingests composite multi-modal benchmark documents into SQLite, uploads, and CLIP index."""

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
from app.visual_search import get_visual_search_engine
from app.semantic_search import build_embeddings_index

UPLOADS_DIR = ROOT_DIR.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
COMPOSITE_DIR = ROOT_DIR.parent / "dataset" / "composite"

def ingest_composite_dataset():
    print("=" * 85)
    print("INGESTING COMPOSITE MULTI-MODAL DATASET (AADHAAR, ID CARD, SIGNATURES)")
    print("=" * 85)

    database.init_db()
    detector = get_visual_detector()
    v_search = get_visual_search_engine()

    doc_files = sorted(COMPOSITE_DIR.glob("*.jpg"))
    print(f"Found {len(doc_files)} composite benchmark documents in {COMPOSITE_DIR}\n")

    for img_path in doc_files:
        dest_path = UPLOADS_DIR / img_path.name
        shutil.copy(img_path, dest_path)

        # 1. OCR Extraction
        text = extract_text(dest_path)
        if not text.strip():
            text = "(no text detected)"

        # 2. Visual Detection (QR/structural)
        vis_res = detector.detect_visual_objects(dest_path)
        has_vis = 1 if vis_res.get("detected") else 0

        # 3. Save to DB
        row = database.save_image(
            image_name=img_path.name,
            image_path=str(dest_path.resolve()),
            extracted_text=text,
            original_ocr_text=text,
            cleaned_text=text,
            category="COMPOSITE",
            has_visual_objects=has_vis,
            visual_metadata=vis_res,
        )

        # 4. Extract & Index Visual Regions via CLIP
        reg_count = v_search.index_document(row["id"], img_path.name, str(dest_path))

        print(f"  [Indexed] {img_path.name} (ID: {row['id']}) | Regions indexed: {reg_count}")
        print(f"     OCR text snippet: {text[:80]}...")

    # 5. Refresh Semantic Vectors Index
    print("\nRefreshing dense semantic embeddings index...")
    build_embeddings_index()
    print("=" * 85)
    print("INGESTION & INDEXING COMPLETE!")
    print("=" * 85)

if __name__ == "__main__":
    ingest_composite_dataset()
