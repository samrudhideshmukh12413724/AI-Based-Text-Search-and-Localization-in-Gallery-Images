"""Unit Tests for Research Paper Innovations Enrolled into DocuLens AI.

Verifies:
1. Paper 12 Boyer-Moore-Horspool algorithm shift tables and matching
2. Paper 13 Bounded Dice similarity & short-text matching
3. Paper 1 BPE Subword tokenization and inclusive-OR support
4. Paper 9 Cross-weighted product relevance formulation
5. Paper 8 & 10 Extractive Grounded QA Engine
6. Paper 11 Unsupervised Semantic Document Clustering
"""

import pytest
from app.search.research_algorithms import (
    BoyerMooreHorspoolMatcher,
    compute_dice_similarity,
    bounded_dice_search,
    bpe_subword_tokenize,
    bpe_inclusive_or_score,
    compute_cross_weighted_product_score,
)
from app.qa_engine import extractive_sentence_ranker, extract_specific_value
from app.clustering import extract_keywords_tfidf


def test_bmh_matcher_paper12():
    # Test Boyer-Moore-Horspool exact search and shift jump
    matcher = BoyerMooreHorspoolMatcher("invoice")
    assert matcher.m == 7
    assert "i" in matcher.shift_table
    assert matcher.shift_table["c"] == 1  # 7 - 1 - 5 = 1

    text = "Please find attached the official invoice for tuition fees."
    occurrences = matcher.search_in(text)
    assert len(occurrences) == 1
    assert occurrences[0] == text.lower().find("invoice")
    assert matcher.match_score(text) == 1.0

    # Negative match
    assert matcher.search_in("No matching document here") == []
    assert matcher.match_score("No matching document here") == 0.0


def test_dice_similarity_paper13():
    # Identical strings have Dice 1.0
    assert compute_dice_similarity("aadhaar", "aadhaar") == 1.0

    # Common OCR typo: 'scholarshp' (missing letter) vs 'scholarship'
    sim = compute_dice_similarity("scholarshp", "scholarship")
    assert sim >= 0.80

    # Common OCR typo: 'certifcate' vs 'certificate'
    sim2 = compute_dice_similarity("certifcate", "certificate")
    assert sim2 >= 0.85

    # Dissimilar strings
    assert compute_dice_similarity("electricity", "passport") < 0.25

    # Bounded 3-band search
    score, matched = bounded_dice_search("certifcate", ["certificate", "invoice", "receipt"])
    assert score >= 0.70
    assert matched == "certificate"


def test_bpe_subword_paper1():
    # Word decomposition into subword chunks
    subwords = bpe_subword_tokenize("challan", min_subword_len=3)
    assert "challan" in subwords
    assert "cha" in subwords
    assert "llan" in subwords

    # Inclusive-OR score against fragmented OCR text
    doc_tokens = ["state", "bank", "challan", "paid", "amount"]
    score, matched = bpe_inclusive_or_score("challan", doc_tokens)
    assert score == 1.0
    assert len(matched) > 0


def test_cross_weighted_product_paper9():
    # High text match + high filter + high confidence attention
    score_high = compute_cross_weighted_product_score(
        text_similarity=1.0,
        filter_score=1.0,
        attention_confidence=0.95,
    )
    assert score_high > 0.90

    # Low text match heavily drops score due to product multiplication
    score_low = compute_cross_weighted_product_score(
        text_similarity=0.10,
        filter_score=1.0,
        attention_confidence=0.95,
    )
    assert score_low < score_high * 0.4


def test_qa_extractive_ranker_paper8():
    doc = "VIT Pune College of Engineering. Total tuition fee payable is Rs 45000. Last date of payment is 15-11-2026."
    ranked = extractive_sentence_ranker(doc, "What is the tuition fee amount?")
    assert len(ranked) > 0
    assert "45000" in ranked[0]["sentence"]


def test_qa_specific_value_expert_rule_paper10():
    doc = "Government of Maharashtra Electricity Bill. Grand Total Amount: Rs 1,480.00. Due Date: 28/11/2026."
    amount = extract_specific_value("total amount", doc)
    assert amount == "₹1,480.00"

    date = extract_specific_value("due date", doc)
    assert date == "28/11/2026"


def test_tfidf_keywords_paper11():
    texts = [
        "Electricity bill payment receipt total amount paid",
        "Utility bill invoice payment transaction successful",
        "Monthly bill payment confirmation electricity charge",
    ]
    kws = extract_keywords_tfidf(texts, top_n=3)
    assert len(kws) > 0
    assert any(k in ["bill", "payment", "electricity", "amount"] for k in kws)


