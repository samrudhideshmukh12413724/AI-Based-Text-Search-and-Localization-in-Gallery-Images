"""Smart word & phrase highlighting and text preview extraction for Keyword and Semantic search."""

import re
import numpy as np
from app.semantic_search import get_embedding_model

STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "in", "on", "at", "to", "from", "of", 
    "with", "is", "was", "are", "were", "by", "as", "about", "can", "this", "that", 
    "these", "those", "it", "its", "be", "been", "being", "have", "has", "had", 
    "do", "does", "did", "will", "would", "shall", "should", "may", "might", "must"
}


def _clean_text_for_split(text: str) -> str:
    # Replace multiple whitespaces/newlines with single spaces
    return re.sub(r"\s+", " ", text).strip()


def extract_best_sentence(query_embedding: np.ndarray, text: str, model=None, query_text: str = "") -> str:
    """
    Split text into logical sentences/clauses and select the one with highest semantic relevance.
    Falls back to first 150 chars if no clean sentence boundary found.
    Fast O(1) lexical matching is checked first when query_text is available, avoiding neural sentence encodings.
    """
    if not text or not text.strip():
        return ""

    raw_chunks = re.split(r"(?<=[.!?\n|])\s+", text)
    sentences = []
    for s in raw_chunks:
        cleaned_s = s.strip()
        # Skip pure metadata boilerplate (e.g. "ID: 001 Category: SCHOLARSHIP")
        if re.match(r"^ID:\s*\d+\s*(?:Category:.*)?$", cleaned_s, re.IGNORECASE):
            continue
        if len(cleaned_s) >= 15:
            sentences.append(cleaned_s)

    if not sentences:
        # Fallback to any non-empty chunk
        sentences = [s.strip() for s in raw_chunks if s.strip()]

    if not sentences:
        return text[:160].strip()

    # 1. Fast Lexical Shortcut: Check if any sentence matches query terms directly
    if query_text:
        q_words = [w.lower() for w in re.findall(r"\w+", query_text) if len(w) >= 3 and w.lower() not in STOPWORDS]
        if not q_words:
            q_words = [w.lower() for w in re.findall(r"\w+", query_text) if len(w) >= 2]
        if q_words:
            # Prefer sentence containing all query words
            for s in sentences:
                s_low = s.lower()
                if all(w in s_low for w in q_words):
                    return s if len(s) <= 200 else s[:197] + "..."
            # Next prefer sentence containing any query word
            for s in sentences:
                s_low = s.lower()
                if any(w in s_low for w in q_words):
                    return s if len(s) <= 200 else s[:197] + "..."

    if len(sentences) == 1 or query_embedding is None:
        return sentences[0][:180].strip()

    # 2. Semantic Fallback: encode only top 4 candidate sentences
    cand_sentences = sentences[:4]
    if model is None:
        model = get_embedding_model()

    sent_embs = model.encode(cand_sentences, convert_to_numpy=True, normalize_embeddings=True)
    scores = np.dot(sent_embs, query_embedding)
    best_idx = int(np.argmax(scores))

    best_sentence = cand_sentences[best_idx]
    if len(best_sentence) > 200:
        best_sentence = best_sentence[:197] + "..."
    return best_sentence


def get_keyword_highlights(query: str, text: str) -> list[str]:
    """
    Extract exact and case-insensitive query word matches from text.
    """
    if not query or not text:
        return []

    q_tokens = [w.lower() for w in re.findall(r"\w+", query) if len(w) >= 3 and w.lower() not in STOPWORDS]
    if not q_tokens:
        q_tokens = [w.lower() for w in re.findall(r"\w+", query) if w]

    matched_spans = []
    text_lower = text.lower()

    for token in q_tokens:
        # Find exact word boundaries or substring occurrences in text
        pattern = re.compile(rf"\b{re.escape(token)}\w*", re.IGNORECASE)
        for match in pattern.finditer(text):
            matched_spans.append(match.group(0))

    # Deduplicate preserving original case found in text
    seen = set()
    result = []
    for term in matched_spans:
        t_low = term.lower()
        if t_low not in seen:
            seen.add(t_low)
            result.append(term)
    return result


def _generate_candidate_phrases(text: str, max_n: int = 3) -> list[str]:
    """
    Generate natural 1-gram, 2-gram, and 3-gram candidate phrases from text clauses.
    """
    clauses = re.split(r"[,;:.!?\n|/()]+", text)
    candidates = []

    for clause in clauses:
        words = [w.strip() for w in re.findall(r"\b\w+(?:[-']\w+)?\b", clause) if w.strip()]
        if not words:
            continue

        for n in range(1, min(max_n, len(words)) + 1):
            for i in range(len(words) - n + 1):
                ngram = words[i:i+n]
                # Filter if starting or ending with a stopword
                if ngram[0].lower() in STOPWORDS or ngram[-1].lower() in STOPWORDS:
                    continue
                phrase = " ".join(ngram)
                if len(phrase) >= 3 and not phrase.isdigit() and phrase.lower() not in STOPWORDS:
                    candidates.append(phrase)

    # Deduplicate preserving order
    return list(dict.fromkeys(candidates))


