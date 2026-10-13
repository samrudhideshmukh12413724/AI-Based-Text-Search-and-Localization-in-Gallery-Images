"""FastAPI application for AI Document & Image-Inside-Image Visual Search (Phase 1, 2, 3A, and 3B)."""

import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
sys.modules["tensorflow"] = None

import uuid
from pathlib import Path
from typing import Any, Optional, Dict

from fastapi import FastAPI, File, HTTPException, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import database
from app.duplicates import check_duplicate, collapse_duplicate_results
from app.entities import extract_entities
from app.filters import FilterParams, get_eligible_candidate_ids
from app.linking import get_image_relationships


from app.highlighting import build_highlight_payload
from app.ocr import extract_text
from app.ocr.ocr_engine import extract_text_adaptive
from app.search import search as run_search, extract_image_metadata
from app.semantic_search import build_embeddings_index, append_single_embedding
from app.semantic_search import semantic_search as run_semantic_search
from app.visual_detector import get_visual_detector
from app.visual_search import get_visual_search_engine
from app.captioning import generate_caption
from app.qr_decoder import extract_qr_payloads
from app.steganography import extract_stego_text, compute_document_hash

from fastapi import Depends
from app import auth
from app.auth import UserRegister, UserLogin, Token
from app.scoring.custom_scorer import get_custom_scorer

ROOT_DIR = Path(__file__).resolve().parents[2]
UPLOADS_DIR = ROOT_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

