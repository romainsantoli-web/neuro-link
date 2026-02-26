"""
Stripe payment integration for Neuro-Link SaaS.

Handles:
- Checkout session creation for plan subscriptions
- Webhook processing (subscription lifecycle events)
- Customer portal session creation
- Plan <-> Stripe Price ID mapping

Requires environment variables:
- STRIPE_SECRET_KEY: Stripe API secret key
- STRIPE_WEBHOOK_SECRET: Webhook endpoint signing secret
- STRIPE_PRICE_STARTER: Price ID for Starter plan
- STRIPE_PRICE_CLINIQUE: Price ID for Clinique plan
- STRIPE_PRICE_INSTITUTION: Price ID for Institution plan
- FRONTEND_URL: Frontend base URL for redirects (default: http://localhost:5173)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("neuro-link.stripe")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").strip().rstrip("/")

# Plan → Stripe Price ID mapping (configured via env vars)
STRIPE_PRICE_IDS: dict[str, str] = {
    "starter": os.getenv("STRIPE_PRICE_STARTER", "").strip(),
    "clinique": os.getenv("STRIPE_PRICE_CLINIQUE", "").strip(),
    "institution": os.getenv("STRIPE_PRICE_INSTITUTION", "").strip(),
}

_stripe = None


def _get_stripe():
    """Lazy-import stripe to avoid ImportError if not installed."""
    global _stripe
    if _stripe is None:
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            _stripe = stripe
        except ImportError:
            raise RuntimeError("stripe package not installed. Run: pip install stripe")
    return _stripe


def is_configured() -> bool:
    """Check if Stripe is properly configured."""
    return bool(STRIPE_SECRET_KEY) and any(STRIPE_PRICE_IDS.values())


def get_price_id(plan: str) -> str:
    """Get Stripe Price ID for a plan."""
    price_id = STRIPE_PRICE_IDS.get(plan, "")
    if not price_id:
        raise ValueError(f"No Stripe Price ID configured for plan '{plan}'. Set STRIPE_PRICE_{plan.upper()} env var.")
    return price_id


def create_checkout_session(
    plan: str,
    owner: str,
    email: str,
    api_key_id: int,
    success_url: str | None = None,
    cancel_url: str | None = None,
) -> dict[str, Any]:
    """
    Create a Stripe Checkout Session for a plan subscription.

    Returns: {'session_id': str, 'url': str}
    """
    stripe = _get_stripe()
    price_id = get_price_id(plan)

    if not success_url:
        success_url = f"{FRONTEND_URL}?stripe=success&session_id={{CHECKOUT_SESSION_ID}}"
    if not cancel_url:
        cancel_url = f"{FRONTEND_URL}?stripe=cancelled"

    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        customer_email=email if email else None,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "neuro_link_plan": plan,
            "neuro_link_owner": owner,
            "neuro_link_key_id": str(api_key_id),
        },
        subscription_data={
            "metadata": {
                "neuro_link_plan": plan,
                "neuro_link_key_id": str(api_key_id),
            },
        },
    )

    logger.info("Checkout session created: %s for plan=%s owner=%s", session.id, plan, owner)

    return {
        "session_id": session.id,
        "url": session.url,
    }


def create_portal_session(customer_id: str) -> dict[str, Any]:
    """
    Create a Stripe Customer Portal session for managing subscription.

    Returns: {'url': str}
    """
    stripe = _get_stripe()

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=FRONTEND_URL,
    )

    return {"url": session.url}


def construct_webhook_event(payload: bytes, sig_header: str) -> Any:
    """
    Verify and construct a Stripe webhook event.

    Raises ValueError if verification fails.
    """
    stripe = _get_stripe()

    if not STRIPE_WEBHOOK_SECRET:
        raise ValueError("STRIPE_WEBHOOK_SECRET not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError as e:
        raise ValueError(f"Webhook signature verification failed: {e}")

    return event


def handle_webhook_event(event: Any) -> dict[str, Any]:
    """
    Process a Stripe webhook event.

    Supported events:
    - checkout.session.completed → Activate plan
    - customer.subscription.updated → Update plan
    - customer.subscription.deleted → Downgrade to free
    - invoice.payment_failed → Log warning

    Returns: {'action': str, 'details': dict}
    """
    event_type = event["type"]
    data = event["data"]["object"]

    result: dict[str, Any] = {"event_type": event_type, "action": "ignored", "details": {}}

    if event_type == "checkout.session.completed":
        metadata = data.get("metadata", {})
        plan = metadata.get("neuro_link_plan", "")
        key_id = metadata.get("neuro_link_key_id", "")
        customer_id = data.get("customer", "")
        subscription_id = data.get("subscription", "")

        result["action"] = "subscription_created"
        result["details"] = {
            "plan": plan,
            "key_id": int(key_id) if key_id else None,
            "customer_id": customer_id,
            "subscription_id": subscription_id,
            "email": data.get("customer_email", ""),
        }

        # Auto-activate the API key with the correct plan
        if key_id:
            try:
                from backend.api_keys import update_key
                update_key(int(key_id), plan=plan, active=True)
                logger.info("API key %s activated with plan %s via checkout", key_id, plan)
            except Exception as exc:
                logger.error("Failed to activate key %s: %s", key_id, exc)

    elif event_type == "customer.subscription.updated":
        metadata = data.get("metadata", {})
        key_id = metadata.get("neuro_link_key_id", "")
        status = data.get("status", "")
        items = data.get("items", {}).get("data", [])

        result["action"] = "subscription_updated"
        result["details"] = {
            "key_id": int(key_id) if key_id else None,
            "status": status,
            "subscription_id": data.get("id", ""),
        }

        # If subscription becomes active and has a plan change
        if key_id and status == "active" and items:
            current_price = items[0].get("price", {}).get("id", "")
            new_plan = next(
                (plan for plan, pid in STRIPE_PRICE_IDS.items() if pid == current_price),
                None,
            )
            if new_plan:
                try:
                    from backend.api_keys import update_key
                    update_key(int(key_id), plan=new_plan)
                    logger.info("API key %s plan changed to %s via subscription update", key_id, new_plan)
                    result["details"]["new_plan"] = new_plan
                except Exception as exc:
                    logger.error("Failed to update key %s plan: %s", key_id, exc)

    elif event_type == "customer.subscription.deleted":
        metadata = data.get("metadata", {})
        key_id = metadata.get("neuro_link_key_id", "")

        result["action"] = "subscription_cancelled"
        result["details"] = {
            "key_id": int(key_id) if key_id else None,
            "subscription_id": data.get("id", ""),
        }

        # Downgrade to free plan
        if key_id:
            try:
                from backend.api_keys import update_key
                update_key(int(key_id), plan="free")
                logger.info("API key %s downgraded to free (subscription cancelled)", key_id)
            except Exception as exc:
                logger.error("Failed to downgrade key %s: %s", key_id, exc)

    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer", "")
        subscription_id = data.get("subscription", "")
        result["action"] = "payment_failed"
        result["details"] = {
            "customer_id": customer_id,
            "subscription_id": subscription_id,
            "attempt_count": data.get("attempt_count", 0),
        }
        logger.warning("Payment failed for customer %s, subscription %s", customer_id, subscription_id)

    else:
        logger.debug("Unhandled Stripe event: %s", event_type)

    return result


def get_stripe_config() -> dict[str, Any]:
    """Return Stripe configuration status (no secrets exposed)."""
    return {
        "configured": is_configured(),
        "has_secret_key": bool(STRIPE_SECRET_KEY),
        "has_webhook_secret": bool(STRIPE_WEBHOOK_SECRET),
        "price_ids": {plan: bool(pid) for plan, pid in STRIPE_PRICE_IDS.items()},
        "frontend_url": FRONTEND_URL,
    }
