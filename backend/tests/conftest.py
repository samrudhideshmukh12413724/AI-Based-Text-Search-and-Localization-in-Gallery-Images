"""Pytest fixtures and configuration for AI Image Search backend tests."""

import sys
from pathlib import Path
import pytest

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app import database


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Reusable TestClient fixture for FastAPI endpoints."""
    database.init_db()
    return TestClient(app)
