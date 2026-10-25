"""Unit tests for Paper 8: Educational Semantic Search & Grounded QA Engine.

Directly tests the research implementation resolving:
Paper 8: Semantic Search of Educational Texts
(Choudhary et al., IEEE ICISAA 2024, Symbiosis Institute of Technology, SIT Pune)

Covers:
1. TF-IDF Sentence Scoring & Extractive Summarization (Figures 3, 4, 10).
2. Dense Semantic Vector Search & Top-5 Candidate Answers (Figures 5, 6, 11).
3. Pixel-Grounded Visual Attribution Engine (Zero-Hallucination Verification).
4. Formula & Entity-Preserving Summary-of-Summary (Figures 9, 12).
5. Hybrid Dense-Lexical Scoring.
6. Full Comparative Study (Section IV & V).
"""

import pytest
from app.educational_semantic_search import (
    TFIDFEducationalSummarizer,
    SemanticEducationalSearchEngine,
    ground_answer_to_ocr_pixels,
    entity_preserving_summary_of_summary,
    run_educational_semantic_study,
)


@pytest.fixture
def educational_corpus():
    return (
        "Quantum physics describes the behavior of matter and light on atomic and subatomic scales. "
        "The energy of a photon is given by Planck relation E = hf where h is Planck constant. "
        "In the photoelectric experiment, Einstein discovered that light behaves as discrete packets called quanta. "
        "The cutoff frequency determines whether electrons are emitted from the metal surface. "
        "Students scored an average marks percentage of 84.5% with top cohort achieving CGPA 9.8 in final exam 2026-10-25."
    )


@pytest.fixture
def sample_ocr_boxes():
    return [
        {"text": "Quantum", "ymin": 50, "xmin": 40, "ymax": 70, "xmax": 120},
        {"text": "physics", "ymin": 50, "xmin": 125, "ymax": 70, "xmax": 190},
        {"text": "energy", "ymin": 80, "xmin": 10, "ymax": 100, "xmax": 35},
        {"text": "photon", "ymin": 80, "xmin": 40, "ymax": 100, "xmax": 85},
        {"text": "Planck", "ymin": 80, "xmin": 90, "ymax": 100, "xmax": 140},
        {"text": "relation", "ymin": 80, "xmin": 145, "ymax": 100, "xmax": 200},
        {"text": "E = hf", "ymin": 80, "xmin": 205, "ymax": 100, "xmax": 260},
        {"text": "Einstein", "ymin": 110, "xmin": 40, "ymax": 130, "xmax": 120},
        {"text": "quanta", "ymin": 110, "xmin": 200, "ymax": 130, "xmax": 260},
    ]


def test_tfidf_sentence_scoring(educational_corpus):
    """Tests Paper 8 Model 1: TF-IDF sentence tokenization, word scoring, and ranking."""
    tfidf = TFIDFEducationalSummarizer()
    scored = tfidf.compute_sentence_scores(educational_corpus)

    assert len(scored) >= 4
    for item in scored:
        assert item["score"] > 0
        assert "top_words" in item
        assert len(item["top_words"]) > 0

    summary = tfidf.generate_tfidf_summary(educational_corpus, top_n=2)
    assert summary["method"] == "TF-IDF Extractive Model"
    assert len(summary["summary"]) > 30
    assert summary["total_sentences_evaluated"] >= 4


def test_dense_semantic_top5_answers(educational_corpus):
    """Tests Paper 8 Model 2: Dense Semantic Vector search and Top-5 answers."""
    engine = SemanticEducationalSearchEngine()
    result = engine.extract_top_5_answers(
        text=educational_corpus,
        question="How did Einstein describe the behavior of light?",
    )

    assert result["question"] == "How did Einstein describe the behavior of light?"
    assert len(result["top_5_answers"]) > 0
    assert "concatenated_summary" in result
    assert "detailed_summary" in result
    assert result["confidence"] > 0.0

    # Best answer should be salient to Einstein or light
    best = result["best_answer"].lower()
    assert ("einstein" in best) or ("light" in best) or ("quanta" in best) or ("photon" in best)


def test_pixel_grounded_spatial_attribution(sample_ocr_boxes):
    """Tests Paper 8 Grounded Pixel Attribution preventing generative hallucination."""
    # 1. Factually grounded sentence present on page
    grounded_ans = "The energy of a photon is given by Planck relation E = hf."
    grounding = ground_answer_to_ocr_pixels(grounded_ans, sample_ocr_boxes)

    assert grounding["is_grounded_in_pixels"] is True
    assert grounding["attribution_grounding_score"] >= 0.35
    assert grounding["matched_boxes_count"] >= 3
    assert grounding["bounding_box_union"] is not None
    assert grounding["hallucination_risk"] == "Very Low (Physically Grounded in Pixels)"

    # 2. Hallucinated / external sentence not present in OCR boxes
    hallucinated_ans = "The capital of France is Paris and Eiffel Tower was built in 1889."
    ungrounded = ground_answer_to_ocr_pixels(hallucinated_ans, sample_ocr_boxes)

    assert ungrounded["is_grounded_in_pixels"] is False
    assert ungrounded["attribution_grounding_score"] == 0.0
    assert ungrounded["matched_boxes_count"] == 0
    assert "High" in ungrounded["hallucination_risk"]


def test_entity_and_formula_preserving_distillation():
    """Tests Paper 8 Formula & Entity-Preserving summary-of-summary."""
    answers = [
        {"answer": "Planck relation states energy is E = hf for a single photon."},
        {"answer": "Class scored 84.5% with top cohort achieving CGPA: 9.8."},
        {"answer": "The examination report was released on 2026-10-25."},
    ]

    distilled = entity_preserving_summary_of_summary(answers, "What are the test parameters and formulas?")
    assert "summary" in distilled
    assert "preserved_entities" in distilled
    entities = distilled["preserved_entities"]

    # Must preserve formulas and numerical entities
    entity_str = " ".join(entities)
    assert any("84.5%" in e for e in entities) or "84.5%" in distilled["summary"]
    assert any("CGPA" in e.upper() for e in entities) or "CGPA" in distilled["summary"]


def test_hybrid_dense_lexical_scoring(educational_corpus, sample_ocr_boxes):
    """Tests that answers include hybrid dense-lexical score."""
    engine = SemanticEducationalSearchEngine()
    res = engine.extract_top_5_answers(
        text=educational_corpus,
        question="What is the Planck relation formula?",
        ocr_boxes=sample_ocr_boxes,
    )

    top_ans = res["top_5_answers"][0]
    assert "hybrid_score" in top_ans
    assert "tfidf_component_score" in top_ans
    assert "pixel_grounding" in top_ans
    assert top_ans["pixel_grounding"]["is_grounded_in_pixels"] is True


def test_full_comparative_study_enrollment(educational_corpus, sample_ocr_boxes):
    """Tests full dual-model comparative experiment from ICISAA 2024."""
    study = run_educational_semantic_study(
        text=educational_corpus,
        question="Explain Planck relation and photon energy",
        ocr_boxes=sample_ocr_boxes,
    )

    assert "model_1_tfidf" in study
    assert "model_2_semantic" in study
    assert "paper_conclusion" in study
    assert "Symbiosis Institute of Technology, SIT Pune" in study["paper_conclusion"]["authors"]
    assert study["model_2_semantic"]["hallucination_prevention_audit"]["top_answer_grounded"] is True
