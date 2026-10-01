"""Unified Text Retrieval & Ranking Router.

Combines Exact Lexical Search with Typo-Tolerant Fuzzy Search and
OCR Confidence Weighting, providing a single consolidated text search API.
"""

from typing import Dict, Any, List
from app.search.exact_search import exact_search
from app.search.fuzzy_search import fuzzy_search


def unified_text_search(query: str, min_score: float = 0.65) -> Dict[str, Any]:
    """
    Consolidated text search orchestrator.
    1. Runs exact lexical search.
    2. Runs typo-tolerant fuzzy search.
    3. Merges results, prioritizing exact matches and weighting by OCR confidence.
    """
    cleaned = query.strip()
    if not cleaned:
        return {"query": query, "count": 0, "results": []}

    exact_results = exact_search(cleaned, min_score=min_score)
    fuzzy_results = fuzzy_search(cleaned, min_score=min_score)

    merged: Dict[int, Dict[str, Any]] = {}

    # Exact matches first
    for item in exact_results:
        img_id = item["id"]
        merged[img_id] = item

    # Fuzzy matches merged or updated
    for item in fuzzy_results:
        img_id = item["id"]
        if img_id not in merged:
            merged[img_id] = item
        else:
            # If fuzzy score exceeds exact score, update
            if item["match_score"] > merged[img_id]["match_score"]:
                merged[img_id]["match_score"] = item["match_score"]
                merged[img_id]["is_exact"] = False

    sorted_results = list(merged.values())
    # Sort descending by match_score, then exact match priority
    sorted_results.sort(
        key=lambda x: (x.get("match_score", 0.0), 1.0 if x.get("is_exact") else 0.5),
        reverse=True
    )

    formatted = []
    for r in sorted_results:
        filename = r["image_name"]
        formatted.append({
            "id": r["id"],
            "image_name": filename,
            "image_path": r.get("image_path", ""),
            "image_url": f"/uploads/{filename}",
            "matched_text": r["matched_text"],
            "match_score": round(r["match_score"], 3),
            "is_exact": r.get("is_exact", True),
            "ocr_confidence": r.get("ocr_confidence", 0.85),
        })

    return {
        "query": cleaned,
        "count": len(formatted),
        "results": formatted
    }
