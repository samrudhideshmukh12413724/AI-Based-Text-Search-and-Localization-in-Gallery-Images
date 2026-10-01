"""FastAPI backend: upload images, OCR, store in SQLite, keyword search."""

import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import database
from app.ocr import extract_text
from app.search import search as run_search
from app.semantic_search import semantic_search as run_semantic_search, build_embeddings_index

ROOT_DIR = Path(__file__).resolve().parents[2]
UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
database.init_db()
build_embeddings_index()

app = FastAPI(title="AI Image Search API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """Receive image, save it, OCR it, store text in SQLite."""
    suffix = Path(file.filename or "").suffix.lower() or ".jpg"
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Supported formats: JPG, PNG, WEBP")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file uploaded.")

    original_name = Path(file.filename or "image.jpg").name
    safe_name = f"{Path(original_name).stem}_{uuid.uuid4().hex[:8]}{suffix}"
    dest_path = UPLOADS_DIR / safe_name

    with open(dest_path, "wb") as out:
        out.write(data)

    try:
        text = extract_text(dest_path)
    except FileNotFoundError as exc:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(400, str(exc)) from exc

    if not text.strip():
        text = "(no text detected)"

    row = database.save_image(safe_name, str(dest_path), text)
    # Refresh embeddings index with new upload
    build_embeddings_index()

    return {
        "id": row["id"],
        "image_name": row["image_name"],
        "text": row["extracted_text"],
        "image_url": f"/uploads/{safe_name}",
    }


from app.highlighting import build_highlight_payload


@app.post("/search")
def search_images(body: SearchRequest):
    """
    Search over stored images.
    1. First performs Keyword Search.
    2. If keyword search yields 0 matches, seamlessly performs Phase 2 Semantic Search with thresholding.
    """
    kw_res = run_search(body.query)
    raw_results = kw_res.get("results", [])
    if len(raw_results) > 0:
        enriched = []
        for r in raw_results:
            raw_text = r.get("matched_text", "")
            h_data = build_highlight_payload(body.query, raw_text, search_type="keyword")
            item = dict(r)
            item.update(h_data)
            enriched.append(item)
        return {
            "query": body.query,
            "search_type": "keyword",
            "count": len(enriched),
            "total_matches": len(enriched),
            "message": f"Found {len(enriched)} keyword match(es).",
            "results": enriched,
            "matched_images": enriched,
        }

    # Fallback to semantic search
    return search_semantic(body)


@app.post("/search/semantic")
def search_semantic(body: SearchRequest):
    """Phase 2 Semantic Search using NLP embeddings and cosine similarity thresholding."""
    sem_matches = run_semantic_search(body.query, top_k=10)
    formatted = []
    for doc in sem_matches:
        img_name = doc.get("image_name") or Path(doc.get("image_path", "")).name
        raw_text = doc.get("cleaned_text") or doc.get("extracted_text", "")
        h_data = build_highlight_payload(body.query, raw_text, search_type="semantic")

        item = {
            "id": doc.get("id"),
            "image_name": img_name,
            "image_path": doc.get("image_path"),
            "image_url": f"/uploads/{img_name}",
            "matched_text": raw_text,
            "similarity_score": doc.get("similarity_score", 0.0),
        }
        item.update(h_data)
        formatted.append(item)

    msg = "No relevant documents found." if len(formatted) == 0 else f"Found {len(formatted)} relevant document(s)."

    return {
        "query": body.query,
        "search_type": "semantic",
        "count": len(formatted),
        "total_matches": len(formatted),
        "message": msg,
        "results": formatted,
        "matched_images": formatted,
    }


@app.post("/search/keyword")
def search_keyword_only(body: SearchRequest):
    """Phase 1 Keyword search only (for comparison)."""
    kw_res = run_search(body.query)
    raw_results = kw_res.get("results", [])
    enriched = []
    for r in raw_results:
        raw_text = r.get("matched_text", "")
        h_data = build_highlight_payload(body.query, raw_text, search_type="keyword")
        item = dict(r)
        item.update(h_data)
        enriched.append(item)
    return {
        "query": body.query,
        "search_type": "keyword",
        "count": len(enriched),
        "total_matches": len(enriched),
        "message": f"Found {len(enriched)} keyword match(es).",
        "results": enriched,
        "matched_images": enriched,
    }


@app.get("/images")
def list_images():
    rows = database.list_images()
    return [
        {
            "id": row["id"],
            "image_name": row["image_name"],
            "text": row["extracted_text"],
            "image_url": f"/uploads/{row['image_name']}",
        }
        for row in rows
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
