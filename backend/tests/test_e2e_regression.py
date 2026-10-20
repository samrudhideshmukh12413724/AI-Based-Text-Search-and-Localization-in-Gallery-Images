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


from app import database


def _get_owner_for_image_stem(stem: str) -> dict:
    """Helper to dynamically resolve the user account that owns the regression document."""
    conn = database._connect()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM images WHERE image_name LIKE ? LIMIT 1", (f"%{stem}%",))
    row = cursor.fetchone()
    conn.close()
    uid = row[0] if (row and row[0]) else 1
    return {"id": uid, "username": f"user_{uid}"}


@pytest.mark.parametrize("query,expected_image_stem,min_score", TARGET_QUERIES)
def test_e2e_query_retrieval(query: str, expected_image_stem: str, min_score: float):
    """Verify that every key user upload is returned at Top 1 with exact score and bounding boxes."""
    req = SearchRequest(query=query)
    owner = _get_owner_for_image_stem(expected_image_stem)
    res = search_images(body=req, current_user=owner)

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
