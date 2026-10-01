"""Search package public interface."""

from app.search.exact_search import exact_search, compute_exact_score, tokenize
from app.search.fuzzy_search import fuzzy_search, damerau_levenshtein_distance
from app.search.ranking import unified_text_search
from app.search.metadata_search import metadata_search as search, metadata_search, parse_temporal_query
from app.search.metadata_extractor import extract_image_metadata

__all__ = [
    "search",
    "metadata_search",
    "parse_temporal_query",
    "extract_image_metadata",
    "unified_text_search",
    "exact_search",
    "fuzzy_search",
    "compute_exact_score",
    "damerau_levenshtein_distance",
    "tokenize",
]