def test_person_search_components_paper4_5():
    from app.person_search import extract_dominant_clothing_colors, partition_implicit_local_parts
    import numpy as np
    from PIL import Image

    # Synthetic red torso image
    red_torso = np.zeros((100, 100, 3), dtype=np.uint8)
    red_torso[:, :] = [0, 0, 220]  # Red in BGR
    colors = extract_dominant_clothing_colors(red_torso)
    assert "red" in colors

    # Implicit Local Alignment part partition (Paper 4)
    pil_dummy = Image.new("RGB", (100, 200), color=(120, 120, 120))
    parts = partition_implicit_local_parts(pil_dummy)
    assert "global" in parts
    assert "head" in parts
    assert "torso" in parts
    assert parts["head"].size[1] < parts["global"].size[1]


def test_document_summarizer_and_tone_paper7_8():
    from app.summarizer import generate_document_summary, analyze_document_tone

    doc_text = (
        "GOVERNMENT OF MAHARASHTRA STATE ELECTRICITY BOARD.\n"
        "Official notice for electricity bill payment for consumer ID 849201.\n"
        "Total payable amount is Rs 2,450.00.\n"
        "Due date is 15-11-2026. Failure to pay will attract disconnection notice."
    )
    summary = generate_document_summary(doc_text, max_bullets=3)
    assert len(summary["key_highlights"]) > 0
    assert "abstract" in summary
    assert summary["tone_analysis"]["primary_tone"] in ["Financial / Transactional", "Urgent / Action Required", "Official / Government"]


def test_geo_distance_and_search_paper14():
    from app.geo_search import haversine_distance_km, INDIAN_GEO_HUBS

    # Distance between Pune and Mumbai is ~120-150 km
    pune = INDIAN_GEO_HUBS["pune"]
    mumbai = INDIAN_GEO_HUBS["mumbai"]
    dist = haversine_distance_km(pune[0], pune[1], mumbai[0], mumbai[1])
    assert 110.0 <= dist <= 160.0

    # Distance from Pune to itself is 0
    assert haversine_distance_km(pune[0], pune[1], pune[0], pune[1]) == 0.0


def test_instruction_parser_paper11():
    from app.instruction_parser import parse_natural_language_instruction

    cmd = "Find all electricity bills from 2026 with total above 1000 rupees"
    res = parse_natural_language_instruction(cmd)
    assert res["category"] == "Bills & Invoices"
    assert res["year"] == "2026"
    assert res["min_amount"] == 1000.0
    assert "electricity" in res["search_keywords"]

    cmd_person = "Show me person wearing red shirt with glasses"
    res_person = parse_natural_language_instruction(cmd_person)
    assert res_person["is_person_search"] is True

    cmd_geo = "Find documents from Pune"
    res_geo = parse_natural_language_instruction(cmd_geo)
    assert res_geo["is_geo_search"] is True
    assert res_geo["detected_city"] == "pune"


def test_ieee_icisaa_educational_semantic_search():
    from app.educational_semantic_search import (
        TFIDFEducationalSummarizer,
        SemanticEducationalSearchEngine,
        run_educational_semantic_study,
    )

    sample_educational_text = (
        "Natural Language Processing (NLP) is a crucial subfield of artificial intelligence. "
        "It focuses on the interactions between human language and computational algorithms. "
        "In educational texts, text summarization helps students comprehend complex subjects and saves learning time. "
        "The model utilizes Term Frequency-Inverse Document Frequency (TF-IDF) and transformer embeddings. "
        "The primary objective is to obtain the top 5 answers to any question and provide a detailed summary of the results."
    )

    # 1. Test Model 1: TF-IDF Sentence Scorer (Figures 3, 4, 10 in ICISAA paper)
    tfidf = TFIDFEducationalSummarizer()
    scored = tfidf.compute_sentence_scores(sample_educational_text)
    assert len(scored) >= 3
    assert scored[0]["score"] > 0
    assert "top_words" in scored[0]

    tfidf_summary = tfidf.generate_tfidf_summary(sample_educational_text, top_n=2)
    assert "summary" in tfidf_summary
    assert len(tfidf_summary["summary"]) > 0

    # 2. Test Model 2: Semantic Top-5 Answers & Summary of Summary (Figures 11 & 12)
    semantic_engine = SemanticEducationalSearchEngine()
    qa_res = semantic_engine.extract_top_5_answers(
        sample_educational_text,
        question="What is the role of text summarization in educational texts?"
    )
    assert "top_5_answers" in qa_res
    assert "concatenated_summary" in qa_res
    assert "detailed_summary" in qa_res
    assert len(qa_res["top_5_answers"]) > 0

    # 3. Test Full Comparative Study (Section IV & V)
    study = run_educational_semantic_study(
        sample_educational_text,
        question="How does NLP assist students?"
    )
    assert "model_1_tfidf" in study
    assert "model_2_semantic" in study
    assert "paper_conclusion" in study
    assert "Symbiosis" in study["paper_conclusion"]["authors"]