def _filter_and_subsume_phrases(scored_phrases: list[tuple[str, float]], max_terms: int = 4) -> list[str]:
    """
    Sort candidate phrases and eliminate redundant sub-phrases (e.g. prefer 'education loan' over 'loan').
    """
    # Sort descending by score, and on tie, by longer length
    sorted_candidates = sorted(scored_phrases, key=lambda x: (x[1], len(x[0])), reverse=True)
    
    accepted = []
    for phrase, score in sorted_candidates:
        phrase_lower = phrase.lower()
        
        # Check if already covered by an accepted longer phrase
        already_covered = False
        for acc in accepted:
            acc_lower = acc.lower()
            if phrase_lower in acc_lower or acc_lower in phrase_lower:
                already_covered = True
                break
                
        if not already_covered:
            accepted.append(phrase)
            if len(accepted) >= max_terms:
                break

    return accepted


def get_semantic_highlights(
    query_embedding: np.ndarray,
    text: str,
    model=None,
    threshold: float = 0.38,
    max_terms: int = 4,
) -> list[str]:
    """
    Identify the most semantically relevant phrases/concepts in the document text.
    Prefers longer meaningful phrases and limits output to top 3-5 distinct concepts.
    """
    if not text or not text.strip() or query_embedding is None:
        return []

    candidates = _generate_candidate_phrases(text, max_n=3)[:10]
    if not candidates:
        return []

    if model is None:
        model = get_embedding_model()

    c_embs = model.encode(candidates, convert_to_numpy=True, normalize_embeddings=True)
    scores = np.dot(c_embs, query_embedding)

    scored_candidates = [
        (cand, float(score))
        for cand, score in zip(candidates, scores)
        if score >= threshold
    ]

    if not scored_candidates:
        # Fallback: if no phrase meets threshold >= 0.38, check top candidate >= 0.32
        top_candidates = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        if top_candidates and top_candidates[0][1] >= 0.32:
            scored_candidates = [(top_candidates[0][0], float(top_candidates[0][1]))]

    return _filter_and_subsume_phrases(scored_candidates, max_terms=max_terms)


