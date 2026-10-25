"""Search package public interface."""

from app.search.exact_search import exact_search, compute_exact_score, tokenize
from app.search.fuzzy_search import fuzzy_search, damerau_levenshtein_distance
from app.search.ranking import unified_text_search
from app.search.metadata_search import metadata_search as search, metadata_search, parse_temporal_query
from app.search.metadata_extractor import extract_image_metadata

from app.search.research_algorithms import (
    BoyerMooreHorspoolMatcher,
    compute_dice_similarity,
    bounded_dice_search,
    bpe_subword_tokenize,
    bpe_inclusive_or_score,
    compute_cross_weighted_product_score,
    compute_cross_weighted_similarity,
    calculate_power_grid_comprehensive_score,
    compute_normalized_levenshtein,
    ocr_glyph_normalize,
    compute_paper2_ocr_similarity,
)
from app.search.positional_inverted_index import (
    PositionalInvertedIndex,
    get_positional_inverted_index,
)

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
    "BoyerMooreHorspoolMatcher",
    "compute_dice_similarity",
    "bounded_dice_search",
    "bpe_subword_tokenize",
    "bpe_inclusive_or_score",
    "compute_cross_weighted_product_score",
    "compute_cross_weighted_similarity",
    "calculate_power_grid_comprehensive_score",
    "compute_normalized_levenshtein",
    "ocr_glyph_normalize",
    "compute_paper2_ocr_similarity",
    "PositionalInvertedIndex",
    "get_positional_inverted_index",
]

