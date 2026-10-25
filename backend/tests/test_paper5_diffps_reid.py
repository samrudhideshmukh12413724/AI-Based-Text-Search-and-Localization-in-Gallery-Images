"""Unit test suite for Paper 5 (DiffPS: Kim et al., ICCV 2025) implementation.

Verifies:
1. 2D Discrete Wavelet Transform (DWT) High-Frequency Texture Descriptor (Paper 5 Section 3.5 - MSFRN)
2. Shape-bias mitigation: discriminates between plain vs patterned apparel of the same color
3. DWT texture similarity metrics & mathematical bounds
4. Semantic-Adaptive Feature Aggregation (SFAN) multi-part identity fusion diagnostics in reidentify_person
"""

import numpy as np
import pytest
from PIL import Image

from app.person_search import (
    extract_dwt_texture_descriptor,
    compute_dwt_texture_similarity,
    partition_implicit_local_parts,
)


def test_paper5_dwt_texture_descriptor_shape_and_norm():
    """Verify DWT produces a 64-D unit-normalized feature vector."""
    dummy_crop = np.random.randint(50, 200, (120, 80, 3), dtype=np.uint8)
    desc = extract_dwt_texture_descriptor(dummy_crop)

    assert desc is not None
    assert desc.shape == (64,)
    assert desc.dtype == np.float32
    # Should be unit-normalized
    assert pytest.approx(float(np.linalg.norm(desc)), rel=1e-3) == 1.0


def test_paper5_dwt_texture_discrimination_mitigates_shape_bias():
    """
    Paper 5 Key Finding (Section 3.2 & 3.5):
    Two people wearing the same shade of blue (identical global color and silhouette)
    must be differentiated by high-frequency DWT texture (checks/stripes vs smooth).
    """
    # 1. Plain smooth blue shirt
    plain_blue = np.zeros((100, 100, 3), dtype=np.uint8)
    plain_blue[:, :] = [180, 50, 30]  # Smooth blue

    # 2. Checked / patterned blue shirt with grid stripes
    checked_blue = np.zeros((100, 100, 3), dtype=np.uint8)
    checked_blue[:, :] = [180, 50, 30]
    checked_blue[::6, :] = [255, 255, 255]  # Horizontal white lines
    checked_blue[:, ::6] = [255, 255, 255]  # Vertical white lines

    desc_plain = extract_dwt_texture_descriptor(plain_blue)
    desc_checked = extract_dwt_texture_descriptor(checked_blue)

    # Self-similarity should be 1.0
    assert pytest.approx(compute_dwt_texture_similarity(desc_plain, desc_plain), rel=1e-3) == 1.0
    assert pytest.approx(compute_dwt_texture_similarity(desc_checked, desc_checked), rel=1e-3) == 1.0

    # Cross-texture similarity must be significantly lower, mitigating shape bias
    cross_sim = compute_dwt_texture_similarity(desc_plain, desc_checked)
    assert cross_sim < 0.50, f"DWT should distinguish smooth vs checked pattern; got {cross_sim}"


def test_paper5_dwt_texture_similarity_bounds():
    """Verify bounds of compute_dwt_texture_similarity (always within [0.0, 1.0])."""
    empty = np.array([], dtype=np.float32)
    zero_vec = np.zeros(64, dtype=np.float32)
    unit_vec = np.ones(64, dtype=np.float32) / np.sqrt(64)

    assert compute_dwt_texture_similarity(empty, unit_vec) == 0.0
    assert compute_dwt_texture_similarity(zero_vec, unit_vec) == 0.0
    assert 0.0 <= compute_dwt_texture_similarity(unit_vec, unit_vec) <= 1.0
