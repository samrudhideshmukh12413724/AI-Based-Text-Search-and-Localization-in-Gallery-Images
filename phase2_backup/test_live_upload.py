"""Test dynamic end-to-end image upload pipeline: Upload -> OCR -> SQLite -> Embedding Index -> Instant Search."""

import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_dynamic_test_image() -> bytes:
    width, height = 750, 480
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(180, 50, 50), width=3)
    draw.rectangle([(25, 25), (width - 25, 80)], fill=(255, 240, 240))

    try:
        font_title = ImageFont.truetype("arial.ttf", 24)
        font_sub = ImageFont.truetype("arial.ttf", 18)
        font_body = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_body = ImageFont.load_default()

    draw.text((45, 38), "Student Internship Opportunity", fill=(160, 20, 20), font=font_title)
    draw.text((45, 110), "Summer Technical Training 2026", fill=(40, 40, 40), font=font_sub)
    draw.text((45, 180), "Paid stipend with pre-placement opportunity for college students.", fill=(70, 70, 70), font=font_body)
    draw.text((45, 380), "ID: NEW_TEST_099  |  Category: CAREER", fill=(120, 120, 120), font=font_body)

    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def run_test():
    print("==========================================================================================")
    print("TEST: DYNAMIC NEW-DOCUMENT UPLOAD & REAL-TIME EMBEDDINGS INDEXING")
    print("==========================================================================================")

    # 1. Generate new image
    img_bytes = create_dynamic_test_image()
    filename = "student_internship_opportunity.jpg"
    print(f"1. Created new test document: {filename} (in memory)")

    # 2. Upload image to /upload endpoint
    print("2. Sending POST /upload multipart request...")
    files = {"file": (filename, img_bytes, "image/jpeg")}
    upload_resp = client.post("/upload", files=files)
    
    if upload_resp.status_code != 200:
        print(f"[FAIL] Upload failed with status {upload_resp.status_code}: {upload_resp.text}")
        return False

    upload_data = upload_resp.json()
    extracted_text = upload_data.get("text", "")
    print(f"   -> Upload Status: {upload_resp.status_code} OK")
    print(f"   -> EasyOCR Extracted Text: \"{extracted_text}\"")

    # 3. Immediately search with natural-language query
    search_query = "summer work opportunity for students"
    print(f"\n3. Performing semantic search for query: \"{search_query}\"...")
    search_resp = client.post("/search", json={"query": search_query})
    search_data = search_resp.json()

    results = search_data.get("results", [])
    print(f"   -> Matches Found: {len(results)}")
    
    found = False
    base_name = Path(filename).stem
    for rank, doc in enumerate(results[:5], start=1):
        name = doc.get("image_name", "")
        score = doc.get("similarity_score", 0.0)
        is_new = base_name in name
        marker = "[NEW UPLOAD]" if is_new else ""
        print(f"      Rank #{rank}: {name:<45} | Score: {score:.4f} {marker}")
        if is_new:
            found = True

    print("\n==========================================================================================")
    if found:
        print("[SUCCESS] The newly uploaded image was automatically OCR'd, indexed into SQLite,")
        print("          embedded into the vector space, and retrieved in real-time by semantic meaning!")
    else:
        print("[FAIL] The new image was not found in top semantic results.")
    print("==========================================================================================")
    return found


if __name__ == "__main__":
    run_test()
