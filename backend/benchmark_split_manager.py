"""Benchmark Split Manager & Stratified Ingestion Engine.
Partitions the 259+ diverse document corpus into reproducible 70% Dev / 15% Val / 15% Unseen Test splits,
ingests the expanded dataset into SQLite images.db, runs EasyOCR and OpenCV region extraction,
computes CLIP ViT-B/32 crop embeddings, and updates the MiniLM semantic vector store.
"""

import io
import json
import random
import shutil
import sqlite3
import sys
import time
from pathlib import Path

# Ensure UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent
AI_SEARCH_DIR = ROOT_DIR.parent
DATASET_DIR = AI_SEARCH_DIR / "dataset"
UPLOADS_DIR = AI_SEARCH_DIR / "uploads"
DB_PATH = AI_SEARCH_DIR / "database" / "images.db"

# Sub-dataset folders
CAT_DIRS = {
    "SYNTHETIC_ID": DATASET_DIR / "synthetic_ids",
    "HANDWRITTEN": DATASET_DIR / "handwritten",
    "SIGNATURE": DATASET_DIR / "signatures_expanded",
    "STAMP": DATASET_DIR / "stamps_expanded",
    "COMPOSITE": DATASET_DIR / "composites_expanded",
    "NEGATIVE": DATASET_DIR / "negatives_expanded",
}

def partition_corpus(seed=42):
    random.seed(seed)
    all_categorized = {cat: [] for cat in CAT_DIRS}

    # Collect files per category
    for cat, p in CAT_DIRS.items():
        if p.exists():
            files = sorted([f for f in p.glob("*.jpg")])
            all_categorized[cat] = files

    manifest = {
        "seed": seed,
        "splits": {
            "dev": {},
            "val": {},
            "test": {}
        },
        "stats": {}
    }

    dev_all = []
    val_all = []
    test_all = []

    for cat, flist in all_categorized.items():
        shuffled = list(flist)
        random.shuffle(shuffled)
        n = len(shuffled)
        n_test = max(1, int(n * 0.15))
        n_val = max(1, int(n * 0.15))
        n_dev = n - n_test - n_val

        dev_files = [f.name for f in shuffled[:n_dev]]
        val_files = [f.name for f in shuffled[n_dev:n_dev + n_val]]
        test_files = [f.name for f in shuffled[n_dev + n_val:]]

        manifest["splits"]["dev"][cat] = dev_files
        manifest["splits"]["val"][cat] = val_files
        manifest["splits"]["test"][cat] = test_files

        dev_all.extend(dev_files)
        val_all.extend(val_files)
        test_all.extend(test_files)

        manifest["stats"][cat] = {
            "total": n,
            "dev_count": len(dev_files),
            "val_count": len(val_files),
            "test_count": len(test_files)
        }

    total_expanded = len(dev_all) + len(val_all) + len(test_all)
    manifest["stats"]["TOTAL_EXPANDED"] = total_expanded
    manifest["stats"]["DEV_TOTAL"] = len(dev_all)
    manifest["stats"]["VAL_TOTAL"] = len(val_all)
    manifest["stats"]["TEST_TOTAL"] = len(test_all)

    out_json = DATASET_DIR / "benchmark_split_manifest.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Stratified partition created at {out_json}")
    print(f"  -> Development (70%): {len(dev_all)} documents")
    print(f"  -> Validation  (15%): {len(val_all)} documents")
    print(f"  -> Test Unseen (15%): {len(test_all)} documents")
    return manifest

def ingest_all_into_system():
    print("\n" + "=" * 90)
    print("INGESTING EXPANDED DATASETS INTO RETRIEVAL ENGINE (OCR + REGIONS + CLIP + MINILM)")
    print("=" * 90)

    from app.ocr import extract_text
    from app.visual_search import get_visual_search_engine
    from app.semantic_search import build_embeddings_index
    from app import database

    v_engine = get_visual_search_engine()

    total_ingested = 0
    total_regions = 0

    # Collect all images across all category folders
    all_files = []
    for cat, p in CAT_DIRS.items():
        if p.exists():
            for f in sorted(p.glob("*.jpg")):
                all_files.append((cat, f))

    print(f"Found {len(all_files)} documents to ingest...")

    for idx, (cat, fpath) in enumerate(all_files, 1):
        target_upload = UPLOADS_DIR / fpath.name
        if not target_upload.exists() or target_upload.stat().st_size != fpath.stat().st_size:
            shutil.copy2(fpath, target_upload)

        # Step 1: Run EasyOCR
        t0 = time.time()
        try:
            raw_text = extract_text(target_upload)
            clean_text = raw_text.strip() if raw_text else "(no text detected)"
        except Exception as e:
            raw_text = f"{cat} document"
            clean_text = raw_text

        # Step 2: Save to images table
        saved = database.save_image(
            image_name=fpath.name,
            image_path=str(target_upload.resolve()),
            extracted_text=clean_text,
            original_ocr_text=raw_text,
            cleaned_text=clean_text,
            category=cat,
            has_visual_objects=1 if cat != "NEGATIVE" else 0,
            visual_metadata={"category": cat},
        )
        img_id = saved["id"]

        # Step 3: Extract & Index Visual Regions via CLIP
        reg_count = 0
        if cat != "NEGATIVE":
            reg_count = v_engine.index_document(img_id, fpath.name, str(target_upload.resolve()))
        total_regions += reg_count
        total_ingested += 1
        dt = time.time() - t0
        print(f"  [{idx:03d}/{len(all_files)}] Ingested {fpath.name} | OCR: {len(clean_text)} chars | Regions: {reg_count} ({dt:.2f}s)")

    # Step 4: Refresh MiniLM Semantic Index
    print("\nRefreshing Dense Semantic MiniLM Vector Index...")
    build_embeddings_index()

    print("\n" + "=" * 90)
    print(f"INGESTION COMPLETE: {total_ingested} documents indexed with {total_regions} visual region crops!")
    print("=" * 90)

if __name__ == "__main__":
    partition_corpus()
    ingest_all_into_system()
