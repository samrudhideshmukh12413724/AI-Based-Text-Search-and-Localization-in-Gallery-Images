"""Unit tests for Duplicate Collapsing & Non-Hijacking."""

import pytest
from app.duplicates.collapsing import collapse_duplicate_results


def test_collapse_preserves_matching_representative():
    """Verify that a matching image is never replaced with an irrelevant parent."""
    fused_results = [
        {
            "id": 100,
            "image_name": "matching_child.jpg",
            "is_duplicate": True,
            "canonical_image_id": 1,
            "canonical_image_name": "unrelated_parent.jpg",
            "similarity_score": 1.0,
            "search_type": "keyword",
            "matched_text": "Narhari Deshmukh paid rent",
        }
    ]

    collapsed = collapse_duplicate_results(fused_results)
    assert len(collapsed) == 1
    rep = collapsed[0]
    # The representative card MUST be the matching item, not the parent!
    assert rep["id"] == 100
    assert rep["image_name"] == "matching_child.jpg"
    assert rep["similarity_score"] == 1.0