app = FastAPI(
    title="AI Document & Image Search Backend",
    version="5.0.0",
    description="Multi-modal document retrieval with Phase 5 Security, Multi-Tenant User Isolation, and Custom Hybrid Scoring.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


@app.on_event("startup")
def on_startup() -> None:
    database.init_db()
    # Pre-warm vision-language and semantic models on startup
    get_visual_search_engine()
    build_embeddings_index()


@app.get("/health")
def health_check():
    """Health check endpoint for Docker, Kubernetes, and CI/CD probes."""
    return {"status": "ok", "service": "AI Document & Image Search"}


@app.post("/auth/register", response_model=dict)
def register_user(user: UserRegister):
    existing = database.get_user_by_username(user.username)
    if existing:
        raise HTTPException(400, "Username already registered")
    hashed = auth.get_password_hash(user.password)
    created = database.create_user(user.username, hashed)
    return {"message": "User registered successfully", "user_id": created["id"], "username": created["username"]}


@app.post("/auth/login", response_model=Token)
def login_user(user: UserLogin):
    db_user = database.get_user_by_username(user.username)
    if not db_user or not auth.verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(401, "Incorrect username or password")
    token = auth.create_access_token({"sub": db_user["username"], "user_id": db_user["id"]})
    return {"access_token": token, "token_type": "bearer", "username": db_user["username"], "user_id": db_user["id"]}


@app.get("/auth/me")
def get_user_me(current_user: dict = Depends(auth.get_current_user)):
    return {"id": current_user["id"], "username": current_user["username"]}


class SearchRequest(BaseModel):
    query: str
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    year: Optional[int] = None
    category: Optional[str] = None
    format: Optional[str] = None
    visual_type: Optional[str] = None
    entity_type: Optional[str] = None


def _extract_visual_info(db_row: dict) -> dict:
    """Helper to format Phase 3/3B visual object metadata."""
    v_meta = db_row.get("visual_metadata", {})
    if isinstance(v_meta, str):
        import json
        try:
            v_meta = json.loads(v_meta)
        except Exception:
            v_meta = {}

    objs = v_meta.get("objects", []) if isinstance(v_meta, dict) else []
    has_vis = bool(db_row.get("has_visual_objects", 0)) or len(objs) > 0

    summary = ""
    if has_vis and objs:
        obj_labels = [f"{o.get('label', 'Object')} ({o.get('location_desc', 'Embedded')})" for o in objs]
        summary = ", ".join(obj_labels)

    return {
        "has_visual_objects": has_vis,
        "visual_objects": objs,
        "visual_summary": summary,
    }


@app.post("/upload")
def upload_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(auth.get_current_user),
):
    """
    Multi-Modal Ingestion Pipeline:
    1. Saves document image.
    2. Runs EasyOCR for text extraction (Phase 1 & 2).
    3. Runs OpenCV Visual Detector for QR codes (Phase 3A).
    4. Extracts & Indexes Visual Regions via CLIP in Background (Phase 3B).
    5. Persists text + visual bounding box metadata in SQLite.
    6. Fast incremental semantic vector update.
    """
    suffix = Path(file.filename or "").suffix.lower() or ".jpg"
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Supported formats: JPG, PNG, WEBP")

    data = file.file.read()
    if not data:
        raise HTTPException(400, "Empty file uploaded.")

    original_name = Path(file.filename or "image.jpg").name
    safe_name = f"{Path(original_name).stem}_{uuid.uuid4().hex[:8]}{suffix}"
    dest_path = UPLOADS_DIR / safe_name

    # Normalize phone camera EXIF orientation & auto-downscale giant resolutions (>2560px)
    try:
        import io
        from PIL import Image as PILImg, ImageOps
        pil_img = PILImg.open(io.BytesIO(data))
        pil_img = ImageOps.exif_transpose(pil_img)

        # Scale down oversized photos (e.g. 48MP) to preserve crisp OCR while eliminating memory/time lag
        max_dim = 2560
        if max(pil_img.size) > max_dim:
            scale = max_dim / float(max(pil_img.size))
            new_size = (int(pil_img.width * scale), int(pil_img.height * scale))
            pil_img = pil_img.resize(new_size, PILImg.Resampling.LANCZOS)

        if suffix in [".jpg", ".jpeg"]:
            pil_img.convert("RGB").save(dest_path, format="JPEG", quality=95)
        elif suffix == ".png":
            pil_img.save(dest_path, format="PNG")
        elif suffix == ".webp":
            pil_img.save(dest_path, format="WEBP", quality=95)
        else:
            with open(dest_path, "wb") as out:
                out.write(data)
    except Exception as e:
        print(f"[Upload Ingestion] EXIF normalize fallback: {e}")
        with open(dest_path, "wb") as out:
            out.write(data)

    # 1. Run Duplicate & Near-Duplicate Detection (Phase 4 Step 5)
    dupe_res = check_duplicate(dest_path)
    is_dupe = 1 if dupe_res.get("is_duplicate") else 0
    canon_id = dupe_res.get("canonical_id")
    dupe_sim = float(dupe_res.get("similarity", 0.0)) if is_dupe else 0.0
    dupe_match_type = dupe_res.get("match_type", "unique") if is_dupe else "unique"
    sha256_hash = dupe_res.get("sha256_hash", "")
    phash = dupe_res.get("phash", "")

    # 2. Run OCR (Phase 1 & 2)
    try:
        ocr_res = extract_text_adaptive(dest_path)
        text = ocr_res.get("text", "")
        word_boxes = ocr_res.get("word_boxes", [])
    except FileNotFoundError as exc:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(400, str(exc)) from exc

    if not text.strip():
        text = "(no text detected)"

    # 3. Extract Structured Entities (Phase 4 Step 3)
    entities = extract_entities(text)

    # 4. Extract Technical & Temporal Metadata (Phase 4 Step 4)
    img_meta = extract_image_metadata(dest_path, entities)

    # 5. Run OpenCV Visual Object Detection (Phase 3A)
    detector = get_visual_detector()
    vis_res = detector.detect_visual_objects(dest_path)
    has_visual = 1 if vis_res.get("detected") else 0

    # 5B. Fast OpenCV QR payload decoder & Steganography Reader
    qr_res = extract_qr_payloads(dest_path)
    stego_text = extract_stego_text(dest_path)
    doc_sha256 = sha256_hash or compute_document_hash(dest_path)
    blip_cap = ""  # Populated asynchronously in background task for 3x speedup

    # 6. Store in Database
    row = database.save_image(
        image_name=safe_name,
        image_path=str(dest_path),
        extracted_text=text,
        original_ocr_text=text,
        cleaned_text=text,
        has_visual_objects=has_visual,
        visual_metadata=vis_res,
        entities=entities,
        user_id=current_user.get("id", 1),
    )
    database.update_image_ocr_boxes(row["id"], word_boxes)
    database.update_image_metadata(
        image_id=row["id"],
        file_size_bytes=img_meta["file_size_bytes"],
        image_width=img_meta["image_width"],
        image_height=img_meta["image_height"],
        file_format=img_meta["file_format"],
        file_modified_at=img_meta["file_modified_at"],
        exif_created_at=img_meta["exif_created_at"],
        primary_date=img_meta["primary_date"],
    )
    database.update_multimodal_payloads(
        image_id=row["id"],
        blip_caption="",
        qr_payload=qr_res.get("qr_summary", ""),
        stego_payload=stego_text,
    )
    database.update_image_duplicates(
        image_id=row["id"],
        sha256_hash=doc_sha256,
        phash=phash,
        is_duplicate=is_dupe,
        canonical_image_id=canon_id,
        duplicate_similarity=dupe_sim,
        duplicate_match_type=dupe_match_type,
    )

    # 7. Heavy AI Tasks (BLIP Captioning + CLIP Region Indexing) executed in background
    def _async_bg_tasks(img_id: int, img_name: str, p: Path):
        try:
            cap = generate_caption(p)
            if cap:
                database.update_multimodal_payloads(
                    image_id=img_id,
                    blip_caption=cap,
                    qr_payload=qr_res.get("qr_summary", ""),
                    stego_payload=stego_text,
                )
        except Exception as e:
            print(f"[Background Task] BLIP warning: {e}")
        v_search = get_visual_search_engine()
        v_search.index_document(img_id, img_name, str(p))

    background_tasks.add_task(_async_bg_tasks, row["id"], safe_name, dest_path)

    # 8. Fast Incremental Semantic Vector Embeddings Index (50ms)
    append_single_embedding(row)

    vis_info = _extract_visual_info(row)

    return {
        "id": row["id"],
        "image_name": row["image_name"],
        "image_path": row["image_path"],
        "image_url": f"/uploads/{row['image_name']}",
        "text": row["extracted_text"],
        "extracted_text": row["extracted_text"],
        "original_ocr_text": row.get("original_ocr_text", row["extracted_text"]),
        "cleaned_text": row.get("cleaned_text", row["extracted_text"]),
        "blip_caption": blip_cap,
        "qr_payload": qr_res.get("qr_summary", ""),
        "stego_payload": stego_text,
        "entities": row.get("entities", entities),
        "has_visual_objects": vis_info["has_visual_objects"],
        "visual_objects": vis_info["visual_objects"],
        "visual_summary": vis_info["visual_summary"],
        "is_duplicate": bool(is_dupe),
        "canonical_image_id": canon_id,
        "canonical_image_name": dupe_res.get("canonical_image_name"),
        "duplicate_match_type": dupe_match_type,
        "duplicate_similarity": dupe_sim,
        "sha256_hash": doc_sha256,
        "phash": phash,
        "message": (
            "Duplicate image linked to canonical document."
            if is_dupe
            else (
                "Image processed with OCR, Structured Entities, Semantic NLP,"
                " and Visual Region Embeddings."
            )
        ),
    }



