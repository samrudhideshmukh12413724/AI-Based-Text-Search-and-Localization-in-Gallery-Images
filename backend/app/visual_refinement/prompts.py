"""Prompt Ensembling Module for Phase 4 Step 7A: Modular CLIP Open-Vocabulary Search Refinement.

Constructs deterministic, generic prompt templates for arbitrary visual queries without
hardcoding object-specific lists.
"""

from typing import List
import re


def sanitize_query(query: str) -> str:
    """Deterministically sanitizes, trims, and normalizes user query string."""
    if not query:
        return ""
    # Normalize multiple whitespaces into a single space, strip, and lowercase
    cleaned = re.sub(r"\s+", " ", query.strip()).lower()
    return cleaned


def build_prompt_ensemble(query: str) -> List[str]:
    """
    Generates a deterministic generic prompt ensemble for an arbitrary visual query Q.
    
    Templates:
      1. Q
      2. 'a photo of {Q}'
      3. 'an image containing {Q}'
      4. 'a photo or image of {Q}'
      5. 'an official {Q}'
      6. 'a document containing {Q}'
    
    Guarantees:
      - Deterministic ordering
      - Open-vocabulary: works for any natural language visual query
      - Safe fallback on empty/whitespace queries
    """
    clean_q = sanitize_query(query)
    if not clean_q:
        return []

    return [
        clean_q,
        f"a photo of {clean_q}",
        f"an image containing {clean_q}",
        f"a photo or image of {clean_q}",
        f"an official {clean_q}",
        f"a document containing {clean_q}",
        f"an official document containing {clean_q}",
    ]
