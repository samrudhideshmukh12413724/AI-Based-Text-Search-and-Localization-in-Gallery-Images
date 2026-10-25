"""Unit Tests for Paper 9: Cross-Weighted Product Text Similarity & Comprehensive Search Ranking.

Reference:
  Zengtao Zhao, Hao Zhang, Yilong Yu
  "Method For Calculating Text Similarity Of Cross-Weighted Products Applied To Power Grid Model Search"
  Preprints of the 4th IEEE Conference on Energy Internet and Energy System Integration (EI2 2020), Wuhan, China.
"""

import pytest
import math
from app.search.research_algorithms import (
    compute_cross_weighted_similarity,
    calculate_power_grid_comprehensive_score,
    compute_cross_weighted_product_score,
)


def test_exact_identity_and_disjoint_boundaries():
    """Verify Paper 9 boundary conditions: identical -> 1.0, disjoint -> 0.0, empty -> 0.0."""
    assert compute_cross_weighted_similarity("ABC", "ABC") == 1.0
    assert compute_cross_weighted_similarity("110kV switch", "110kV switch") == 1.0
    assert compute_cross_weighted_similarity("ABC", "DEF") == 0.0
    assert compute_cross_weighted_similarity("ABC", "XYZ") == 0.0
    assert compute_cross_weighted_similarity("", "ABC") == 0.0
    assert compute_cross_weighted_similarity("ABC", "") == 0.0


def test_paper9_table1_empirical_benchmarks():
    """Verify Table I and Section III-E mathematical benchmarks from Paper 9."""
    # Section III-E Example: "ABCD" vs "ABECF" -> 0.2216
    sim_example = compute_cross_weighted_similarity("ABCD", "ABECF")
    assert pytest.approx(sim_example, abs=0.005) == 0.2216

    # Table I: "ABC" vs "ABCD" -> 0.692
    sim_abcd = compute_cross_weighted_similarity("ABC", "ABCD")
    assert pytest.approx(sim_abcd, abs=0.005) == 0.692

    # Table I: "ABC" vs "ABCDE" -> 0.525
    sim_abcde = compute_cross_weighted_similarity("ABC", "ABCDE")
    assert pytest.approx(sim_abcde, abs=0.005) == 0.525

    # Table I: "ABC" vs "ABDC" -> 0.469
    sim_abdc = compute_cross_weighted_similarity("ABC", "ABDC")
    assert pytest.approx(sim_abdc, abs=0.005) == 0.469


def test_right_side_emphasis_power_grid_logic():
    """
    Paper 9 Sec III-A & III-D: Technical phrases and asset codes put critical type discriminators
    at the end (e.g. 'XXX switch' vs 'XXX transformer').
    Right-side matching must rank higher than left-side matching.
    """
    query = "ABC switch"
    target_match_type = "ABCD switch"
    target_different_type = "ABC switch cabinet"

    sim_match_type = compute_cross_weighted_similarity(query, target_match_type)
    sim_diff_type = compute_cross_weighted_similarity(query, target_different_type)

    assert sim_match_type > sim_diff_type, (
        f"Right-side type match ({sim_match_type}) must rank higher than changed type ({sim_diff_type})"
    )


def test_continuous_vs_fragmented_match_reward():
    """
    Paper 9 Eq. 8: Continuous matching range [d, u] rewards uninterrupted character segments
    over scrambled or fragmented occurrences.
    """
    sim_continuous = compute_cross_weighted_similarity("ABC", "ABCD")
    sim_fragmented = compute_cross_weighted_similarity("ABC", "ABDC")

    assert sim_continuous > sim_fragmented
    # Continuous match should have significant margin over fragmented match
    margin = sim_continuous - sim_fragmented
    assert margin >= 0.20, f"Expected margin >= 0.20, got {margin}"


def test_sigmoid_filter_score_calculation():
    """
    Paper 9 Eq. 2: S_f = 1 / (1 + exp(-W_s))
    Validates non-linear saturation for multi-attribute matching (voltage, asset type, location).
    """
    # Ws = 0: neutral baseline
    res_zero = calculate_power_grid_comprehensive_score(text_similarity=0.8, filter_weights_sum=0.0)
    assert res_zero["filter_score"] == 0.50

    # Ws = 1 (e.g. voltage level matched)
    res_one = calculate_power_grid_comprehensive_score(text_similarity=0.8, filter_weights_sum=1.0)
    expected_one = round(1.0 / (1.0 + math.exp(-1.0)), 4)
    assert pytest.approx(res_one["filter_score"], abs=0.001) == expected_one

    # Ws = 5 (voltage=1, asset_type=2, functional_location=2)
    res_five = calculate_power_grid_comprehensive_score(text_similarity=0.8, filter_weights_sum=5.0)
    expected_five = round(1.0 / (1.0 + math.exp(-5.0)), 4)
    assert pytest.approx(res_five["filter_score"], abs=0.001) == expected_five
    assert res_five["filter_score"] > 0.99


def test_comprehensive_ranking_tri_part_formula():
    """
    Paper 9 Eq. 1: S = S_f * 0.5 + S_s * 0.3 + S_h * 0.2
    Comprehensive multi-field ranking integrating filter, cross-weighted similarity, and heat.
    """
    # Test case: Sf ~ 0.9933 (Ws=5), Ss = 0.6923 ("ABC" vs "ABCD"), Sh = 0.80 (popular asset)
    result = calculate_power_grid_comprehensive_score(
        text_similarity=0.6923,
        filter_weights_sum=5.0,
        heat_score=0.80,
    )

    expected_s = (0.9933 * 0.5) + (0.6923 * 0.3) + (0.80 * 0.2)
    assert pytest.approx(result["comprehensive_score"], abs=0.002) == round(expected_s, 4)
    assert result["weights"] == {"filter": 0.5, "text": 0.3, "heat": 0.2}

    # Verify backwards compatible scorer still functions
    legacy_score = compute_cross_weighted_product_score(
        text_similarity=0.6923,
        filter_score=0.9933,
        attention_confidence=0.80,
    )
    assert legacy_score > 0.0
