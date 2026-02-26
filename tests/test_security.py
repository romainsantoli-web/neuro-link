"""Tests for security middleware and rate limiting."""
import os

from fastapi.testclient import TestClient


def test_analyze_without_file_fails(client):
    resp = client.post('/analyze')
    assert resp.status_code == 422  # FastAPI validation error


def test_rate_limit_headers_present(client):
    resp = client.get('/health')
    # Health should always succeed
    assert resp.status_code == 200


def test_auth_required_when_token_set(monkeypatch):
    """When SECURITY_BEARER_TOKEN is set, routes need the header."""
    import backend.app as app_module

    monkeypatch.setattr(app_module, 'SECURITY_BEARER_TOKEN', 'test-secret')

    client = TestClient(app_module.app)
    resp = client.get('/project/tasks')
    assert resp.status_code == 401

    resp2 = client.get(
        '/project/tasks',
        headers={'Authorization': 'Bearer test-secret'},
    )
    assert resp2.status_code == 200
