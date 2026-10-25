"""Unit test suite for Paper 4 (Yan et al., IEEE TNNLS 2024 / MANet) Future Scope Extensions.

Verifies:
1. Illumination-invariant CLAHE normalization (mitigating the author's identified color vulnerability)
2. Occlusion-aware dynamic body part scaling
3. Cross-modal text-on-clothing OCR fusion (linking optical text on apparel with person search)
"""

import json
import numpy as np
import pytest
from PIL import Image

from app.person_search import (
    normalize_illumination_clahe,
    extract_dominant_clothing_colors,
    detect_occlusion_and_scale_parts,
    fuse_clothing_ocr_tokens,
    partition_implicit_local_parts,
    apply_ocr_aware_background_suppression,
)


def test_paper4_illumination_clahe_normalization():
    # Synthetic dark/underexposed image with red tint
    dark_red = np.zeros((100, 100, 3), dtype=np.uint8)
    dark_red[:, :] = [10, 10, 80]  # Dim red in BGR
    
    equalized = normalize_illumination_clahe(dark_red)
    assert equalized is not None
    assert equalized.shape == (100, 100, 3)
    # Luminance channel should have been enhanced by CLAHE
    assert np.mean(equalized) >= np.mean(dark_red)


def test_paper4_extract_dominant_colors_with_illumination_norm():
    # Synthetic blue clothing image
    blue_crop = np.zeros((120, 80, 3), dtype=np.uint8)
    blue_crop[:, :] = [180, 30, 20]  # Blue in BGR
    
    colors = extract_dominant_clothing_colors(blue_crop, apply_illumination_norm=True)
    assert "blue" in colors


def test_paper4_occlusion_aware_dynamic_part_scaling():
    # 1. Close-up selfie/portrait (Aspect ratio ~ 0.9, lower body occluded)
    selfie_crop = Image.new("RGB", (100, 90), color=(200, 150, 150))
    occ_selfie = detect_occlusion_and_scale_parts(selfie_crop, ptype="upper_body")
    assert occ_selfie["is_occluded"] is True
    assert occ_selfie["weights"]["head"] > occ_selfie["weights"]["torso"]
    assert occ_selfie["weights"]["head"] >= 0.40

    # 2. Standing pedestrian (Aspect ratio ~ 2.2, full body visible)
    full_pedestrian = Image.new("RGB", (100, 220), color=(150, 150, 150))
    occ_full = detect_occlusion_and_scale_parts(full_pedestrian, ptype="full_person")
    assert occ_full["is_occluded"] is False
    assert occ_full["weights"]["head"] == 0.30
    assert occ_full["weights"]["torso"] == 0.35


def test_paper4_text_on_clothing_ocr_fusion():
    person_bbox = {"x": 100, "y": 100, "width": 200, "height": 400}
    
    # 3 OCR boxes:
    # Box 1: "Google" printed on T-shirt (center at x=200, y=250) -> INSIDE person box
    # Box 2: "Runner 402" bib on chest (center at x=190, y=220) -> INSIDE person box
    # Box 3: "Coffee Shop" sign in background (center at x=600, y=50) -> OUTSIDE person box
    ocr_boxes = [
        {
            "text": "Google Developer",
            "box": [[150, 240], [250, 240], [250, 260], [150, 260]],
            "confidence": 0.95,
        },
        {
            "text": "Runner 402",
            "box": [[160, 210], [220, 210], [220, 230], [160, 230]],
            "confidence": 0.98,
        },
        {
            "text": "Coffee Shop Billboard",
            "box": [[550, 40], [650, 40], [650, 60], [550, 60]],
            "confidence": 0.92,
        },
    ]
    ocr_boxes_json = json.dumps(ocr_boxes)

    # Query 1: "person in google hoodie"
    bonus_1, matches_1 = fuse_clothing_ocr_tokens(person_bbox, ocr_boxes_json, "person in google hoodie")
    assert bonus_1 > 0.0
    assert "google" in matches_1

    # Query 2: "athlete with 402 bib"
    bonus_2, matches_2 = fuse_clothing_ocr_tokens(person_bbox, ocr_boxes_json, "athlete with 402 bib")
    assert bonus_2 > 0.0
    assert "402" in matches_2

    # Query 3: "coffee shop sign" -> Billboard is OUTSIDE person box, should NOT match person clothing
    bonus_3, matches_3 = fuse_clothing_ocr_tokens(person_bbox, ocr_boxes_json, "coffee shop billboard")
    assert bonus_3 == 0.0
    assert len(matches_3) == 0


def test_paper4_ocr_aware_background_suppression():
    # 100x100 white crop
    crop = np.ones((100, 100, 3), dtype=np.uint8) * 200
    crop_bbox = {"x": 50, "y": 50, "width": 100, "height": 100}

    # Case A: No OCR text -> Background corners are dimmed
    suppressed_a, ratio_a = apply_ocr_aware_background_suppression(crop, crop_bbox, ocr_boxes_json=None)
    assert ratio_a > 0.0
    # Corner pixel (x=5, y=5) is non-pedestrian background and should be attenuated
    assert suppressed_a[5, 5, 0] < crop[5, 5, 0]

    # Case B: Shop sign OCR box in the top-left corner (x=55 to 75, y=55 to 75 in image coords -> x=5..25, y=5..25 in crop)
    ocr_boxes = [
        {
            "text": "Starbucks Coffee",
            "box": [[55, 55], [75, 55], [75, 75], [55, 75]],
            "confidence": 0.96,
        }
    ]
    ocr_json = json.dumps(ocr_boxes)
    suppressed_b, ratio_b = apply_ocr_aware_background_suppression(crop, crop_bbox, ocr_boxes_json=ocr_json)

    # In Case B, the shop sign at (10, 10) must be PROTECTED (A_text = 1.0) and preserved brighter than without protection!
    assert suppressed_b[10, 10, 0] > suppressed_a[10, 10, 0]

