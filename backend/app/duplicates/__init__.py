"""Duplicate & Near-Duplicate Detection Package."""

from app.duplicates.hasher import (
    compute_sha256,
    compute_phash,
    hamming_distance,
    phash_similarity,
)
from app.duplicates.detector import check_duplicate
from app.duplicates.grouping import group_corpus
from app.duplicates.collapsing import collapse_duplicate_results

__all__ = [
    "compute_sha256",
    "compute_phash",
    "hamming_distance",
    "phash_similarity",
    "check_duplicate",
    "group_corpus",
    "collapse_duplicate_results",
]