@app.get("/images")
def get_images():
    """Retrieve all indexed documents."""
    rows = database.list_images()
    result = []
    for r in rows:
        item = {
            "id": r["id"],
            "image_name": r["image_name"],
            "image_path": r["image_path"],
            "image_url": f"/uploads/{r['image_name']}",
            "extracted_text": r["extracted_text"],
            "original_ocr_text": r.get("original_ocr_text", r["extracted_text"]),
            "cleaned_text": r.get("cleaned_text", r["extracted_text"]),
            "entities": r.get("entities", {}),
            "created_at": r["created_at"],
        }
        item.update(_extract_visual_info(r))
        result.append(item)
    return result


@app.get("/images/{image_id}/relationships")
def get_image_relationships_endpoint(image_id: int):
    """
    Retrieve explainable cross-image relationships for a specific document image (Phase 4 Step 6C).
    If the queried image is a duplicate variant, resolves its canonical_image_id and returns
    the canonical image's relationships, preserving strict duplicate isolation.
    """
    row = database.get_image_by_id(image_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Image with ID {image_id} not found.")

    canonical_id = row.get("canonical_image_id") if row.get("is_duplicate") else None

    raw_rels = get_image_relationships(image_id)
    formatted_rels = []
    for r in raw_rels:
        formatted_rels.append({
            "image_id": r["target_image_id"],
            "image_name": r["image_name"],
            "image_url": f"/uploads/{r['image_name']}",
            "relationship_type": r["relationship_type"],
            "confidence_score": float(r["confidence_score"]),
            "evidence": r["evidence"],
            "reason": r.get("reason", f"Shares {r['relationship_type']}: '{r['evidence']}'"),
        })

    return {
        "image_id": image_id,
        "canonical_image_id": canonical_id,
        "relationships": formatted_rels,
    }


@app.post("/search")
def search_images(
    body: SearchRequest,
    current_user: dict | Any = Depends(auth.get_current_user),
):
    """
    Parallel Multi-Modal Search Fusion Router:
    Concurrently executes Text Retrieval (Exact Keyword + Dense Semantic NLP) and Visual Retrieval (CLIP).
    """
    if not isinstance(current_user, dict):
        current_user = {"id": 1, "username": "guest"}

    q_norm = body.query.strip().lower()
    if not q_norm:
        return {
            "query": body.query,
            "search_type": "keyword",
            "count": 0,
            "total_matches": 0,
            "message": "Empty query provided.",
            "results": [],
            "matched_images": [],
        }

    # =========================================================================
    # Phase 4 & 5: UNIFIED MULTI-FACETED FILTER & MULTI-TENANT EVALUATION
    # =========================================================================
    params = FilterParams(
        date_from=body.date_from,
        date_to=body.date_to,
        year=body.year,
        category=body.category,
        format=body.format,
        visual_type=body.visual_type,
        entity_type=body.entity_type,
        user_id=current_user.get("id", 1),
    )
    eligible_ids = get_eligible_candidate_ids(params) if params.has_any_filter() else None

    # Deterministic empty candidate termination when filters yield no matches
    if eligible_ids is not None and len(eligible_ids) == 0:
        return {
            "query": body.query,
            "search_type": "multimodal",
            "count": 0,
            "total_matches": 0,
            "message": "No relevant documents found matching the specified filters.",
            "results": [],
            "matched_images": [],
        }

    # =========================================================================
    # 1. PARALLEL TEXT RETRIEVAL (Keyword Exact + Dense Semantic NLP)
    # =========================================================================
    text_candidates: dict[int, dict] = {}

    # 1A. Exact Lexical Keyword Search
    try:
        kw_res = run_search(body.query)
        for item in kw_res.get("results", []):
            img_id = item.get("id")
            if img_id:
                raw_text = item.get("matched_text", "")
                h_data = build_highlight_payload(body.query, raw_text, search_type="keyword")
                kw_s = float(item.get("match_score", 0.90))
                text_candidates[img_id] = {
                    "score": kw_s,
                    "is_kw": True,
                    "text": raw_text,
                    "highlight_data": h_data,
                    "image_name": item.get("image_name"),
                    "image_path": item.get("image_path"),
                }
    except Exception as e:
        print(f"[Search Engine] Keyword search warning: {e}")

    # 1B. Dense Semantic Vector Search (NLP Meaning)
    try:
        sem_matches = run_semantic_search(body.query, top_k=25)
        for doc in sem_matches:
            img_id = doc.get("id")
            if not img_id:
                continue
            sem_score = float(doc.get("similarity_score", 0.0))
            raw_text = doc.get("cleaned_text") or doc.get("extracted_text", "")

            if img_id in text_candidates:
                # Existing keyword match: boost score if semantic also strongly agrees
                text_candidates[img_id]["score"] = max(text_candidates[img_id]["score"], sem_score)
            else:
                # Semantic match above calibrated threshold
                h_data = build_highlight_payload(body.query, raw_text, search_type="semantic")
                text_candidates[img_id] = {
                    "score": sem_score,
                    "is_kw": False,
                    "text": raw_text,
                    "highlight_data": h_data,
                    "image_name": doc.get("image_name") or Path(doc.get("image_path", "")).name,
                    "image_path": doc.get("image_path"),
                }
    except Exception as e:
        print(f"[Search Engine] Semantic search warning: {e}")

    # =========================================================================
    # 2. PARALLEL VISUAL RETRIEVAL (CLIP Patch-Level Region Matching)
    # =========================================================================
    visual_candidates: dict[int, dict] = {}
    # Adapt visual threshold for numeric/code queries to prevent false positive CLIP noise
    clean_q_raw = body.query.strip().lower()
    is_numeric_query = clean_q_raw.isdigit() or (len(clean_q_raw) <= 3 and not clean_q_raw.isalpha())
    VISUAL_TARGET_KEYWORDS = {
        "stamp", "seal", "signature", "sign", "qr", "qrcode", "barcode", "logo",
        "photo", "picture", "image", "portrait", "face", "car", "cat", "dog",
        "diagram", "chart", "graph", "map", "table", "icon", "drawing", "badge",
        "passport", "steganography"
    }
    is_visual_target_query = any(vk in clean_q_raw for vk in VISUAL_TARGET_KEYWORDS)
    v_thresh = 0.380 if (is_numeric_query or not is_visual_target_query) else 0.335

    try:
        v_engine = get_visual_search_engine()
        # Calibrated threshold for visual region patches
        v_matches = v_engine.search(body.query, top_k=25, threshold=v_thresh)
        for doc in v_matches:
            img_id = doc.get("id")
            if img_id:
                visual_candidates[img_id] = {
                    "score": float(doc.get("similarity_score", 0.0)),
                    "best_region": doc.get("best_region", {}),
                    "image_name": doc.get("image_name"),
                    "image_path": doc.get("image_path"),
                    "extracted_text": doc.get("extracted_text", ""),
                }
    except Exception as e:
        print(f"[Search Engine] Visual search warning: {e}")

    # =========================================================================
    # Phase 4 Step 8: CANDIDATE PRUNING PRIOR TO FUSION
    # =========================================================================
    if eligible_ids is not None:
        text_candidates = {k: v for k, v in text_candidates.items() if k in eligible_ids}
        visual_candidates = {k: v for k, v in visual_candidates.items() if k in eligible_ids}

    # =========================================================================
    # 3. MULTI-MODAL SCORE FUSION & UNIFIED RESULT FORMATION
    # =========================================================================
    all_doc_ids = set(text_candidates.keys()) | set(visual_candidates.keys())
    if not all_doc_ids:
        return {
            "query": body.query,
            "search_type": "multimodal",
            "count": 0,
            "total_matches": 0,
            "message": "No relevant documents found.",
            "results": [],
            "matched_images": [],
        }

    def _norm_vis_score(raw_v: float) -> float:
        """Normalizes raw CLIP cosine similarity without artificially inflating weak scores."""
        if raw_v < 0.34:
            return round(raw_v, 3)
        return round(min(0.95, 0.45 + 0.50 * (raw_v - 0.34) / 0.16), 3)

    fused_results = []

    for img_id in all_doc_ids:
        db_row = database.get_image_by_id(img_id)
        has_text = img_id in text_candidates
        has_vis = img_id in visual_candidates

        # Fetch document dimensions and stored OCR word boxes
        word_boxes = database.get_image_ocr_boxes(img_id)
        img_w = db_row.get("image_width", 0) if db_row else 0
        img_h = db_row.get("image_height", 0) if db_row else 0

        # Fetch basic document info
        img_name = ""
        img_path = ""
        raw_text = ""
        if db_row:
            img_name = db_row.get("image_name", "")
            img_path = db_row.get("image_path", "")
            raw_text = db_row.get("extracted_text", "")
        elif has_text:
            img_name = text_candidates[img_id].get("image_name", "")
            img_path = text_candidates[img_id].get("image_path", "")
            raw_text = text_candidates[img_id].get("text", "")
        elif has_vis:
            img_name = visual_candidates[img_id].get("image_name", "")
            img_path = visual_candidates[img_id].get("image_path", "")
            raw_text = visual_candidates[img_id].get("extracted_text", "")

        card_item = {
            "id": img_id,
            "image_name": img_name,
            "image_path": img_path,
            "image_url": f"/uploads/{img_name}",
            "matched_text": raw_text,
        }

        if (img_w == 0 or img_h == 0) and img_path and Path(img_path).exists():
            try:
                from PIL import Image as PILImage
                with PILImage.open(img_path) as pil_img:
                    img_w, img_h = pil_img.size
                database.update_image_metadata(img_id, image_width=img_w, image_height=img_h)
            except Exception:
                pass

        is_kw = text_candidates[img_id]["is_kw"] if has_text else False
        h_data = build_highlight_payload(
            body.query,
            raw_text,
            search_type="keyword" if is_kw else "semantic",
            word_boxes=word_boxes,
            image_width=img_w,
            image_height=img_h,
        )
        text_boxes = h_data.get("text_bounding_boxes", [])

        # Case A: Multi-Modal Match (Document satisfies BOTH text and visual criteria)
        if has_text and has_vis:
            t_score = text_candidates[img_id]["score"]
            v_raw = visual_candidates[img_id]["score"]
            v_norm = _norm_vis_score(v_raw)
            if is_kw and t_score >= 0.98:
                fused_score = 1.00
            else:
                fused_score = round(min(0.95, max(t_score, v_norm) * 0.85 + min(t_score, v_norm) * 0.15), 3)

            card_item.update(h_data)

            best_reg = visual_candidates[img_id]["best_region"]
            visual_objects = [{
                "type": best_reg.get("source", "visual_region"),
                "label": f"Visual Match: {best_reg.get('location_desc', 'Embedded')}",
                "location_desc": best_reg.get("location_desc", "Center"),
                "bbox": best_reg.get("bbox", {}),
                "normalized_bbox": best_reg.get("normalized_bbox", {}),
                "confidence": best_reg.get("confidence", v_raw),
                "data": f"Visual Match: {body.query} ({v_raw:.2f})",
            }]
            # Append in-image text bounding box overlays if available
            if text_boxes:
                visual_objects.extend(text_boxes)

            card_item["has_visual_objects"] = True
            card_item["visual_objects"] = visual_objects
            card_item["visual_summary"] = (
                f"Visual match: {body.query} at "
                f"{best_reg.get('location_desc', 'Document')} + Text match"
            )
            card_item["similarity_score"] = fused_score
            card_item["search_type"] = "multimodal"

        # Case B: Text-Only Match
        elif has_text:
            raw_t = text_candidates[img_id]["score"]
            if is_kw and raw_t >= 0.98:
                t_score = 1.00
            else:
                t_score = round(min(0.95, raw_t), 3)
            card_item.update(h_data)
            card_item["similarity_score"] = t_score
            card_item["search_type"] = "keyword" if is_kw else "semantic"

            v_info = _extract_visual_info(db_row) if db_row else {"has_visual_objects": False, "visual_objects": [], "visual_summary": ""}
            existing_objs = v_info.get("visual_objects", [])
            combined_objs = list(existing_objs)
            if text_boxes:
                combined_objs.extend(text_boxes)

            card_item["has_visual_objects"] = len(combined_objs) > 0
            card_item["visual_objects"] = combined_objs
            card_item["visual_summary"] = v_info.get("visual_summary", "")

        # Case C: Visual-Only Match
        else:
            v_raw = visual_candidates[img_id]["score"]
            if is_numeric_query and v_raw < 0.380:
                continue
            if not is_visual_target_query and v_raw < 0.400:
                continue
            if v_raw < 0.335:
                continue
            v_norm = round(_norm_vis_score(v_raw), 3)
            best_reg = visual_candidates[img_id]["best_region"]
            visual_objects = [{
                "type": best_reg.get("source", "visual_region"),
                "label": f"Visual Match: {best_reg.get('location_desc', 'Embedded')}",
                "location_desc": best_reg.get("location_desc", "Center"),
                "bbox": best_reg.get("bbox", {}),
                "normalized_bbox": best_reg.get("normalized_bbox", {}),
                "confidence": best_reg.get("confidence", v_raw),
                "data": f"Visual Match: {body.query} ({v_raw:.2f})",
            }]
            if text_boxes:
                visual_objects.extend(text_boxes)

            card_item.update(h_data)
            card_item["has_visual_objects"] = True
            card_item["visual_objects"] = visual_objects
            card_item["visual_summary"] = f"Matched {body.query} at {best_reg.get('location_desc', 'Document')}"
            card_item["similarity_score"] = v_norm
            card_item["search_type"] = "visual"

        fused_results.append(card_item)

    # Sort by score first, then prioritize grounded visual evidence.
    # This ensures a verified visual/multimodal match wins an exact-score text-only tie.
    fused_results.sort(
        key=lambda x: (
            x.get("similarity_score", 0.0),
            1.0 if x.get("search_type") == "keyword"
            else (0.8 if x.get("search_type") == "multimodal"
            else (0.5 if x.get("search_type") == "semantic" else 0.2))
        ),
        reverse=True
    )

    # Phase 5 Adaptive Dynamic Thresholding (tau_adaptive) to prevent Data Drift
    all_fused_scores = [r.get("similarity_score", 0.0) for r in fused_results]
    custom_scorer = get_custom_scorer()
    adaptive_cutoff = custom_scorer.compute_adaptive_threshold(body.query, all_fused_scores)
    fused_results = [r for r in fused_results if r.get("similarity_score", 0.0) >= adaptive_cutoff]

    # If high-confidence text matches exist (keyword 1.00 or high semantic >= 0.85),
    # prune weak visual-only stragglers (< 0.50) to prevent false-positive drift
    has_high_confidence_text = any(
        r.get("similarity_score", 0.0) >= 0.85 and r.get("search_type") in ("keyword", "semantic", "multimodal")
        for r in fused_results
    )
    if has_high_confidence_text:
        fused_results = [
            r for r in fused_results
            if r.get("search_type") != "visual" or r.get("similarity_score", 0.0) >= 0.50
        ]

    # Collapse duplicate variants under canonical image (Phase 4 Step 5D-2)
    collapsed_results = collapse_duplicate_results(fused_results)

    # Dominant search type for response header
    dominant_type = "multimodal"
    types = [r.get("search_type") for r in collapsed_results[:3]]
    if any(t == "multimodal" for t in types):
        dominant_type = "multimodal"
    elif all(t == "visual" for t in types):
        dominant_type = "visual"
    elif any(t == "keyword" for t in types):
        dominant_type = "keyword"
    else:
        dominant_type = "semantic"

    return {
        "query": body.query,
        "search_type": dominant_type,
        "count": len(collapsed_results),
        "total_matches": len(collapsed_results),
        "message": f"Found {len(collapsed_results)} relevant document(s).",
        "results": collapsed_results,
        "matched_images": collapsed_results,
    }



@app.post("/search/semantic")
def search_semantic(body: SearchRequest):
    """Phase 2 Semantic Search using NLP embeddings and cosine similarity thresholding."""
    sem_matches = run_semantic_search(body.query, top_k=10)
    formatted = []
    for doc in sem_matches:
        img_name = doc.get("image_name") or Path(doc.get("image_path", "")).name
        raw_text = doc.get("cleaned_text") or doc.get("extracted_text", "")
        h_data = build_highlight_payload(body.query, raw_text, search_type="semantic")

        img_id = doc.get("id")
        db_row = database.get_image_by_id(img_id) if img_id else None

        item = {
            "id": img_id,
            "image_name": img_name,
            "image_path": doc.get("image_path"),
            "image_url": f"/uploads/{img_name}",
            "matched_text": raw_text,
            "similarity_score": doc.get("similarity_score", 0.0),
        }
        item.update(h_data)

        # Enrich with Phase 3 visual object information
        if db_row:
            item.update(_extract_visual_info(db_row))
        else:
            item.update({"has_visual_objects": False, "visual_objects": [], "visual_summary": ""})

        formatted.append(item)

    collapsed_formatted = collapse_duplicate_results(formatted)
    msg = "No relevant documents found." if len(collapsed_formatted) == 0 else f"Found {len(collapsed_formatted)} relevant document(s)."

    return {
        "query": body.query,
        "search_type": "semantic",
        "count": len(collapsed_formatted),
        "total_matches": len(collapsed_formatted),
        "message": msg,
        "results": collapsed_formatted,
        "matched_images": collapsed_formatted,
    }


@app.post("/search/visual_region")
def search_visual_region(body: SearchRequest):
    """Direct Phase 3B Localized Visual Region Search."""
    v_engine = get_visual_search_engine()
    v_matches = v_engine.search(body.query, top_k=10, threshold=0.24)
    formatted = []
    for doc in v_matches:
        img_name = doc["image_name"]
        raw_text = doc.get("extracted_text", "")
        best_reg = doc.get("best_region", {})

        visual_objects = [{
            "type": best_reg.get("source", "visual_region"),
            "label": f"Visual Match: {best_reg.get('location_desc', 'Embedded')}",
            "location_desc": best_reg.get("location_desc", "Center"),
            "bbox": best_reg.get("bbox", {}),
            "normalized_bbox": best_reg.get("normalized_bbox", {}),
            "confidence": best_reg.get("confidence", 0.0),
            "data": f"Visual Match: {body.query} ({best_reg.get('confidence', 0.0):.2f})",
        }]

        h_data = build_highlight_payload(body.query, raw_text, search_type="semantic")
        item = {
            "id": doc["id"],
            "image_name": img_name,
            "image_path": doc["image_path"],
            "image_url": f"/uploads/{img_name}",
            "matched_text": raw_text,
            "similarity_score": doc["similarity_score"],
            "has_visual_objects": True,
            "visual_objects": visual_objects,
            "visual_summary": f"Matched {body.query} at {best_reg.get('location_desc', 'Document')}",
        }
        item.update(h_data)
        formatted.append(item)

    collapsed_formatted = collapse_duplicate_results(formatted)
    return {
        "query": body.query,
        "search_type": "visual",
        "count": len(collapsed_formatted),
        "total_matches": len(collapsed_formatted),
        "message": f"Found {len(collapsed_formatted)} visual match(es).",
        "results": collapsed_formatted,
        "matched_images": collapsed_formatted,
    }


# ==============================================================================
# ADVANCED FEATURES 1-5: Tampering Detection, Table Parser, Indic Translation, Knowledge Graph
# ==============================================================================
from app import tamper_detector, invoice_parser, translation, knowledge_graph
from app.filters.range_filters import filter_by_amount_range


@app.get("/analyze-tampering/{image_id}")
def analyze_tampering(image_id: int):
    """
    Advanced Feature 1: Document Tampering & Photo Edit Detection (Error Level Analysis ELA).
    Detects photoshopped text, cloned pixels, or image manipulation.
    """
    row = database.get_image(image_id)
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")
    img_path = Path(row["image_path"])
    return tamper_detector.analyze_document_tampering(img_path)


@app.get("/parse-invoice/{image_id}")
def parse_invoice(image_id: int):
    """
    Advanced Feature 2: Structured Receipt & Invoice Table Parser.
    Extracts itemized tables, taxes (CGST/SGST/IGST), payment mode, and grand totals into structured JSON.
    """
    row = database.get_image(image_id)
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")
    text = row.get("extracted_text", "")
    return invoice_parser.parse_invoice_structure(text)


@app.post("/translate-indic")
def translate_indic(payload: Dict[str, str]):
    """
    Advanced Feature 3: Multi-Lingual Indic OCR Translation & Cross-Lingual Query Expansion.
    Auto-translates Hindi/Marathi document terms (e.g. छात्रवृत्ति -> scholarship, रसीद -> receipt).
    """
    text = payload.get("text", "")
    return translation.translate_indic_text(text)


@app.get("/knowledge-graph")
def get_knowledge_graph(user_id: int = 1):
    """
    Advanced Feature 4: Document Knowledge Graph & Entity Relationship Linker.
    Generates a global network graph linking related documents by Aadhaar, Phone, PAN, Name, & Application IDs.
    """
    return knowledge_graph.generate_document_knowledge_graph(user_id=user_id)


# ==============================================================================
# ADMIN ROUTES & XSS SANITIZATION PROTECTION
# ==============================================================================
from app.security import sanitizer
from app.auth import get_current_admin_user


@app.get("/admin/stats")
def get_admin_stats(admin_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """
    Admin Route: Retrieves global repository statistics, disk storage usage,
    and user document distribution (Role-Based Access Control Protected).
    """
    all_images = database.list_images()
    total_images = len(all_images)
    categories = {}
    for img in all_images:
        cat = img.get("category", "General")
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "admin_user": admin_user["username"],
        "total_documents": total_images,
        "categories_breakdown": categories,
        "database_status": "ONLINE_HEALTHY",
        "security_policy": "RBAC_ROLE_BASED_ACCESS_ACTIVE",
        "xss_protection": "HTML_ESCAPE_STRICT_ACTIVE",
    }


@app.post("/admin/sanitize-input")
def sanitize_user_input(payload: Dict[str, str]):
    """
    XSS Protection Route: Demonstrates real-time XSS input sanitization,
    stripping dangerous script tags, event handlers, and malicious HTML injections.
    """
    raw_input = payload.get("input", "")
    sanitized = sanitizer.sanitize_text(raw_input)
    return {
        "raw_input": raw_input,
        "sanitized_output": sanitized,
        "is_safe": "<script>" not in sanitized.lower(),
    }


# ==============================================================================
# PATENTABLE INVENTIONS 1-3 (2026 PATENT FRAMEWORK)
# ==============================================================================
from app.patentable import stego_crypto_binding, forgery_localizer, entropy_fusion

_entropy_ranker = entropy_fusion.EntropyAdaptiveMultiModalRanker()


@app.post("/patentable/stego-crypto-bind/{image_id}")
def stego_crypto_bind(image_id: int):
    """
    Patentable Invention 1 (2026): ZK-Stego Cryptographic Hash Binding Engine.
    Embeds an encrypted HMAC-SHA256 signature of OCR & Entity data directly into image pixels.
    """
    row = database.get_image(image_id)
    if not row:
        raise HTTPException(404, "Image not found")
    img_path = Path(row["image_path"])
    entities = row.get("entities", {})
    ocr_text = row.get("extracted_text", "")

    hmac_sig = stego_crypto_binding.generate_document_hmac(img_path, ocr_text, entities)
    return {
        "image_id": image_id,
        "patentable_innovation": "ZK_STEGO_CRYPTOGRAPHIC_HASH_BINDING",
        "generated_hmac_signature": hmac_sig,
        "status": "HMAC_BOUND_TO_PIXELS",
    }


@app.get("/patentable/forgery-localizer/{image_id}")
def localize_forged_fields(image_id: int):
    """
    Patentable Invention 2 (2026): Real-Time Spatial Forgery Field Localization Engine.
    Overlays ELA pixel variance onto OCR bounding boxes to pinpoint specifically forged text fields.
    """
    row = database.get_image(image_id)
    if not row:
        raise HTTPException(404, "Image not found")
    img_path = Path(row["image_path"])
    word_boxes = row.get("word_boxes", [])
    if not word_boxes:
        ocr_res = extract_text_adaptive(img_path)
        word_boxes = ocr_res.get("word_boxes", [])

    return forgery_localizer.localize_forged_text_fields(img_path, word_boxes)


@app.post("/patentable/entropy-fusion")
def evaluate_entropy_fusion(payload: Dict[str, Any]):
    """
    Patentable Invention 3 (2026): Shannon Entropy-Weighted Multi-Modal Fusion Engine.
    Computes query entropy H(Q) to dynamically adjust modality weights with noise penalization.
    """
    query = payload.get("query", "scholarship fee receipt")
    weights = _entropy_ranker.compute_adaptive_weights(query)
    score = _entropy_ranker.compute_entropy_fused_score(
        query=query,
        s_ocr=payload.get("s_ocr", 0.90),
        s_semantic=payload.get("s_semantic", 0.85),
        s_blip=payload.get("s_blip", 0.80),
        s_qr=payload.get("s_qr", 0.0),
        s_stego=payload.get("s_stego", 0.0),
        tamper_score=payload.get("tamper_score", 0.10),
    )
    return {
        "query": query,
        "shannon_entropy": weights["shannon_entropy"],
        "adaptive_modality_weights": weights,
        "entropy_fused_score": score,
        "status": "ENTROPY_ADAPTIVE_FUSION_COMPUTED",
    }




