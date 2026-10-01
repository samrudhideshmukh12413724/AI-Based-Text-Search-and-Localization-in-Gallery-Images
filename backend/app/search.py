"""Backward-compatible wrapper routing to the modular search package."""

from app.search import (
    search,
    exact_search,
    fuzzy_search,
    compute_exact_score,
    damerau_levenshtein_distance,
    tokenize,
)

# Export legacy interface
run_search = search


