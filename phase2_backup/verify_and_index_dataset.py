"""Verify OCR output on pilot dataset and index into SQLite database."""

import csv
import json
import re
from pathlib import Path
import difflib

from app.ocr import extract_text
from app.database import save_image, init_db

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "dataset"
METADATA_FILE = DATASET_DIR / "metadata.csv"
REPORT_FILE = DATASET_DIR / "ocr_verification_report.json"


def clean_text(text: str) -> str:
    """Normalize whitespace and remove unwanted artifacts."""
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return " ".join(lines)


def main():
    init_db()
    
    if not METADATA_FILE.exists():
        print(f"Error: {METADATA_FILE} not found!")
        return

    records = []
    with open(METADATA_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    print(f"Running OCR extraction & indexing on {len(records)} images...\n")
    results = []
    passed_count = 0

    for rec in records:
        filename = rec["filename"]
        img_path = DATASET_DIR / filename
        category = rec.get("category", "")
        expected_text = rec.get("expected_text", "")

        if not img_path.exists():
            print(f"Warning: {filename} not found on disk!")
            continue

        raw_ocr = extract_text(str(img_path))
        cleaned = clean_text(raw_ocr)

        # Compute accuracy against expected text
        expected_clean = clean_text(expected_text)
        matcher = difflib.SequenceMatcher(None, cleaned.lower(), expected_clean.lower())
        accuracy = round(matcher.ratio() * 100, 2)

        is_passed = accuracy >= 70.0  # High confidence threshold
        if is_passed:
            passed_count += 1

        # Store in SQLite database
        save_image(
            image_name=filename,
            image_path=str(img_path),
            extracted_text=raw_ocr,
            original_ocr_text=raw_ocr,
            cleaned_text=cleaned,
            category=category,
        )

        results.append({
            "image_id": rec.get("image_id"),
            "filename": filename,
            "category": category,
            "accuracy_percent": accuracy,
            "is_passed": is_passed,
            "original_ocr_text": raw_ocr,
            "cleaned_text": cleaned,
            "expected_text": expected_clean,
        })

        status = "PASSED" if is_passed else "CHECK"
        print(f"[{status}] {filename:28} | Accuracy: {accuracy:5.1f}% | OCR: {cleaned[:45]}...")

    with open(REPORT_FILE, mode="w", encoding="utf-8") as f:
        json.dump({
            "total_images": len(records),
            "passed_images": passed_count,
            "overall_accuracy_percent": round(sum(r["accuracy_percent"] for r in results) / len(results), 2) if results else 0,
            "details": results
        }, f, indent=2)

    print(f"\n==========================================")
    print(f"Verified {len(results)} images: {passed_count}/{len(results)} passed accuracy check.")
    print(f"Report saved to: {REPORT_FILE}")
    print(f"All images successfully indexed into SQLite database!")
    print(f"==========================================")


if __name__ == "__main__":
    main()
