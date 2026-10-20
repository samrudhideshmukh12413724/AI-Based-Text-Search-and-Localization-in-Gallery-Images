"""Multi-Tenant Isolation and Role-Based Access Control (RBAC) Test Suite.

Validates:
1. User registration & JWT authentication.
2. Row-Level Security: User B cannot view User A's indexed documents.
3. Search scoping: Non-admin tenant searches are strictly filtered to the user's vault.
4. Anti-IDOR protections: Cross-tenant relationship and PDF export attempts are blocked (HTTP 403).
"""

import uuid
import pytest
from fastapi.testclient import TestClient


def test_user_registration_and_login(client: TestClient):
    suffix = uuid.uuid4().hex[:6]
    username = f"tenant_user_{suffix}"
    password = "SecurePassword123!"

    # 1. Register new user
    reg_resp = client.post(
        "/auth/register",
        json={"username": username, "password": password, "is_admin": False},
    )
    assert reg_resp.status_code == 200, reg_resp.text
    reg_data = reg_resp.json()
    assert reg_data["username"] == username
    user_id = reg_data["user_id"]
    assert user_id > 0

    # 2. Login
    login_resp = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert login_resp.status_code == 200, login_resp.text
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["username"] == username
    assert login_data["user_id"] == user_id
    assert login_data["is_admin"] is False
    token = login_data["access_token"]

    # 3. Verify /auth/me
    me_resp = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["id"] == user_id
    assert me_data["username"] == username
    assert me_data["is_admin"] is False


def test_tenant_vault_isolation_and_search_scoping(client: TestClient):
    suffix = uuid.uuid4().hex[:6]
    username_b = f"isolated_bob_{suffix}"
    password = "BobPassword123!"

    # Register Bob (Standard Tenant, Non-Admin)
    client.post(
        "/auth/register",
        json={"username": username_b, "password": password, "is_admin": False},
    )
    login_resp = client.post(
        "/auth/login",
        json={"username": username_b, "password": password},
    )
    token_b = login_resp.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. Bob lists images: should see 0 images since Bob hasn't uploaded anything
    img_resp = client.get("/images", headers=headers_b)
    assert img_resp.status_code == 200
    bob_docs = img_resp.json()
    assert len(bob_docs) == 0, f"Expected 0 documents for empty tenant Bob, got {len(bob_docs)}"

    # 2. Bob searches for existing User 1 / Alice keyword: should return 0 results
    search_resp = client.post(
        "/search",
        headers=headers_b,
        json={"query": "Avneet"},
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["count"] == 0, "Bob should not see User 1's documents in search results"

    # 3. IDOR Prevention: Bob attempts to view relationships of User 1's image (#1)
    rel_resp = client.get("/images/1/relationships", headers=headers_b)
    assert rel_resp.status_code == 403, "Bob must receive 403 Forbidden for User 1's image"
    assert "Tenant access denied" in rel_resp.json()["detail"]

    # 4. IDOR Prevention: Bob attempts to export PDF of User 1's image (#1)
    pdf_resp = client.get("/images/1/export-pdf", headers=headers_b)
    assert pdf_resp.status_code == 403, "Bob must receive 403 Forbidden for User 1's PDF export"
    assert "Tenant access denied" in pdf_resp.json()["detail"]

    # 5. Non-admin Bob attempts to access /admin/stats: must receive 403 Forbidden
    admin_resp = client.get("/admin/stats", headers=headers_b)
    assert admin_resp.status_code == 403, "Non-admin Bob must receive 403 Forbidden on /admin/stats"


def test_unauthenticated_security_and_privacy(client: TestClient):
    """Unauthenticated requests must NEVER receive admin privileges or access private cross-tenant data."""
    # 1. Unauthenticated request to /admin/stats MUST be rejected (403 Forbidden)
    admin_resp = client.get("/admin/stats")
    assert admin_resp.status_code == 403, "Unauthenticated request to /admin/stats must return 403 Forbidden"
    assert "Admin privileges required" in admin_resp.json()["detail"]

    # 2. Unauthenticated request to /auth/me returns is_admin: False
    me_resp = client.get("/auth/me")
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["is_admin"] is False, "Unauthenticated user must NOT have is_admin=True"

