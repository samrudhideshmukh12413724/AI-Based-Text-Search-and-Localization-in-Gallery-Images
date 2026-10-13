"""Unit tests for Word Highlighting and Bounding Box Geometry."""

import pytest
from app.highlighting import get_keyword_highlights, build_highlight_payload


def test_get_keyword_highlights_extraction():
    """Verify extracted query terms from snippet."""
    query = "Avneet Kaur"
    text = "KESARIYO RANG starring Avneet Kaur live at Yash Lawns"
    highlights = get_keyword_highlights(query, text)
    assert any("avneet" in h.lower() for h in highlights)
    assert any("kaur" in h.lower() for h in highlights)


def test_build_highlight_payload_normalized_boxes():
    """Verify that bounding boxes are properly normalized between 0.0 and 1.0."""
    word_boxes = [
        {
            "text": "AVNEET",
            "confidence": 0.85,
            "bbox": {"x": 100, "y": 200, "width": 300, "height": 100}
        }
    ]
    payload = build_highlight_payload(
        query="Avneet",
        raw_text="AVNEET KAUR",
        search_type="keyword",
        word_boxes=word_boxes,
        image_width=1000,
        image_height=2000
    )

    t_boxes = payload.get("text_bounding_boxes", [])
    assert len(t_boxes) == 1
    norm = t_boxes[0]["normalized_bbox"]
    assert norm["x"] == pytest.approx(0.1, 0.01)
    assert norm["y"] == pytest.approx(0.1, 0.01)
    assert norm["width"] == pytest.approx(0.3, 0.01)
    assert norm["height"] == pytest.approx(0.05, 0.01)
