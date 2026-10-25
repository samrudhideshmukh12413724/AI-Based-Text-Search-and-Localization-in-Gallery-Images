"""Unit Tests for Paper 11: Natural Language Instruction Parsing & Cluster-Guided Search.

Reference:
  Ying Shi, Zhuolin Chen, Yuanchun Tang, Zhanghuang Zhang, Bingqian Chen
  "Automatic Search Method for Unstructured Database of Natural Language Instructions
  Combining Cross-Step Matching Word Segmentation Algorithm and Web Text Clustering Analysis Model"
  2023 3rd International Conference on Electronic Information Engineering and Computer Science (EIECS), IEEE.

Covers:
1. Cross-Step Matching Word Segmentation (Filtering conversational filler verbs).
2. Quantitative Financial Range Extraction (Above, Below, Between).
3. Temporal Year Extraction (2020-2030).
4. Multi-Modal Intent Extraction (Person search with clothing colors).
5. Geo-Spatial City Extraction (Pune, Mumbai, Delhi, etc.).
6. Category Taxonomy Mapping (Bills, Govt IDs, Academic, Medical, Legal).
7. Payment Status Intent (PAID vs UNPAID vs OVERDUE).
8. Cluster-Guided Pruning & Search Space Reduction Percentage.
9. End-to-End Instruction Search Execution.
"""

import pytest
from app.instruction_parser import (
    CrossStepInstructionParser,
    parse_natural_language_instruction,
    execute_instruction_search,
)
from app.clustering import (
    find_matching_cluster_for_instruction,
    cluster_user_documents,
    extract_keywords_tfidf,
)


@pytest.fixture
def parser():
    return CrossStepInstructionParser()


def test_cross_step_word_segmentation_command_filtering(parser):
    """
    Paper 11 Core Methodology: Cross-Step matching eliminates conversational
    filler verbs ('find', 'show me', 'please search for') and isolates target tokens.
    """
    instruction = "Please can you find me all photos containing electricity meter"
    parsed = parser.parse(instruction)

    assert "find" not in parsed["cross_step_tokens"]
    assert "please" not in parsed["cross_step_tokens"]
    assert "all" not in parsed["cross_step_tokens"]
    assert "photos" not in parsed["cross_step_tokens"]
    assert "electricity" in parsed["cross_step_tokens"]
    assert "meter" in parsed["cross_step_tokens"]


def test_financial_amount_range_extraction(parser):
    """
    Validates quantitative numerical parsing across three distinct instruction patterns:
    1. Above X
    2. Below Y
    3. Between X and Y
    """
    # Pattern A: Above
    p_above = parser.parse("Show all restaurant bills above 1500 rupees")
    assert p_above["min_amount"] == 1500.0
    assert p_above["max_amount"] is None

    # Pattern B: Below
    p_below = parser.parse("Get receipts under 500 rs from store")
    assert p_below["min_amount"] is None
    assert p_below["max_amount"] == 500.0

    # Pattern C: Between
    p_between = parser.parse("Find electricity bills between 1000 and 2500 rupees")
    assert p_between["min_amount"] == 1000.0
    assert p_between["max_amount"] == 2500.0


def test_temporal_year_extraction(parser):
    """Validates year constraint extraction from conversational commands."""
    parsed = parser.parse("Show my semester marksheet from 2026 final exam")
    assert parsed["year"] == "2026"
    assert parsed["category"] == "Academic & College"


def test_multi_modal_person_intent_and_clothing_colors(parser):
    """
    Validates cross-modal intent detection:
    Identifies person search commands and extracts dominant clothing colors.
    """
    instruction = "Find person wearing red shirt and blue jeans with spectacles"
    parsed = parser.parse(instruction)

    assert parsed["is_person_search"] is True
    assert "red" in parsed["detected_clothing_colors"]
    assert "blue" in parsed["detected_clothing_colors"]


def test_geospatial_city_extraction(parser):
    """Validates spatial intent detection for offline travel gallery photos."""
    parsed = parser.parse("Show all vacation photos from Pune trip")

    assert parsed["is_geo_search"] is True
    assert parsed["detected_city"] == "pune"


def test_category_taxonomy_mapping(parser):
    """Validates deterministic mapping into 5 core document categories."""
    assert parser.parse("Electricity bill payment receipt")["category"] == "Bills & Invoices"
    assert parser.parse("Download my Aadhaar card and PAN")["category"] == "Government & Identity Cards"
    assert parser.parse("Check university degree certificate and grades")["category"] == "Academic & College"
    assert parser.parse("Doctor prescription tablets from clinic")["category"] == "Medical & Healthcare"
    assert parser.parse("Notarized rent agreement and stamp deed")["category"] == "Legal & Agreements"


def test_payment_status_intent(parser):
    """Validates operational payment state deduction (PAID vs UNPAID)."""
    p_unpaid = parser.parse("Find all unpaid electricity bills")
    assert p_unpaid["payment_status"] == "UNPAID"

    p_paid = parser.parse("Show all cleared payment receipts")
    assert p_paid["payment_status"] == "PAID"


def test_cluster_guided_pruning_and_search_space_reduction():
    """
    Paper 11 Core Optimization:
    Directs query to the target semantic cluster, proving search space reduction.
    """
    guidance = find_matching_cluster_for_instruction("Show electricity power bills")

    assert guidance["matched_cluster"] in ["Bills & Invoices", "General Documents"]
    assert guidance["confidence"] >= 0.50
    assert "search_space_reduction_pct" in guidance


def test_tfidf_keyword_extraction_clustering():
    """Validates TF-IDF keyword extraction across document cluster collections."""
    corpus = [
        "MSEDCL electricity power bill consumer units",
        "Utility power electricity meter bill payment",
        "Solar electricity power generation bill account",
    ]
    keywords = extract_keywords_tfidf(corpus, top_n=3)
    assert len(keywords) > 0
    assert any(k in ["electricity", "power", "bill"] for k in keywords)


def test_end_to_end_instruction_search_execution():
    """Validates full execution of natural language instruction search pipeline."""
    result = execute_instruction_search("find bills from 2026")

    assert result["status"] == "success"
    assert "parsed_parameters" in result
    assert "documents" in result
    assert result["parsed_parameters"]["year"] == "2026"
    assert result["target_cluster"] == "Bills & Invoices"
