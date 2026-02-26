"""Tests for API Key management (P2.01 – SaaS API)."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))


# ─── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    """Use a temporary SQLite DB for each test."""
    import backend.api_keys as ak_module
    db_file = tmp_path / "api_keys_test.db"
    monkeypatch.setattr(ak_module, "DB_PATH", db_file)
    ak_module.init_db()
    yield


@pytest.fixture()
def admin_client(monkeypatch):
    """FastAPI TestClient with ADMIN_TOKEN configured."""
    monkeypatch.setenv("ADMIN_TOKEN", "test-admin-secret")
    # Need to reload the module-level variable
    import backend.app as app_module
    monkeypatch.setattr(app_module, "ADMIN_TOKEN", "test-admin-secret")
    from fastapi.testclient import TestClient
    return TestClient(app_module.app)


@pytest.fixture()
def client_no_admin():
    """FastAPI TestClient without ADMIN_TOKEN."""
    from backend.app import app
    from fastapi.testclient import TestClient
    return TestClient(app)


# ═══════════ Unit tests: api_keys module ═══════════

class TestApiKeysModule:

    def test_generate_key_returns_raw_key(self):
        from backend.api_keys import generate_api_key
        result = generate_api_key(owner="Dr. Dupont", email="dr@test.com", plan="starter")
        assert result["raw_key"].startswith("nlk_")
        assert len(result["raw_key"]) > 20
        assert result["owner"] == "Dr. Dupont"
        assert result["email"] == "dr@test.com"
        assert result["plan"] == "starter"
        assert result["id"] is not None

    def test_generate_key_unknown_plan_raises(self):
        from backend.api_keys import generate_api_key
        with pytest.raises(ValueError, match="Unknown plan"):
            generate_api_key(owner="test", plan="premium_ultra")

    def test_validate_key_success(self):
        from backend.api_keys import generate_api_key, validate_key
        result = generate_api_key(owner="test_user")
        info = validate_key(result["raw_key"])
        assert info is not None
        assert info["owner"] == "test_user"
        assert info["active"] == 1

    def test_validate_key_invalid(self):
        from backend.api_keys import validate_key
        assert validate_key("nlk_invalid_key_12345") is None

    def test_validate_key_revoked(self):
        from backend.api_keys import generate_api_key, validate_key, revoke_key
        result = generate_api_key(owner="test_user")
        revoke_key(result["id"])
        assert validate_key(result["raw_key"]) is None

    def test_check_quota_free_plan(self):
        from backend.api_keys import generate_api_key, check_quota
        result = generate_api_key(owner="free_user", plan="free")
        quota = check_quota(result["id"], "free")
        assert quota["allowed"] is True
        assert quota["limit"] == 5
        assert quota["remaining"] == 5

    def test_check_quota_unlimited(self):
        from backend.api_keys import generate_api_key, check_quota
        result = generate_api_key(owner="institution_user", plan="institution")
        quota = check_quota(result["id"], "institution")
        assert quota["allowed"] is True
        assert quota["limit"] == -1

    def test_record_and_check_usage(self):
        from backend.api_keys import generate_api_key, record_usage, check_quota, get_usage
        result = generate_api_key(owner="test_user", plan="free")
        key_id = result["id"]

        # Record 4 analyses
        for _ in range(4):
            record_usage(key_id, endpoint="/analyze", is_analysis=True)

        quota = check_quota(key_id, "free")
        assert quota["used"] == 4
        assert quota["allowed"] is True
        assert quota["remaining"] == 1

        # Record 1 more → quota full
        record_usage(key_id, endpoint="/analyze", is_analysis=True)
        quota = check_quota(key_id, "free")
        assert quota["used"] == 5
        assert quota["allowed"] is False
        assert quota["remaining"] == 0

    def test_record_non_analysis_request(self):
        from backend.api_keys import generate_api_key, record_usage, get_usage
        result = generate_api_key(owner="test_user", plan="free")
        key_id = result["id"]
        record_usage(key_id, endpoint="/chat", is_analysis=False)
        usage = get_usage(key_id)
        assert usage["requests_count"] == 1
        assert usage["analyses_count"] == 0

    def test_list_keys(self):
        from backend.api_keys import generate_api_key, list_keys
        generate_api_key(owner="user_a", plan="starter")
        generate_api_key(owner="user_b", plan="clinique")
        keys = list_keys()
        assert len(keys) == 2
        owners = {k["owner"] for k in keys}
        assert owners == {"user_a", "user_b"}

    def test_list_keys_excludes_inactive(self):
        from backend.api_keys import generate_api_key, list_keys, revoke_key
        k1 = generate_api_key(owner="active_user")
        k2 = generate_api_key(owner="revoked_user")
        revoke_key(k2["id"])
        keys = list_keys(include_inactive=False)
        assert len(keys) == 1
        assert keys[0]["owner"] == "active_user"

    def test_update_key(self):
        from backend.api_keys import generate_api_key, update_key, get_key_by_id
        result = generate_api_key(owner="test_user", plan="free")
        update_key(result["id"], plan="clinique", owner="Dr. Updated")
        key = get_key_by_id(result["id"])
        assert key["plan"] == "clinique"
        assert key["owner"] == "Dr. Updated"

    def test_delete_key(self):
        from backend.api_keys import generate_api_key, delete_key, get_key_by_id
        result = generate_api_key(owner="doomed_user")
        assert delete_key(result["id"]) is True
        assert get_key_by_id(result["id"]) is None

    def test_get_all_usage_summary(self):
        from backend.api_keys import generate_api_key, record_usage, get_all_usage_summary
        k1 = generate_api_key(owner="user_a", plan="starter")
        k2 = generate_api_key(owner="user_b", plan="clinique")
        record_usage(k1["id"], endpoint="/analyze", is_analysis=True)
        record_usage(k1["id"], endpoint="/analyze", is_analysis=True)
        record_usage(k2["id"], endpoint="/analyze", is_analysis=True)
        summary = get_all_usage_summary()
        assert summary["total_analyses"] == 3
        assert summary["total_requests"] == 3
        assert summary["active_keys"] == 2

    def test_plans_configuration(self):
        from backend.api_keys import PLANS
        assert "free" in PLANS
        assert "starter" in PLANS
        assert "clinique" in PLANS
        assert "institution" in PLANS
        assert PLANS["starter"]["max_analyses_per_month"] == 50
        assert PLANS["institution"]["max_analyses_per_month"] == -1


# ═══════════ Integration tests: Admin routes ═══════════

class TestAdminRoutes:

    def test_admin_requires_token(self, client_no_admin):
        """Admin routes should 401/503 without proper token."""
        resp = client_no_admin.get("/admin/keys")
        assert resp.status_code in (401, 503)

    def test_admin_wrong_token(self, admin_client):
        resp = admin_client.get("/admin/keys", headers={"Authorization": "Bearer wrong-token"})
        assert resp.status_code == 401

    def test_create_and_list_keys(self, admin_client):
        headers = {"Authorization": "Bearer test-admin-secret"}

        # Create a key
        resp = admin_client.post(
            "/admin/keys",
            json={"owner": "Clinique Test", "email": "cli@test.com", "plan": "clinique"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["raw_key"].startswith("nlk_")
        assert data["plan"] == "clinique"
        key_id = data["id"]

        # List keys
        resp = admin_client.get("/admin/keys", headers=headers)
        assert resp.status_code == 200
        keys = resp.json()["keys"]
        assert len(keys) >= 1
        assert any(k["id"] == key_id for k in keys)

    def test_get_key_details(self, admin_client):
        headers = {"Authorization": "Bearer test-admin-secret"}
        create_resp = admin_client.post(
            "/admin/keys",
            json={"owner": "Detail Test"},
            headers=headers,
        )
        key_id = create_resp.json()["id"]

        resp = admin_client.get(f"/admin/keys/{key_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["owner"] == "Detail Test"
        assert "usage" in data
        assert "plan_info" in data

    def test_update_key_plan(self, admin_client):
        headers = {"Authorization": "Bearer test-admin-secret"}
        create_resp = admin_client.post(
            "/admin/keys",
            json={"owner": "Upgrade Test", "plan": "free"},
            headers=headers,
        )
        key_id = create_resp.json()["id"]

        resp = admin_client.patch(
            f"/admin/keys/{key_id}",
            json={"plan": "starter"},
            headers=headers,
        )
        assert resp.status_code == 200

        # Verify
        resp = admin_client.get(f"/admin/keys/{key_id}", headers=headers)
        assert resp.json()["plan"] == "starter"

    def test_revoke_key(self, admin_client):
        headers = {"Authorization": "Bearer test-admin-secret"}
        create_resp = admin_client.post(
            "/admin/keys",
            json={"owner": "To Revoke"},
            headers=headers,
        )
        key_id = create_resp.json()["id"]

        resp = admin_client.post(f"/admin/keys/{key_id}/revoke", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "revoked"

    def test_delete_key(self, admin_client):
        headers = {"Authorization": "Bearer test-admin-secret"}
        create_resp = admin_client.post(
            "/admin/keys",
            json={"owner": "To Delete"},
            headers=headers,
        )
        key_id = create_resp.json()["id"]

        resp = admin_client.delete(f"/admin/keys/{key_id}", headers=headers)
        assert resp.status_code == 200

        resp = admin_client.get(f"/admin/keys/{key_id}", headers=headers)
        assert resp.status_code == 404

    def test_usage_endpoint(self, admin_client):
        headers = {"Authorization": "Bearer test-admin-secret"}
        create_resp = admin_client.post(
            "/admin/keys",
            json={"owner": "Usage Test"},
            headers=headers,
        )
        key_id = create_resp.json()["id"]

        resp = admin_client.get(f"/admin/keys/{key_id}/usage", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["key_id"] == key_id
        assert data["analyses_count"] == 0

    def test_usage_summary(self, admin_client):
        headers = {"Authorization": "Bearer test-admin-secret"}
        resp = admin_client.get("/admin/usage/summary", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_analyses" in data
        assert "month" in data

    def test_plans_endpoint(self, admin_client):
        headers = {"Authorization": "Bearer test-admin-secret"}
        resp = admin_client.get("/admin/plans", headers=headers)
        assert resp.status_code == 200
        plans = resp.json()["plans"]
        assert "free" in plans
        assert "institution" in plans

    def test_create_key_invalid_plan(self, admin_client):
        headers = {"Authorization": "Bearer test-admin-secret"}
        resp = admin_client.post(
            "/admin/keys",
            json={"owner": "Bad Plan", "plan": "nonexistent"},
            headers=headers,
        )
        assert resp.status_code == 400


# ═══════════ Integration tests: API Key quota in /api/quota ═══════════

class TestApiQuotaEndpoint:

    def test_quota_without_key(self, admin_client):
        resp = admin_client.get("/api/quota")
        assert resp.status_code == 401

    def test_quota_with_valid_key(self, admin_client):
        headers = {"Authorization": "Bearer test-admin-secret"}
        create_resp = admin_client.post(
            "/admin/keys",
            json={"owner": "Quota Tester", "plan": "starter"},
            headers=headers,
        )
        raw_key = create_resp.json()["raw_key"]

        resp = admin_client.get("/api/quota", headers={"X-API-Key": raw_key})
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"] == "starter"
        assert data["quota"]["allowed"] is True
        assert data["quota"]["limit"] == 50

    def test_quota_with_invalid_key(self, admin_client):
        resp = admin_client.get("/api/quota", headers={"X-API-Key": "nlk_fake_key"})
        assert resp.status_code == 401
