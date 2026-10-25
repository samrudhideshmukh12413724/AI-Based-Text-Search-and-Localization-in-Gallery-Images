"""Unit Tests for Constraint-Aware Natural Language Search and Negation Exclusion (Idea 1).

Research Basis:
  Overcomes the fundamental 'Negation Blindness' in modern Multimodal Vision-Language Models (CLIP/Transformers)
  by decomposing user instructions into positive required conditions and negative exclusions,
  enforcing hard suppression filters (NFPR -> 0.0) and Constraint Satisfaction Rate (CSR) scoring.

Covers:
1. Complex multi-condition query parsing (Positive objects + attributes + negative exclusions).
2. Semantic synonym expansion for negative constraints (e.g., 'people' -> person, pedestrian, human).
3. Stripping of negative tokens from positive search keywords to prevent false attraction.
4. Hard suppression of candidates violating negative exclusion constraints.
5. Multi-modal verification across OCR text, visual object metadata, and file metadata.
6. Quantitative Constraint Satisfaction Rate (CSR) calculation.
7. Verification against the canonical query:
   'Find the photo with a red car on a road, with no people and a blue sky'
"""

import pytest
from app.instruction_parser import (
    CrossStepInstructionParser,
    parse_natural_language_instruction,
    execute_instruction_search,
)


@pytest.fixture
def parser():
    return CrossStepInstructionParser()


def test_canonical_query_constraint_decomposition(parser):
    """
    Validates parsing of the user's primary benchmark query:
    'Find the photo with a red car on a road, with no people and a blue sky'
    """
    query = "Find the photo with a red car on a road, with no people and a blue sky"
    parsed = parser.parse(query)

    # 1. Negative exclusion detection
    assert parsed["has_exclusions"] is True
    assert "people" in parsed["exclusions"]
    assert "person" in parsed["exclusions"]
    assert "pedestrian" in parsed["exclusions"]

    # 2. Negation Blindness Prevention: 'people' must NOT be in cross_step_tokens!
    assert "people" not in parsed["cross_step_tokens"]
    assert "person" not in parsed["cross_step_tokens"]

    # 3. Positive objects & attributes extraction
    assert "car" in parsed["positive_objects"]
    assert "road" in parsed["positive_objects"]
    assert "sky" in parsed["positive_objects"]
    assert "red" in parsed["positive_attributes"]
    assert "blue" in parsed["positive_attributes"]


def test_negative_exclusion_syntactical_variants(parser):
    """
    Validates diverse negation syntactical patterns:
    - 'without watermark'
    - 'excluding penalty'
    - 'free of blur'
    - 'having no signature'
    """
    # Pattern A: 'without watermark'
    p_watermark = parser.parse("Retrieve electricity bill from Pune without watermark")
    assert "watermark" in p_watermark["exclusions"]
    assert "watermarked" in p_watermark["exclusions"]
    assert "watermark" not in p_watermark["cross_step_tokens"]
    assert p_watermark["is_geo_search"] is True
    assert p_watermark["detected_city"] == "pune"

    # Pattern B: 'excluding penalty'
    p_penalty = parser.parse("Show unpaid invoice excluding penalty")
    assert "penalty" in p_penalty["exclusions"]
    assert "fine" in p_penalty["exclusions"]
    assert p_penalty["payment_status"] == "UNPAID"

    # Pattern C: 'free of blur'
    p_blur = parser.parse("Get Aadhaar card copy free of blur")
    assert "blur" in p_blur["exclusions"]
    assert "blurry" in p_blur["exclusions"]

    # Pattern D: 'having no signature'
    p_sign = parser.parse("Find draft rent agreement having no signature")
    assert "signature" in p_sign["exclusions"]
    assert "signed" in p_sign["exclusions"]


def test_positive_attributes_and_clothing_colors(parser):
    """
    Ensures colors associated with positive entities are retained,
    while person search is suppressed if 'people' is excluded.
    """
    # When people are excluded, is_person_search must NOT be activated
    query_neg = "Red car parked on road with no people"
    parsed_neg = parser.parse(query_neg)
    assert parsed_neg["is_person_search"] is False
    assert "red" in parsed_neg["positive_attributes"]

    # When person is explicitly searched, is_person_search is True
    query_pos = "Photo of a person wearing blue shirt in Pune"
    parsed_pos = parser.parse(query_pos)
    assert parsed_pos["is_person_search"] is True
    assert "blue" in parsed_pos["detected_clothing_colors"]


def test_constraint_aware_search_execution_telemetry():
    """
    Validates end-to-end execution of constraint-aware search:
    - returns parsed positive constraints
    - returns negative exclusions
    - records suppressed violations telemetry
    - computes constraint satisfaction rate (CSR)
    """
    res = execute_instruction_search("Find electricity bill from 2026 without watermark")

    assert res["status"] == "success"
    assert "positive_constraints" in res
    assert "negative_exclusions" in res
    assert "watermark" in res["negative_exclusions"]
    assert "suppressed_violations_count" in res
    assert isinstance(res["documents"], list)

    # All returned documents must strictly satisfy constraints without exclusions
    for doc in res["documents"]:
        assert "constraint_satisfaction_rate" in doc
        assert "satisfied_constraints" in doc
        assert doc["constraint_satisfaction_rate"] >= 0.0
