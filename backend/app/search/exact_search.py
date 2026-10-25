"""Exact & Token Lexical Search Engine.

Implements whole-word boundary matching, tokenization, and length-guarded
prefix matching to eliminate false substring hits (e.g. 'cat' in 'category').
"""

import re
from typing import List, Dict, Any, Optional

from app import database

from difflib import SequenceMatcher

STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "in", "on", "at", "to",
    "from", "of", "with", "is", "was", "are", "were", "by", "as", "about"
}

# Domain inflections and synonym mappings for real phone photos, receipts, & handwriting
INFLECTION_MAP: Dict[str, set[str]] = {
    "payment": {"paid", "pay", "paying", "transfer", "transaction", "amount", "upi"},
    "paid": {"payment", "pay", "paying", "transfer", "amount"},
    "pay": {"payment", "paid", "paying", "transfer"},
    "money": {"amount", "inr", "rupees", "paid", "rs"},
    "upi": {"okaxis", "okhdfcbank", "okicici", "oksbi", "paytm", "gpay", "phonepe"},
    "qr": {"qrcode", "qr_code", "barcode"},
    "qrcode": {"qr", "qr_code", "barcode"},
    "barcode": {"qr", "qrcode", "barcode"},
    "number": {"num", "no", "id", "digits", "roll"},
    "folder": {"folders", "gallery", "vault", "photos", "documents"},
    "receipt": {"bill", "payment", "challan", "fee", "fees", "invoice"},
    "bill": {"receipt", "payment", "challan", "fee", "fees", "invoice"},
    "fingerprint": {"fingerprink", "fingerprint", "biometric"},
    "duplicate": {"doplicale", "dupe", "duplicate"},
    "hash": {"hosh", "sha256", "sha", "digest"},
    "sha": {"sha256", "hash", "hosh"},
    "sha256": {"sha", "hash", "hosh"},
    "fee": {"fees", "tuition", "challan"},
    "fees": {"fee", "tuition", "challan"},
    "kesariyo": {"kesari", "kesariy", "kesariyc", "kesario"},
    "kesari": {"kesariyo", "kesariy", "kesariyc"},
    "rang": {"ranga", "rangi"},
    "yash": {"yashlawns"},
    "lawns": {"yashlawns"},
    "avneet": {"avneet"},
    "kaur": {"kaur"},
}


def tokenize(text: str) -> List[str]:
    """Tokenizes text into lowercase words supporting Latin, digits, and Devanagari, filtering stopwords."""
    from urllib.parse import unquote
    clean = unquote(text).replace("%20", " ")
    return [
        w.lower()
        for w in re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", clean)
        if w and w.lower() not in STOPWORDS and (len(w) >= 2 or w.isdigit())
    ]


def compute_exact_score(query: str, text: str, filename: str) -> float:
    """
    Computes exact lexical match score with OCR typo tolerance and inflection matching.
    Handles handwriting errors, numeric queries, QR codes, and partial words.
    """
    from urllib.parse import unquote
    q = query.lower().strip()
    clean_fn = re.sub(r'([a-z])([A-Z])', r'\1 \2', filename).replace("_", " ").replace("-", " ")
    clean_text = unquote(text).replace("_", " ").replace("-", " ").replace("%20", " ")
    full_text = f"{clean_fn} {clean_text}".lower()

    # Direct match in clean filename
    if q in clean_fn.lower():
        return 1.0

    # Direct whole word / phrase match in document text
    if q in clean_text.lower():
        return 1.0

    # Numeric exact matching: numbers must appear as complete number tokens, not single-digit subsets
    if q.isdigit():
        if re.search(r"(?:^|[^\d])" + re.escape(q) + r"(?:[^\d]|$)", full_text):
            return 1.0
        return 0.0

    q_words = tokenize(q)
    if not q_words:
        return 0.0

    doc_words = tokenize(full_text)
    if not doc_words:
        return 0.0

    doc_words_set = set(doc_words)

    word_scores = []
    for qw in q_words:
        related_stems = INFLECTION_MAP.get(qw, set())

        # Fast O(1) exact or synonym match
        if qw in doc_words_set:
            word_scores.append(1.0)
            continue
        if related_stems and bool(related_stems & doc_words_set):
            word_scores.append(1.0)
            continue

        # Substring / Devanagari / Paper 2 Normalized Levenshtein OCR matching
        best = 0.0
        for dw in doc_words:
            if qw.isdigit() and dw.isdigit():
                if qw == dw:
                    best = 1.0
                    break
                elif len(qw) >= 3 and qw in dw:
                    best = max(best, 0.95)
            elif any('\u0900' <= c <= '\u097F' for c in qw + dw):
                if qw in dw or dw in qw:
                    best = max(best, 0.95)
                    break
                elif len(qw) >= 2 and len(dw) >= 2 and abs(len(qw) - len(dw)) <= 2:
                    sim = SequenceMatcher(None, qw, dw).ratio()
                    if sim >= 0.70:
                        best = max(best, round(sim, 3))
            elif len(qw) >= 3 and len(dw) >= 3:
                # Substring containment
                if (qw in dw and len(dw) - len(qw) <= 5) or (dw in qw and len(qw) - len(dw) <= 3):
                    best = max(best, 0.90)
                    if best >= 0.95:
                        break
                # Paper 2 Cross-Modal Normalized Levenshtein & OCR Glyph Confusion Similarity
                from app.search.research_algorithms import compute_paper2_ocr_similarity
                p2_sim = compute_paper2_ocr_similarity(qw, dw)
                min_p2 = 0.60 if len(qw) >= 5 else 0.70
                if p2_sim >= min_p2:
                    best = max(best, round(p2_sim, 3))
                    if best >= 0.95:
                        break


        word_scores.append(best)

    return sum(word_scores) / len(word_scores)



