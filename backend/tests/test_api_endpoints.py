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


from app import auth


def test_search_exact_keyword(client: TestClient):
    """POST /search with known keyword should return matching documents with score."""
    token = auth.create_access_token({"sub": "samrudhi deshmukh", "user_id": 24, "is_admin": False})
    resp = client.post("/search", headers={"Authorization": f"Bearer {token}"}, json={"query": "Avneet"})
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert data["count"] >= 1
    top = data["results"][0]
    assert "AVNEET" in top["matched_text"].upper()


def test_sync_check_endpoint(client: TestClient):
    """POST /images/sync-check must differentiate existing vs missing files."""
    token = auth.create_access_token({"sub": "samrudhi deshmukh", "user_id": 24, "is_admin": False})
    payload = {
        "files": [
            {"filename": "1000182254.jpg", "size": 1024},
            {"filename": "brand_new_unseen_photo_9999.jpg", "size": 2048},
        ]
    }
    resp = client.post("/images/sync-check", headers={"Authorization": f"Bearer {token}"}, json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_checked"] == 2
    assert "brand_new_unseen_photo_9999.jpg" in data["missing"]
    assert "1000182254.jpg" in data["already_synced"]