def get_text_bounding_boxes(
    query: str,
    word_boxes: list[dict],
    image_width: int = 0,
    image_height: int = 0,
    highlight_terms: list[str] = None
) -> list[dict]:
    """
    Finds word bounding boxes matching the query or keyword tokens,
    converting pixel coordinates to normalized bounding box overlays.
    """
    if not word_boxes:
        return []

    targets = list(highlight_terms or [])
    if query:
        q_tokens = [w.lower() for w in re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", query) if len(w) >= 2 and w.lower() not in STOPWORDS]
        targets.extend(q_tokens)

    if not targets:
        return []

    # Extract all individual significant words from targets (including Devanagari)
    target_words = set()
    for t in targets:
        t_str = str(t).strip().lower()
        if not t_str:
            continue
        for w in re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", t_str):
            if len(w) >= 2 and w not in STOPWORDS:
                target_words.add(w)

    if not target_words:
        return []

    from difflib import SequenceMatcher
    from app.search.exact_search import INFLECTION_MAP
    from app.translation import get_query_expansions

    expanded_target_words = set(target_words)
    for tw in list(target_words):
        if tw in INFLECTION_MAP:
            expanded_target_words.update(INFLECTION_MAP[tw])
        for exp in get_query_expansions(tw):
            for ew in re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", exp.lower()):
                if len(ew) >= 2:
                    expanded_target_words.add(ew)

    # Dynamic fallback for image dimensions if not pre-populated in database
    eff_w = image_width
    eff_h = image_height
    if eff_w <= 0 or eff_h <= 0:
        valid_boxes_w = [b.get("bbox", {}).get("x", 0) + b.get("bbox", {}).get("width", 0) for b in word_boxes if b.get("bbox")]
        valid_boxes_h = [b.get("bbox", {}).get("y", 0) + b.get("bbox", {}).get("height", 0) for b in word_boxes if b.get("bbox")]
        if valid_boxes_w and valid_boxes_h:
            eff_w = max(int(max(valid_boxes_w) * 1.04), 100)
            eff_h = max(int(max(valid_boxes_h) * 1.04), 100)
        else:
            eff_w = 1000
            eff_h = 1333

    clean_q_raw = query.strip().lower()
    clean_q_noprot = re.sub(r"^https?://(www\.)?", "", clean_q_raw)

    matched_boxes = []
    seen = set()

    for box in word_boxes:
        w_text = box.get("text", "").strip()
        if not w_text or len(w_text) < 2:
            continue

        w_lower = w_text.lower()
        w_noprot = re.sub(r"^https?://(www\.)?", "", w_lower)
        box_tokens = [w.lower() for w in re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", w_lower)]

        is_match = False

        # 1. Direct URL / Phrase matching in crowded documents
        if len(clean_q_raw) >= 3 and (clean_q_raw in w_lower or (len(clean_q_noprot) >= 4 and clean_q_noprot in w_noprot)):
            is_match = True

        # 2. Token / Concept matching
        if not is_match:
            for tw in expanded_target_words:
                if tw in box_tokens:
                    is_match = True
                    break
                # Substring matching for longer terms
                if any((tw in bt or bt in tw) for bt in box_tokens if len(bt) >= 3 and len(tw) >= 3):
                    is_match = True
                    break
                # Fuzzy typo matching for OCR handwriting / camera errors
                if any(len(tw) >= 4 and len(bt) >= 4 and SequenceMatcher(None, tw, bt).ratio() >= 0.75 for bt in box_tokens):
                    is_match = True
                    break

        if is_match:
            bbox = box.get("bbox", {})
            if not bbox or "x" not in bbox or bbox.get("width", 0) <= 0:
                continue

            x, y, w, h = int(bbox["x"]), int(bbox["y"]), int(bbox["width"]), int(bbox["height"])
            box_key = (x, y, w, h)
            if box_key in seen:
                continue
            seen.add(box_key)

            norm_bbox = {
                "x": round(x / eff_w, 4),
                "y": round(y / eff_h, 4),
                "width": round(w / eff_w, 4),
                "height": round(h / eff_h, 4)
            }

            matched_boxes.append({
                "label": f"Text Match: {w_text}",
                "type": "text_highlight",
                "text": w_text,
                "confidence": str(box.get("confidence", 0.95)),
                "location_desc": "In-Image Text",
                "bbox": {"x": x, "y": y, "width": w, "height": h},
                "normalized_bbox": norm_bbox,
                "data": f"Matched Text: {w_text}"
            })

    return matched_boxes


def build_highlight_payload(
    query: str,
    raw_text: str,
    search_type: str = "semantic",
    query_embedding: np.ndarray = None,
    threshold: float = 0.38,
    max_terms: int = 4,
    word_boxes: list[dict] = None,
    image_width: int = 0,
    image_height: int = 0,
) -> dict:
    """
    Construct the full highlight payload for a single document search result,
    including preview snippet, matched concepts, and in-image text bounding boxes.
    """
    model = None
    if search_type != "keyword":
        if query_embedding is None and query:
            model = get_embedding_model()
            query_embedding = model.encode(query, convert_to_numpy=True, normalize_embeddings=True)

    # 1. Best preview sentence (uses instant lexical matching when available)
    preview = extract_best_sentence(query_embedding, raw_text, model=model, query_text=query)
    if not preview:
        preview = raw_text[:160].strip()

    # 2. Extract highlight terms based on search type
    if search_type == "keyword":
        highlight_terms = get_keyword_highlights(query, preview)
        # If preview didn't contain all keyword terms, check full text
        if not highlight_terms:
            highlight_terms = get_keyword_highlights(query, raw_text)
        matched_concepts = highlight_terms[:3]
    else:
        # Semantic mode: extract semantically relevant concepts
        highlight_terms = (
            get_semantic_highlights(
                query_embedding,
                preview,
                model=model,
                threshold=threshold,
                max_terms=max_terms,
            )
            if query_embedding is not None
            else []
        )
        # If preview had few terms, supplement from first 250 chars of full text
        if len(highlight_terms) < 2 and query_embedding is not None:
            full_terms = get_semantic_highlights(
                query_embedding,
                raw_text[:250],
                model=model,
                threshold=threshold,
                max_terms=max_terms,
            )
            for t in full_terms:
                if t not in highlight_terms and len(highlight_terms) < max_terms:
                    highlight_terms.append(t)
        matched_concepts = highlight_terms[:3]

    text_boxes = get_text_bounding_boxes(
        query=query,
        word_boxes=word_boxes or [],
        image_width=image_width,
        image_height=image_height,
        highlight_terms=highlight_terms,
    )

    return {
        "preview_snippet": preview,
        "highlight_terms": highlight_terms,
        "matched_concepts": matched_concepts,
        "text_bounding_boxes": text_boxes,
    }

