"""Tests for Stripe billing integration (P2.03)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))


# ─── Fixtures ────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    """Isolate API key DB for tests."""
    import backend.api_keys as ak_module
    db_file = tmp_path / "api_keys_test.db"
    monkeypatch.setattr(ak_module, "DB_PATH", db_file)
    ak_module.init_db()


@pytest.fixture()
def admin_client(monkeypatch):
    import backend.app as app_module
    monkeypatch.setattr(app_module, "ADMIN_TOKEN", "test-admin")
    from fastapi.testclient import TestClient
    return TestClient(app_module.app)


# ═══════════ Unit tests: stripe_billing module ═══════════

class TestStripeBillingModule:

    def test_is_configured_false_by_default(self, monkeypatch):
        import backend.stripe_billing as sb
        monkeypatch.setattr(sb, "STRIPE_SECRET_KEY", "")
        monkeypatch.setattr(sb, "STRIPE_PRICE_IDS", {"starter": "", "clinique": "", "institution": ""})
        assert sb.is_configured() is False

    def test_is_configured_true_when_set(self, monkeypatch):
        import backend.stripe_billing as sb
        monkeypatch.setattr(sb, "STRIPE_SECRET_KEY", "sk_test_123")
        monkeypatch.setattr(sb, "STRIPE_PRICE_IDS", {"starter": "price_123", "clinique": "", "institution": ""})
        assert sb.is_configured() is True

    def test_get_price_id_valid(self, monkeypatch):
        import backend.stripe_billing as sb
        monkeypatch.setattr(sb, "STRIPE_PRICE_IDS", {"starter": "price_abc", "clinique": "price_def", "institution": ""})
        assert sb.get_price_id("starter") == "price_abc"
        assert sb.get_price_id("clinique") == "price_def"

    def test_get_price_id_missing_raises(self, monkeypatch):
        import backend.stripe_billing as sb
        monkeypatch.setattr(sb, "STRIPE_PRICE_IDS", {"starter": "", "clinique": "", "institution": ""})
        with pytest.raises(ValueError, match="No Stripe Price ID"):
            sb.get_price_id("starter")

    def test_get_stripe_config(self, monkeypatch):
        import backend.stripe_billing as sb
        monkeypatch.setattr(sb, "STRIPE_SECRET_KEY", "sk_test_xxx")
        monkeypatch.setattr(sb, "STRIPE_WEBHOOK_SECRET", "whsec_xxx")
        monkeypatch.setattr(sb, "STRIPE_PRICE_IDS", {"starter": "price_1", "clinique": "price_2", "institution": ""})
        config = sb.get_stripe_config()
        assert config["configured"] is True
        assert config["has_secret_key"] is True
        assert config["has_webhook_secret"] is True
        assert config["price_ids"]["starter"] is True
        assert config["price_ids"]["institution"] is False

    def test_handle_webhook_checkout_completed(self, monkeypatch):
        """Test checkout.session.completed webhook activates API key."""
        import backend.stripe_billing as sb
        from backend.api_keys import generate_api_key, get_key_by_id

        key = generate_api_key(owner="webhook_test", plan="free")
        key_id = key["id"]

        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {
                        "neuro_link_plan": "clinique",
                        "neuro_link_key_id": str(key_id),
                    },
                    "customer": "cus_test123",
                    "subscription": "sub_test123",
                    "customer_email": "test@example.com",
                }
            }
        }

        result = sb.handle_webhook_event(event)
        assert result["action"] == "subscription_created"
        assert result["details"]["plan"] == "clinique"

        # Verify key was upgraded
        updated_key = get_key_by_id(key_id)
        assert updated_key["plan"] == "clinique"

    def test_handle_webhook_subscription_deleted(self, monkeypatch):
        """Test subscription.deleted webhook downgrades to free."""
        import backend.stripe_billing as sb
        from backend.api_keys import generate_api_key, get_key_by_id

        key = generate_api_key(owner="cancel_test", plan="starter")
        key_id = key["id"]

        event = {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "metadata": {"neuro_link_key_id": str(key_id)},
                    "id": "sub_cancel123",
                }
            }
        }

        result = sb.handle_webhook_event(event)
        assert result["action"] == "subscription_cancelled"

        updated_key = get_key_by_id(key_id)
        assert updated_key["plan"] == "free"

    def test_handle_webhook_payment_failed(self):
        import backend.stripe_billing as sb
        event = {
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "customer": "cus_fail",
                    "subscription": "sub_fail",
                    "attempt_count": 2,
                }
            }
        }
        result = sb.handle_webhook_event(event)
        assert result["action"] == "payment_failed"

    def test_handle_webhook_unknown_event(self):
        import backend.stripe_billing as sb
        event = {
            "type": "some.unknown.event",
            "data": {"object": {}}
        }
        result = sb.handle_webhook_event(event)
        assert result["action"] == "ignored"


# ═══════════ Integration tests: Stripe routes ═══════════

class TestStripeRoutes:

    def test_stripe_config_requires_admin(self, admin_client):
        resp = admin_client.get("/stripe/config")
        assert resp.status_code in (401, 503)

    def test_stripe_config_returns_status(self, admin_client):
        headers = {"Authorization": "Bearer test-admin"}
        resp = admin_client.get("/stripe/config", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "configured" in data
        assert "price_ids" in data

    def test_stripe_checkout_unconfigured(self, admin_client, monkeypatch):
        """Checkout should 503 if Stripe is not configured."""
        import backend.stripe_billing as sb
        monkeypatch.setattr(sb, "STRIPE_SECRET_KEY", "")
        monkeypatch.setattr(sb, "STRIPE_PRICE_IDS", {"starter": "", "clinique": "", "institution": ""})

        headers = {"Authorization": "Bearer test-admin"}
        resp = admin_client.post(
            "/stripe/checkout",
            json={"plan": "starter", "owner": "Test", "api_key_id": 1},
            headers=headers,
        )
        assert resp.status_code == 503
