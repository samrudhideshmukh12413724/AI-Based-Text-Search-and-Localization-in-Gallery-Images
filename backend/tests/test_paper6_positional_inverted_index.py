"""Unit tests for Paper 6 Positional Inverted Index & Proximity Engine.

Directly tests the research implementation resolving:
Paper 6: One Approach for Full-Text Search of Files in MongoDB-Based Systems (Kelec et al., INFOTEH-JAHORINA 2019)
Fulfills authors' stated Future Scope:
- Eliminates MongoDB GridFS file/text content duplication.
- Inverted index with word positional tracking.
- Proximity search within bounded word windows.
- Storage efficiency statistics.
"""

import pytest
from app.search.positional_inverted_index import (
    PositionalInvertedIndex,
    get_positional_inverted_index,
)


@pytest.fixture
def index():
    """Provides a fresh PositionalInvertedIndex instance for each test."""
    return PositionalInvertedIndex()


def test_positional_index_tokenization_and_building(index):
    """Test unicode tokenization, positional offsets, and bulk build."""
    docs = [
        {"id": 1, "cleaned_text": "Invoice from Reliance Digital Store Mumbai", "image_name": "inv_1.jpg"},
        {"id": 2, "cleaned_text": "Electricity Bill Reliance Energy Ltd", "image_name": "bill_2.jpg"},
        {"id": 3, "cleaned_text": "Store receipt from Apollo Pharmacy Store", "image_name": "rec_3.jpg"},
    ]
    total = index.build_from_images(docs)
    assert total == 3
    assert index.total_docs == 3

    # Check that positions are strictly tracked
    assert 1 in index.index["reliance"]
    assert index.index["reliance"][1] == [2]  # "reliance" is token index 2 in doc 1

    # In doc 3, "store" appears at index 0 and index 5
    assert 3 in index.index["store"]
    assert index.index["store"][3] == [0, 5]


def test_exact_phrase_search(index):
    """Test exact multi-word phrase matching requiring pos(w_i+1) == pos(w_i) + 1."""
    docs = [
        {"id": 1, "cleaned_text": "State Bank of India Account Statement", "image_name": "sbi.jpg"},
        {"id": 2, "cleaned_text": "Reserve Bank of India Monetary Policy", "image_name": "rbi.jpg"},
        {"id": 3, "cleaned_text": "Account holder visited the Bank to open State branch", "image_name": "branch.jpg"},
    ]
    index.build_from_images(docs)

    # Search for "State Bank"
    results = index.phrase_search("State Bank")
    assert len(results) == 1
    assert results[0]["id"] == 1
    assert results[0]["start_positions"] == [0]

    # Doc 3 contains both "State" and "Bank" but NOT adjacent in that order
    doc3_matches = [r for r in results if r["id"] == 3]
    assert len(doc3_matches) == 0

    # Search for 3-word phrase "Bank of India"
    results_boi = index.phrase_search("Bank of India")
    matched_ids = {r["id"] for r in results_boi}
    assert matched_ids == {1, 2}
    assert results_boi[0]["phrase_count"] == 1


def test_phrase_search_single_word(index):
    """Test single word phrase search with TF-IDF weighting."""
    docs = [
        {"id": 10, "cleaned_text": "Tax invoice with GST tax details", "image_name": "tax.jpg"},
        {"id": 11, "cleaned_text": "Electricity payment receipt", "image_name": "elec.jpg"},
    ]
    index.build_from_images(docs)

    results = index.phrase_search("tax")
    assert len(results) == 1
    assert results[0]["id"] == 10
    assert results[0]["occurrences"] == 2


def test_proximity_search_bounded_distance(index):
    """Test distance-bounded proximity search (|pos1 - pos2| <= max_distance)."""
    index.add_document(1, "Total invoice amount is 5000 rupees", "doc1.jpg")
    index.add_document(2, "The total calculated billing summary for customer electric charge amount is high", "doc2.jpg")
    index.add_document(3, "Total without the target term", "doc3.jpg")

    # In doc 1: "total" is at pos 0, "amount" is at pos 2 -> distance is 2
    # In doc 2: "total" is at pos 1, "amount" is at pos 9 -> distance is 8

    # Proximity query within distance 3: only doc 1 matches
    res_prox3 = index.proximity_search("total", "amount", max_distance=3)
    assert len(res_prox3) == 1
    assert res_prox3[0]["id"] == 1
    assert res_prox3[0]["min_distance"] == 2

    # Proximity query within distance 10: both doc 1 and doc 2 match
    res_prox10 = index.proximity_search("total", "amount", max_distance=10)
    assert len(res_prox10) == 2
    # Doc 1 must be ranked higher because smaller distance yields higher proximity score
    assert res_prox10[0]["id"] == 1
    assert res_prox10[1]["id"] == 2
    assert res_prox10[0]["score"] > res_prox10[1]["score"]


def test_storage_efficiency_stats(index):
    """Test calculation of storage savings compared to Paper 6 MongoDB duplicate architecture."""
    docs = [
        {"id": i, "cleaned_text": f"Scanned customer invoice document {i} with tax amount and serial number", "image_name": f"doc_{i}.jpg"}
        for i in range(1, 21)
    ]
    index.build_from_images(docs)

    stats = index.get_storage_efficiency_stats(sample_image_size_kb=350.0)
    assert stats["total_documents_indexed"] == 20
    assert stats["distinct_vocabulary_terms"] > 5
    assert stats["total_postings_count"] > 20
    assert stats["paper6_mongodb_waste_prevented_kb"] > 0
    assert "Zero-Duplication" in stats["storage_duplication_rate"]


def test_singleton_get_positional_inverted_index():
    """Test global singleton retrieval function."""
    idx1 = get_positional_inverted_index()
    idx2 = get_positional_inverted_index()
    assert idx1 is idx2
