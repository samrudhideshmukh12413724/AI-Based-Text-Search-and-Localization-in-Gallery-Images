"""Unit and integration tests for Multi-Orientation OCR Engine."""

import numpy as np
import pytest
from pathlib import Path
from app.ocr.ocr_engine import _unrotate_poly, _box_iou, extract_text_adaptive


def test_unrotate_poly_0_deg():
    """Orientation 0 should preserve coordinates identically."""
    pts = np.array([[10, 20], [30, 40]], dtype=np.float32)
    unrot = _unrotate_poly(pts, "0", H_sc=1000, W_sc=800)
    assert np.allclose(pts, unrot)


def test_unrotate_poly_90_cw():
    """Verify exact 90° CW inverse coordinate transformation."""
    # If point in original scaled image is (x=100, y=200) with H=1000, W=800
    # In 90 CW: x_rot = H - 1 - y = 799, y_rot = x = 100
    pts_rot = np.array([[799.0, 100.0]], dtype=np.float32)
    unrot = _unrotate_poly(pts_rot, "90_cw", H_sc=1000, W_sc=800)
    assert round(unrot[0, 0]) == 100
    assert round(unrot[0, 1]) == 200


def test_unrotate_poly_90_ccw():
    """Verify exact 90° CCW inverse coordinate transformation."""
    # If point in original scaled image is (x=100, y=200) with H=1000, W=800
    # In 90 CCW: x_rot = y = 200, y_rot = W - 1 - x = 699
    pts_rot = np.array([[200.0, 699.0]], dtype=np.float32)
    unrot = _unrotate_poly(pts_rot, "90_ccw", H_sc=1000, W_sc=800)
    assert round(unrot[0, 0]) == 100
    assert round(unrot[0, 1]) == 200


def test_unrotate_poly_180():
    """Verify exact 180° inverse coordinate transformation."""
    # In 180: x_rot = W - 1 - x = 699, y_rot = H - 1 - y = 799
    pts_rot = np.array([[699.0, 799.0]], dtype=np.float32)
    unrot = _unrotate_poly(pts_rot, "180", H_sc=1000, W_sc=800)
    assert round(unrot[0, 0]) == 100
    assert round(unrot[0, 1]) == 200


def test_box_iou_exact_overlap():
    """Identical bounding boxes should produce IoU = 1.0."""
    b1 = {"x": 100, "y": 100, "width": 50, "height": 50}
    b2 = {"x": 100, "y": 100, "width": 50, "height": 50}
    assert _box_iou(b1, b2) == pytest.approx(1.0, 0.01)


def test_box_iou_disjoint():
    """Non-overlapping bounding boxes should produce IoU = 0.0."""
    b1 = {"x": 0, "y": 0, "width": 50, "height": 50}
    b2 = {"x": 200, "y": 200, "width": 50, "height": 50}
    assert _box_iou(b1, b2) == 0.0


def test_box_iou_partial_overlap():
    """Partial overlap should return legitimate IoU in (0, 1)."""
    b1 = {"x": 0, "y": 0, "width": 100, "height": 100}
    b2 = {"x": 50, "y": 0, "width": 100, "height": 100}
    # Intersection: 50 * 100 = 5000; Union: 10000 + 10000 - 5000 = 15000 -> IoU = 0.333
    assert _box_iou(b1, b2) == pytest.approx(0.333, 0.01)


def test_extract_text_adaptive_synthetic():
    """Verify extract_text_adaptive runs on an image and returns expected schema."""
    test_img = Path(__file__).resolve().parents[1] / "test.jpg"
    if not test_img.exists():
        pytest.skip("test.jpg not found")

    res = extract_text_adaptive(test_img)
    assert isinstance(res, dict)
    assert "text" in res
    assert "confidence" in res
    assert "word_boxes" in res
    assert isinstance(res["word_boxes"], list)
    assert res["confidence"] >= 0.0
