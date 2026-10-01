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


def extract_best_sentence(query_embedding: np.ndarray, text: str, model=None) -> str:
    """
    Split text into logical sentences/clauses and select the one with highest semantic relevance.
    Falls back to first 150 chars if no clean sentence boundary found.
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

    if len(sentences) == 1 or query_embedding is None:
        return sentences[0][:180].strip()

    if model is None:
        model = get_embedding_model()

    sent_embs = model.encode(sentences, convert_to_numpy=True, normalize_embeddings=True)
    scores = np.dot(sent_embs, query_embedding)
    best_idx = int(np.argmax(scores))

    best_sentence = sentences[best_idx]
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

    candidates = _generate_candidate_phrases(text, max_n=3)
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


def build_highlight_payload(
    query: str,
    raw_text: str,
    search_type: str = "semantic",
    query_embedding: np.ndarray = None,
    threshold: float = 0.38,
    max_terms: int = 4,
) -> dict:
    """
    Construct the full highlight payload for a single document search result.
    """
    model = get_embedding_model()

    if query_embedding is None and query:
        query_embedding = model.encode(query, convert_to_numpy=True, normalize_embeddings=True)

    # 1. Best preview sentence
    preview = extract_best_sentence(query_embedding, raw_text, model=model)
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
        highlight_terms = get_semantic_highlights(
            query_embedding,
            preview,
            model=model,
            threshold=threshold,
            max_terms=max_terms,
        )
        # If preview had few terms, supplement from full text
        if len(highlight_terms) < 2:
            full_terms = get_semantic_highlights(
                query_embedding,
                raw_text,
                model=model,
                threshold=threshold,
                max_terms=max_terms,
            )
            for t in full_terms:
                if t not in highlight_terms and len(highlight_terms) < max_terms:
                    highlight_terms.append(t)
        matched_concepts = highlight_terms[:3]

    return {
        "preview_snippet": preview,
        "highlight_terms": highlight_terms,
        "matched_concepts": matched_concepts,
    }
