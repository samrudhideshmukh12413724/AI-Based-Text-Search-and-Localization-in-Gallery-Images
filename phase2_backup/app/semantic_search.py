"""Semantic Search Engine using Sentence Transformers and Cosine Similarity."""

import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import pickle
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer, util

from app.database import list_images

ROOT_DIR = Path(__file__).resolve().parents[2]
EMBEDDINGS_FILE = ROOT_DIR / "database" / "embeddings.pkl"

_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Lazy-load the SentenceTransformer model singleton."""
    global _model
    if _model is None:
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
    for img in images:
        # Use cleaned_text if present, fallback to extracted_text
        text = (img.get("cleaned_text") or img.get("extracted_text") or img.get("image_name", "")).strip()
        texts.append(text)
        metadata.append(img)

    embeddings = model.encode(texts, convert_to_tensor=True, show_progress_bar=False)

    EMBEDDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(EMBEDDINGS_FILE, "wb") as f:
        pickle.dump({"embeddings": embeddings, "metadata": metadata}, f)

    return len(texts)


def load_embeddings_index() -> tuple[Any, list[dict]] | None:
    """Load cached embeddings and document metadata from disk."""
    if not EMBEDDINGS_FILE.exists():
        build_embeddings_index()

    if not EMBEDDINGS_FILE.exists():
        return None

    with open(EMBEDDINGS_FILE, "rb") as f:
        data = pickle.load(f)
    return data["embeddings"], data["metadata"]


DEFAULT_SIMILARITY_THRESHOLD = 0.39


def semantic_search(
    query: str,
    top_k: int = 10,
    min_score: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> list[dict]:
    """
    Perform semantic vector search using cosine similarity.
    Filters out any document with similarity below min_score (calibrated to 0.39).
    Returns ranked list of matching documents with similarity scores.
    """
    index_data = load_embeddings_index()
    if not index_data:
        return []

    doc_embeddings, metadata = index_data
    if len(metadata) == 0:
        return []

    model = get_embedding_model()
    query_emb = model.encode(query, convert_to_tensor=True)

    # Compute cosine similarity between query and all documents
    cos_scores = util.cos_sim(query_emb, doc_embeddings)[0]

    # Rank & filter results by threshold
    results = []
    print(f"\n[Semantic Search] Query: \"{query}\" (Threshold: {min_score})")
    
    for idx, score in enumerate(cos_scores):
        score_val = round(score.item(), 4)
        doc_info = dict(metadata[idx])
        img_name = doc_info.get("image_name") or Path(doc_info.get("image_path", "")).name

        if score_val >= min_score:
            doc_info["similarity_score"] = score_val
            results.append(doc_info)
            print(f"  -> ACCEPT: {img_name:<28} | Score: {score_val:.4f} >= {min_score}")
        else:
            if score_val > 0.15:
                print(f"  -> REJECT: {img_name:<28} | Score: {score_val:.4f} < {min_score}")

    # Sort descending by similarity score
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    print(f"[Semantic Search] Total eligible matches passing threshold: {len(results[:top_k])}\n")
    return results[:top_k]
