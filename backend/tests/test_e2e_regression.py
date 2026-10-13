"""End-to-End Query Regression Suite validating search scores and grounded bounding boxes."""

import pytest
from app.main import search_images, SearchRequest


TARGET_QUERIES = [
    ("Kesariyo", "1000182254", 1.0),
    ("Avneet", "1000182254", 1.0),
    ("Kaur", "1000182254", 1.0),
    ("Yash Lawns", "1000182254", 1.0),
    ("Title Sponsor", "1000182254", 1.0),
    ("Spanish", "1000181517", 1.0),
    ("Narhari", "1000180211", 1.0),
    ("Apple", "Screenshot 2026-09-02", 1.0),
    ("Google", "Screenshot 2026-09-02", 1.0),
    ("SHA 256", "1000179579", 1.0),
]


@pytest.mark.parametrize("query,expected_image_stem,min_score", TARGET_QUERIES)
def test_e2e_query_retrieval(query: str, expected_image_stem: str, min_score: float):
    """Verify that every key user upload is returned at Top 1 with exact score and bounding boxes."""
    req = SearchRequest(query=query)
    res = search_images(body=req, current_user={"id": 1, "username": "admin"})

    assert res["count"] >= 1, f"Query '{query}' produced 0 results"
    top = res["matched_images"][0]
    
    assert expected_image_stem in top["image_name"], (
        f"Query '{query}': expected '{expected_image_stem}' in top result, got '{top['image_name']}'"
    )
    assert top["similarity_score"] >= min_score, (
        f"Query '{query}': expected score >= {min_score}, got {top['similarity_score']}"
    )
    # Verify in-image bounding boxes exist for yellow highlight rendering
    t_boxes = top.get("text_bounding_boxes", [])
    assert len(t_boxes) >= 1, f"Query '{query}': expected in-image bounding boxes, got 0"
