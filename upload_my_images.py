"""
Helper script to upload and index your own custom images into the AI Image Search database.
Usage:
    python upload_my_images.py path/to/your/image.jpg
    python upload_my_images.py path/to/folder_with_images/
"""

import sys
import os
import requests
from pathlib import Path

BACKEND_URL = "http://127.0.0.1:8000"
SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp"}

def upload_single_image(file_path: Path):
    if not file_path.exists():
        print(f"[ERROR] File does not exist: {file_path}")
        return False

    print(f"\n========================================================")
    print(f" Uploading & Indexing: {file_path.name}")
    print(f"========================================================")

    url = f"{BACKEND_URL}/upload"
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "image/jpeg")}
        try:
            res = requests.post(url, files=files, timeout=180)
        except requests.exceptions.ConnectionError:
            print("[ERROR] Could not connect to backend server at http://127.0.0.1:8000")
            print("        Please ensure the backend is running (run start_backend.bat)")
            return False

    if res.status_code >= 400:
        print(f"[FAILED] HTTP {res.status_code}: {res.text}")
        return False

    data = res.json()
    image_id = data.get("id")
    safe_name = data.get("filename")
    ocr_text = data.get("text", "") or data.get("extracted_text", "")
    vis_summary = data.get("visual_summary", "None")

    print(f"[SUCCESS] Indexed into Database with ID: {image_id}")
    print(f"  - Stored As      : {safe_name}")
    print(f"  - Visual Objects : {vis_summary}")
    print(f"  - OCR Text Snippet:")
    print("    " + "-"*40)
    for line in ocr_text.strip().split("\n")[:6]:
        print(f"    | {line}")
    if len(ocr_text.strip().split("\n")) > 6:
        print(f"    | ... ({len(ocr_text.strip().splitlines()) - 6} more lines)")
    print("    " + "-"*40)
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python upload_my_images.py <image_path_or_folder>")
        print("\nExample:")
        print("  python upload_my_images.py C:\\Users\\deshm\\Pictures\\my_certificate.jpg")
        return

    target = Path(sys.argv[1]).resolve()
    if target.is_dir():
        image_files = [p for p in target.iterdir() if p.suffix.lower() in SUPPORTED_EXT]
        if not image_files:
            print(f"No image files found in folder: {target}")
            return
        print(f"Found {len(image_files)} image(s) to index...")
        success = 0
        for img in image_files:
            if upload_single_image(img):
                success += 1
        print(f"\nFinished! Successfully indexed {success}/{len(image_files)} image(s).")
    else:
        upload_single_image(target)

if __name__ == "__main__":
    main()
