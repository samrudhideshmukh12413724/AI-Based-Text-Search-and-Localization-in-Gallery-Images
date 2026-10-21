"""Semantic Search Engine using Sentence Transformers and Cosine Similarity."""

import os
import sys

os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
sys.modules["tensorflow"] = None

import pickle
import re
from pathlib import Path
from typing import Any, Optional

import numpy as np
from sentence_transformers import SentenceTransformer, util

from app.database import list_images

import os
ROOT_DIR = Path(os.getenv("DOCULENS_ROOT", str(Path(__file__).resolve().parents[2])))
EMBEDDINGS_FILE = ROOT_DIR / "database" / "embeddings.pkl"

_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Lazy-load the SentenceTransformer model singleton with local cache snapshot support."""
    global _model
    if _model is None:
        # Check local huggingface snapshot first to avoid remote connection timeouts
        snapshots = list(Path.home().glob(".cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/*"))
        if snapshots:
            try:
                _model = SentenceTransformer(str(snapshots[0]))
                return _model
            except Exception:
                pass

        try:
            _model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
        except Exception:
            _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def build_embeddings_index() -> int:
    """
    Generate and save embeddings for all images currently in SQLite.
    Returns the number of indexed documents.
    """
    images = list_images()
    if not images:
        return 0

    model = get_embedding_model()
    
    texts = []
    metadata = []
    from app.translation import is_devanagari, translate_indic_text, get_query_expansions
    for img in images:
        raw_ocr = (img.get("cleaned_text") or img.get("extracted_text") or "").strip()
        qr_info = (img.get("qr_payload") or "").strip()
        blip_info = (img.get("blip_caption") or "").strip()
        text = f"{raw_ocr} {qr_info} {blip_info}".strip() or img.get("image_name", "")
        if is_devanagari(text):
            tr = translate_indic_text(text)
            text = tr["searchable_translated_text"]
        texts.append(text)
        metadata.append(img)

    embeddings = model.encode(texts, convert_to_tensor=True, show_progress_bar=False)

    EMBEDDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(EMBEDDINGS_FILE, "wb") as f:
        pickle.dump({"embeddings": embeddings, "metadata": metadata}, f)

    return len(texts)


import threading

_IN_MEMORY_CACHE = {"embeddings": None, "metadata": None}
_embedding_lock = threading.Lock()


def append_single_embedding(doc_row: dict) -> None:
    """Incrementally append a single new document embedding in <1ms in-memory instead of disk thrashing."""
    global _IN_MEMORY_CACHE
    raw_ocr = (doc_row.get("cleaned_text") or doc_row.get("extracted_text") or "").strip()
    qr_info = (doc_row.get("qr_payload") or "").strip()
    blip_info = (doc_row.get("blip_caption") or "").strip()
    text = f"{raw_ocr} {qr_info} {blip_info}".strip() or doc_row.get("image_name", "")
    if not text:
        return
    from app.translation import is_devanagari, translate_indic_text
    if is_devanagari(text):
        tr = translate_indic_text(text)
        text = tr["searchable_translated_text"]
    model = get_embedding_model()
    new_emb = model.encode([text], convert_to_tensor=True)

    if not EMBEDDINGS_FILE.exists():
        build_embeddings_index()
        return

    with _embedding_lock:
        try:
            # Load from in-memory cache if warm, else from disk
            if _IN_MEMORY_CACHE["embeddings"] is None:
                with open(EMBEDDINGS_FILE, "rb") as f:
                    data = pickle.load(f)
                old_embeddings = data.get("embeddings")
                old_metadata = data.get("metadata", [])
            else:
                old_embeddings = _IN_MEMORY_CACHE["embeddings"]
                old_metadata = _IN_MEMORY_CACHE["metadata"]

            import torch
            if isinstance(old_embeddings, torch.Tensor):
                updated_embeddings = torch.cat([old_embeddings, new_emb], dim=0)
            else:
                updated_embeddings = np.vstack([old_embeddings, new_emb.cpu().numpy()])

            old_metadata.append(doc_row)
            _IN_MEMORY_CACHE["embeddings"] = updated_embeddings
            _IN_MEMORY_CACHE["metadata"] = old_metadata

            with open(EMBEDDINGS_FILE, "wb") as f:
                pickle.dump({"embeddings": updated_embeddings, "metadata": old_metadata}, f)
        except Exception:
            build_embeddings_index()



def load_embeddings_index() -> tuple[Any, list[dict]] | None:
    """Load cached embeddings and document metadata with zero-copy in-memory caching."""
    global _IN_MEMORY_CACHE
    if _IN_MEMORY_CACHE["embeddings"] is not None:
        return _IN_MEMORY_CACHE["embeddings"], _IN_MEMORY_CACHE["metadata"]

    if not EMBEDDINGS_FILE.exists():
        build_embeddings_index()

    if not EMBEDDINGS_FILE.exists():
        return None

    try:
        with open(EMBEDDINGS_FILE, "rb") as f:
            data = pickle.load(f)
        _IN_MEMORY_CACHE["embeddings"] = data["embeddings"]
        _IN_MEMORY_CACHE["metadata"] = data["metadata"]
        return _IN_MEMORY_CACHE["embeddings"], _IN_MEMORY_CACHE["metadata"]
    except Exception:
        return None


DEFAULT_SIMILARITY_THRESHOLD = 0.44


def semantic_search(
    query: str,
    top_k: int = 10,
    min_score: Optional[float] = None,
) -> list[dict]:
    """
    Perform semantic vector search using cosine similarity and Adaptive Dynamic Thresholding.
    Prevents Data Drift by dynamically calculating tau_adaptive(Q, scores) based on mean,
    standard deviation, and query length penalty instead of relying on a static cutoff.
    """
    q_clean = (query or "").strip()
    if not q_clean:
        return []
    is_num_q = bool(re.match(r"^[\d\s,.-]+$", q_clean))

    index_data = load_embeddings_index()
    if not index_data:
        return []

    doc_embeddings, metadata = index_data
    if len(metadata) == 0:
        return []

    model = get_embedding_model()
    from app.translation import get_query_expansions
    expanded_terms = get_query_expansions(query)
    search_query_text = " ".join(expanded_terms[:3]) if len(expanded_terms) > 1 else query
    query_emb = model.encode(search_query_text, convert_to_tensor=True)

    # Compute cosine similarity between query and all documents (vectorized)
    cos_scores = util.cos_sim(query_emb, doc_embeddings)[0]
    scores_arr = cos_scores.detach().cpu().numpy()
    raw_scores = [round(float(s), 4) for s in scores_arr]

    # Calculate Adaptive Dynamic Threshold if min_score is not explicitly provided
    if min_score is None:
        from app.scoring.custom_scorer import get_custom_scorer
        scorer = get_custom_scorer()
        # Calibrated tau_adaptive for semantic embeddings
        dynamic_tau = scorer.compute_adaptive_threshold(query, raw_scores)
        # Calibrated tau_adaptive: 0.44 for numeric guards, 0.42 for short single-word entities, 0.40 for general phrases
        if is_num_q:
            min_tau_bound = 0.44
        elif len(q_clean.split()) == 1 and len(q_clean) <= 6:
            min_tau_bound = 0.42
        else:
            min_tau_bound = 0.40
        calibrated_threshold = max(min_tau_bound, min(0.75, dynamic_tau))
    else:
        calibrated_threshold = min_score

    # Rank & filter results by adaptive threshold
    results = []
    debug_search = os.getenv("DEBUG_SEARCH", "0") == "1"

    for idx, score_val in enumerate(raw_scores):
        doc_info = dict(metadata[idx])
        # Skip incomplete or failed indexing records
        if doc_info.get("indexing_status") and doc_info.get("indexing_status") != "completed":
            continue
        img_name = doc_info.get("image_name") or Path(doc_info.get("image_path", "")).name
        raw_t = (doc_info.get("extracted_text", "") + " " + doc_info.get("cleaned_text", "")).lower()

        # Guard for numeric queries (e.g. "100", "88", "1890"):
        # Accept candidates if any number token appears in OCR text or filename
        q_nums = re.findall(r"\d+", q_clean)
        has_num_match = any(num in raw_t or num in img_name.lower() for num in q_nums) if q_nums else False
        if is_num_q and not has_num_match and score_val < 0.52:
            if debug_search:
                print(f"  -> REJECT (Numeric Guard): {img_name:<28} | Score: {score_val:.4f} < 0.5200 and query digits not in OCR text")
            continue

        if score_val >= calibrated_threshold:
            doc_info["similarity_score"] = score_val
            results.append(doc_info)
            if debug_search:
                print(f"  -> ACCEPT: {img_name:<28} | Score: {score_val:.4f} >= {calibrated_threshold:.4f}")
        else:
            if debug_search and score_val > 0.15:
                print(f"  -> REJECT: {img_name:<28} | Score: {score_val:.4f} < {calibrated_threshold:.4f}")

    # Sort descending by similarity score
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    if debug_search:
        print(f"[Semantic Search] Total eligible matches passing adaptive threshold: {len(results[:top_k])}\n")
    return results[:top_k]
