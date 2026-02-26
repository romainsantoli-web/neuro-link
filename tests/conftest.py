"""Shared fixtures for Neuro-Link tests."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure the workspace root is on sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# Disable auth during tests by default
os.environ.pop('SECURITY_BEARER_TOKEN', None)
os.environ.pop('SECURITY_STRICT_MODE', None)

from backend.app import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Clear rate-limit state before each test to avoid cross-test 429s."""
    import backend.app as app_module
    app_module._request_windows.clear()
    app_module._blocked_until.clear()
    app_module._violations.clear()
    yield
    app_module._request_windows.clear()
    app_module._blocked_until.clear()
    app_module._violations.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def tmp_project_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect PROJECT_MEMORY_FILE to a temp file for isolation."""
    import backend.app as app_module

    mem_file = tmp_path / 'project_memory.jsonl'
    mem_file.write_text('')
    monkeypatch.setattr(app_module, 'PROJECT_MEMORY_FILE', mem_file)
    return mem_file


@pytest.fixture()
def tmp_memory_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect MEMORY_FILE to a temp file for isolation."""
    import backend.app as app_module

    mem_file = tmp_path / 'memory_records.jsonl'
    mem_file.write_text('')
    monkeypatch.setattr(app_module, 'MEMORY_FILE', mem_file)
    return mem_file
