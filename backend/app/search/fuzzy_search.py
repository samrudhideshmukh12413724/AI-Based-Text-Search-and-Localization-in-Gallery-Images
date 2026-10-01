"""Typo-Tolerant Fuzzy Search Engine.

Implements Damerau-Levenshtein edit distance, transposition detection,
and SequenceMatcher ratio to recover OCR misspellings (e.g. 'SCHOLARSHP',
'Aadhar', 'certifcate') with strict length-based typo guards.
"""

import difflib
from typing import List, Dict, Any, Tuple
from app import database
from app.search.exact_search import tokenize, STOPWORDS


def damerau_levenshtein_distance(s1: str, s2: str) -> int:
    """
    Computes Damerau-Levenshtein edit distance between two strings,
    supporting insertion, deletion, substitution, and adjacent transposition.
    """
    len1, len2 = len(s1), len(s2)
    d = {}

    for i in range(-1, len1 + 1):
        d[(i, -1)] = i + 1
    for j in range(-1, len2 + 1):
        d[(-1, j)] = j + 1

    for i in range(len1):
        for j in range(len2):
            cost = 0 if s1[i] == s2[j] else 1
            d[(i, j)] = min(
                d[(i - 1, j)] + 1,       # deletion
                d[(i, j - 1)] + 1,       # insertion
                d[(i - 1, j - 1)] + cost # substitution
            )
            # Adjacent transposition
            if i > 0 and j > 0 and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                d[(i, j)] = min(d[(i, j)], d[(i - 2, j - 2)] + 1)

    return d[(len1 - 1, len2 - 1)]


def fuzzy_word_similarity(w1: str, w2: str) -> float:
    """
    Computes normalized typo similarity with strict length guards.
    - Words <= 3 chars: Exact only (no typos allowed to prevent cat/car collisions)
    - Words 4-6 chars: Max 1 edit distance allowed
    - Words >= 7 chars: Max 2 edit distances allowed
    """
    if w1 == w2:
        return 1.0

    len1, len2 = len(w1), len(w2)
    min_len = min(len1, len2)
    max_len = max(len1, len2)

    # Strict guard: do not fuzzy match short tokens
    if min_len < 4 or abs(len1 - len2) > 2:
        return 0.0

    dist = damerau_levenshtein_distance(w1, w2)
    max_allowed_dist = 1 if max_len <= 6 else 2

    if dist <= max_allowed_dist:
        return 1.0 - (dist / max_len)

    # Fallback ratio for longer compounds
    if max_len >= 8:
        ratio = difflib.SequenceMatcher(None, w1, w2).ratio()
        if ratio >= 0.82:
            return ratio

    return 0.0


def compute_fuzzy_score(query: str, text: str, filename: str) -> float:
    """
    Calculates the best fuzzy similarity score for a multi-word query against document text.
    Incorporates filename relevance boost and term frequency.
    """
    clean_fn = filename.replace("_", " ").replace("-", " ")
    q_words = tokenize(query)
    fn_words = tokenize(clean_fn)
    text_words = tokenize(text)
    doc_words = fn_words + text_words

    if not q_words or not doc_words:
        return 0.0

    token_scores = []
    for qw in q_words:
        best_token_score = 0.0
        fn_match = False
        for fw in fn_words:
            sim = fuzzy_word_similarity(qw, fw)
            if sim >= 0.74:
                fn_match = True
                best_token_score = max(best_token_score, sim)

        match_count = 0
        for tw in text_words:
            sim = fuzzy_word_similarity(qw, tw)
            if sim > best_token_score:
                best_token_score = sim
            if sim >= 0.74:
                match_count += 1

        boost = 0.0
        if fn_match:
            boost += 0.05
        if match_count > 1:
            boost += min(0.04, 0.01 * (match_count - 1))

        final_token_score = min(0.99, best_token_score + boost) if best_token_score > 0 else 0.0
        token_scores.append(final_token_score)

    return sum(token_scores) / len(token_scores)


def fuzzy_search(query: str, min_score: float = 0.65) -> List[Dict[str, Any]]:
    """
    Searches all stored images for approximate/fuzzy matches to the query.
    """
    cleaned = query.strip()
    if not cleaned:
        return []

    all_rows = database.list_images()
    results = []

    for row in all_rows:
        score = compute_fuzzy_score(cleaned, row["extracted_text"], row["image_name"])
        if score >= min_score:
            ocr_conf = float(row.get("ocr_confidence", 0.85) or 0.85)
            # Confidence weighting: high-confidence OCR text is prioritized over noisy text
            weighted_score = score * (0.75 + 0.25 * ocr_conf)
            results.append({
                "id": row["id"],
                "image_name": row["image_name"],
                "image_path": row["image_path"],
                "matched_text": row["extracted_text"],
                "raw_fuzzy_score": round(score, 3),
                "match_score": round(weighted_score, 3),
                "ocr_confidence": ocr_conf,
                "is_exact": False,
            })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results
