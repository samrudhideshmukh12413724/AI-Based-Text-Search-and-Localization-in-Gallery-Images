"""Unit tests for Exact Lexical Search & Inflection Engine."""

import pytest
from app.search.exact_search import tokenize, compute_exact_score, exact_search


def test_tokenize_filters_stopwords():
    """Verify stopword filtration and punctuation handling."""
    tokens = tokenize("The scholarship for the admission and student")
    assert "the" not in tokens
    assert "for" not in tokens
    assert "and" not in tokens
    assert "scholarship" in tokens
    assert "admission" in tokens
    assert "student" in tokens


def test_compute_exact_score_direct_match():
    """Direct whole-word match in document text yields 1.0."""
    score = compute_exact_score("Avneet", "AVNEET KAUR TITLE SPONSOR", "photo.jpg")
    assert score == 1.0


def test_compute_exact_score_compound_word():
    """Compound words like 'yash' in 'yashlawns' should score 1.0."""
    score = compute_exact_score("yash", "VENUE YASHLAWNS OCT 15", "ticket.jpg")
    assert score == 1.0

    score2 = compute_exact_score("lawns", "VENUE YASHLAWNS OCT 15", "ticket.jpg")
    assert score2 == 1.0


def test_compute_exact_score_inflections():
    """Inflections (e.g. payment -> paid, upi -> okaxis) should score 1.0."""
    score = compute_exact_score("payment", "Narhari paid rent via okaxis", "cred.jpg")
    assert score == 1.0


def test_compute_exact_score_no_match():
    """Completely irrelevant queries should score 0.0."""
    score = compute_exact_score("submarine", "University admission notice 2026", "notice.jpg")
    assert score == 0.0
