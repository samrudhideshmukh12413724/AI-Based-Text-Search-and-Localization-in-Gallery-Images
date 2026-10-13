"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    """GET /health must return 200 with status ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"


def test_search_empty_query(client: TestClient):
    """POST /search with empty query should return 0 matches gracefully."""
    resp = client.post("/search", json={"query": "   "})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["results"] == []


def test_search_exact_keyword(client: TestClient):
    """POST /search with known keyword should return matching documents with score."""
    resp = client.post("/search", json={"query": "Avneet"})
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert data["count"] >= 1
    top = data["results"][0]
    assert top["similarity_score"] == 1.0
    assert "AVNEET" in top["matched_text"].upper()
