"""Exact & Token Lexical Search Engine.

Implements whole-word boundary matching, tokenization, and length-guarded
prefix matching to eliminate false substring hits (e.g. 'cat' in 'category').
"""

import re
from typing import List, Dict, Any, Optional

from app import database

STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "in", "on", "at", "to",
    "from", "of", "with", "is", "was", "are", "were", "by", "as", "about"
}


def tokenize(text: str) -> List[str]:
    """Tokenizes text into lowercase alphanumeric words, filtering stopwords."""
    return [
        w.lower()
        for w in re.findall(r"[a-zA-Z0-9]+", text)
        if w and w.lower() not in STOPWORDS and len(w) > 2
    ]


def compute_exact_score(query: str, text: str, filename: str) -> float:
    """
    Computes exact lexical match score.
    Returns 1.0 for whole-word boundary matches in filename/title, 0.98 for body text.
    """
    q = query.lower().strip()
    clean_fn = filename.replace("_", " ").replace("-", " ")
    clean_text = text.replace("_", " ").replace("-", " ")
    full = f"{clean_fn} {clean_text}".lower()

    # Exact word-boundary match: prevents false hits on substrings
    if re.search(rf"\b{re.escape(q)}\b", full):
        # Boost if match is in filename/title
        if re.search(rf"\b{re.escape(q)}\b", clean_fn.lower()):
            return 1.0
        return 0.98

    q_words = tokenize(q)
    doc_words = tokenize(full)
    fn_words = set(tokenize(clean_fn))

    if not q_words or not doc_words:
        return 0.0

    word_scores = []
    for qw in q_words:
        best = 0.0
        for dw in doc_words:
            if qw == dw:
                best = 1.0 if qw in fn_words else 0.98
            elif (dw.startswith(qw) or qw.startswith(dw)) and min(len(qw), len(dw)) >= 4 and abs(len(qw) - len(dw)) <= 2:
                best = max(best, 0.85)
        word_scores.append(best)

    return sum(word_scores) / len(word_scores)


def exact_search(query: str, min_score: float = 0.70) -> List[Dict[str, Any]]:
    """Executes exact lexical search across all stored images."""
    cleaned = query.strip()
    if not cleaned:
        return []

    all_rows = database.list_images()
    results = []

    for row in all_rows:
        score = compute_exact_score(cleaned, row["extracted_text"], row["image_name"])
        if score >= min_score:
            results.append({
                "id": row["id"],
                "image_name": row["image_name"],
                "image_path": row["image_path"],
                "matched_text": row["extracted_text"],
                "match_score": round(score, 3),
                "ocr_confidence": float(row.get("ocr_confidence", 0.85) or 0.85),
                "is_exact": True,
            })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results
