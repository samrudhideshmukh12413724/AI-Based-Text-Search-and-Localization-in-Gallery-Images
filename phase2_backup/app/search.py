"""Keyword and typo-tolerant search over stored OCR text."""

import difflib
import re

from app import database


STOPWORDS = {"the", "a", "an", "and", "or", "for", "in", "on", "at", "to", "from", "of", "with", "is", "was", "are", "were", "by", "as", "about"}


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"\w+", text) if w and w.lower() not in STOPWORDS and len(w) > 2]


def _match_score(query: str, text: str, filename: str) -> float:
    q = query.lower().strip()
    full = f"{filename} {text}".lower()

    if q in full:
        return 1.0

    q_words = _tokenize(q)
    doc_words = _tokenize(full)

    if not q_words or not doc_words:
        return 0.0

    word_scores = []
    for qw in q_words:
        best = 0.0
        for dw in doc_words:
            if qw == dw:
                best = 1.0
            elif dw.startswith(qw) or qw.startswith(dw):
                best = max(best, 0.9 if len(qw) >= 4 else 0.7)
            else:
                ratio = difflib.SequenceMatcher(None, qw, dw).ratio()
                if ratio >= 0.80:
                    best = max(best, ratio)
        word_scores.append(best)

    return sum(word_scores) / len(word_scores)


def search(query: str) -> dict:
    cleaned = query.strip()
    if not cleaned:
        return {"query": query, "count": 0, "results": []}

    all_rows = database.list_images()
    scored = []

    for row in all_rows:
        score = _match_score(cleaned, row["extracted_text"], row["image_name"])
        if score >= 0.65:
            scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for _, row in scored:
        filename = row["image_name"]
        results.append(
            {
                "id": row["id"],
                "image_name": filename,
                "image_url": f"/uploads/{filename}",
                "matched_text": row["extracted_text"],
            }
        )

    return {"query": cleaned, "count": len(results), "results": results}