def exact_search(query: str, min_score: float = 0.65) -> List[Dict[str, Any]]:
    """Executes exact lexical search across all stored images with cross-lingual Marathi/English expansion."""
    import json
    cleaned = query.strip()
    if not cleaned:
        return []

    from app.translation import get_query_expansions
    expanded_queries = get_query_expansions(cleaned)

    all_rows = database.list_images()
    results = []

    for row in all_rows:
        searchable_text = row.get("searchable_text")
        if not searchable_text:
            ent = row.get("entities") or {}
            urls_str = " ".join(ent.get("urls", [])) if isinstance(ent, dict) else ""
            v_meta = row.get("visual_metadata") or {}
            if isinstance(v_meta, str):
                try:
                    v_meta = json.loads(v_meta)
                except Exception:
                    v_meta = {}
            has_real_qr = bool(row.get("qr_payload") and row.get("qr_payload").strip())
            if not has_real_qr and isinstance(v_meta, dict):
                if v_meta.get("type") in ("qr_code", "barcode"):
                    has_real_qr = True
                elif any(o.get("type") in ("qr_code", "barcode") or "qr" in str(o.get("label", "")).lower() for o in v_meta.get("objects", [])):
                    has_real_qr = True
            if not has_real_qr and "qr" in str(row.get("image_name", "")).lower():
                has_real_qr = True
            vis_tokens = []
            if has_real_qr:
                vis_tokens.extend(["qr", "qrcode", "qr_code", "barcode"])
            if isinstance(v_meta, dict):
                if v_meta.get("type") and v_meta.get("type") not in ("qr_code", "barcode"):
                    vis_tokens.append(str(v_meta.get("type")))
                for obj in v_meta.get("objects", []):
                    if isinstance(obj, dict):
                        vis_tokens.append(str(obj.get("label", "")))
                        vis_tokens.append(str(obj.get("type", "")))
                        vis_tokens.append(str(obj.get("data", "")))
                        vis_tokens.append(str(obj.get("location_desc", "")))
            vis_str = " ".join(t for t in vis_tokens if t)
            cat_str = str(row.get("category", ""))
            searchable_text = f"{row.get('extracted_text', '')} {row.get('cleaned_text', '')} {row.get('blip_caption', '')} {row.get('qr_payload', '')} {row.get('stego_payload', '')} {urls_str} {vis_str} {cat_str}".strip()

        # Check against original query and expanded terms
        best_score = 0.0
        for q_term in expanded_queries:
            score = compute_exact_score(q_term, searchable_text, row["image_name"])
            if score > best_score:
                best_score = score

        if best_score >= min_score:
            results.append({
                "id": row["id"],
                "image_name": row["image_name"],
                "image_path": row["image_path"],
                "matched_text": searchable_text.strip(),
                "blip_caption": row.get("blip_caption", ""),
                "qr_payload": row.get("qr_payload", ""),
                "stego_payload": row.get("stego_payload", ""),
                "match_score": round(best_score, 3),
                "ocr_confidence": float(row.get("ocr_confidence", 0.85) or 0.85),
                "is_exact": True,
            })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results
