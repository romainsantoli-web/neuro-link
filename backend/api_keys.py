"""
API Key management for Neuro-Link SaaS.

Provides API key generation, validation, quota enforcement, and usage tracking.
Storage: SQLite (backend/data/api_keys.db).

Plans and quotas:
  - free:        5 analyses/month,   60 req/min
  - starter:    50 analyses/month,  120 req/min  (€99/mois)
  - clinique:  500 analyses/month,  300 req/min  (€499/mois)
  - institution: unlimited,         600 req/min  (€1999/mois)
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "data" / "api_keys.db"

PLANS: dict[str, dict[str, Any]] = {
    "free": {
        "label": "Free",
        "max_analyses_per_month": 5,
        "max_requests_per_minute": 60,
        "price_eur": 0,
    },
    "starter": {
        "label": "Starter",
        "max_analyses_per_month": 50,
        "max_requests_per_minute": 120,
        "price_eur": 99,
    },
    "clinique": {
        "label": "Clinique",
        "max_analyses_per_month": 500,
        "max_requests_per_minute": 300,
        "price_eur": 499,
    },
    "institution": {
        "label": "Institution",
        "max_analyses_per_month": -1,  # unlimited
        "max_requests_per_minute": 600,
        "price_eur": 1999,
    },
}

_db_lock = threading.Lock()


def _current_month() -> str:
    """Return current month as 'YYYY-MM'."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash of the raw API key for storage."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _get_conn() -> sqlite3.Connection:
    """Get a SQLite connection (creates DB + tables if needed)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    with _db_lock:
        conn = _get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_hash    TEXT    UNIQUE NOT NULL,
                    key_prefix  TEXT    NOT NULL,
                    owner       TEXT    NOT NULL,
                    email       TEXT    NOT NULL DEFAULT '',
                    plan        TEXT    NOT NULL DEFAULT 'free',
                    active      INTEGER NOT NULL DEFAULT 1,
                    created_at  TEXT    NOT NULL,
                    updated_at  TEXT    NOT NULL
                );

                CREATE TABLE IF NOT EXISTS usage_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_id      INTEGER NOT NULL REFERENCES api_keys(id),
                    month       TEXT    NOT NULL,
                    endpoint    TEXT    NOT NULL,
                    timestamp   TEXT    NOT NULL
                );

                CREATE TABLE IF NOT EXISTS usage_monthly (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_id          INTEGER NOT NULL REFERENCES api_keys(id),
                    month           TEXT    NOT NULL,
                    analyses_count  INTEGER NOT NULL DEFAULT 0,
                    requests_count  INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(key_id, month)
                );

                CREATE INDEX IF NOT EXISTS idx_usage_log_key_month
                    ON usage_log(key_id, month);
                CREATE INDEX IF NOT EXISTS idx_usage_monthly_key_month
                    ON usage_monthly(key_id, month);
                CREATE INDEX IF NOT EXISTS idx_api_keys_hash
                    ON api_keys(key_hash);
            """)
            conn.commit()
        finally:
            conn.close()


# ── Key Generation ──────────────────────────────────────────────────

def generate_api_key(owner: str, email: str = "", plan: str = "free") -> dict[str, Any]:
    """
    Generate a new API key for the given owner.

    Returns dict with 'raw_key' (shown only once), 'key_prefix', 'id', etc.
    """
    if plan not in PLANS:
        raise ValueError(f"Unknown plan: {plan}. Available: {list(PLANS.keys())}")

    raw_key = f"nlk_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)
    key_prefix = raw_key[:12] + "..."
    now = datetime.now(timezone.utc).isoformat()

    with _db_lock:
        conn = _get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO api_keys (key_hash, key_prefix, owner, email, plan, active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
                (key_hash, key_prefix, owner, email, plan, now, now),
            )
            conn.commit()
            key_id = cursor.lastrowid
        finally:
            conn.close()

    return {
        "id": key_id,
        "raw_key": raw_key,
        "key_prefix": key_prefix,
        "owner": owner,
        "email": email,
        "plan": plan,
        "created_at": now,
    }


# ── Key Validation ──────────────────────────────────────────────────

def validate_key(raw_key: str) -> dict[str, Any] | None:
    """
    Validate an API key. Returns key info dict if valid and active, None otherwise.
    """
    key_hash = _hash_key(raw_key)

    with _db_lock:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM api_keys WHERE key_hash = ? AND active = 1",
                (key_hash,),
            ).fetchone()
        finally:
            conn.close()

    if not row:
        return None

    return dict(row)


# ── Quota Check ─────────────────────────────────────────────────────

def check_quota(key_id: int, plan: str, endpoint: str = "/analyze") -> dict[str, Any]:
    """
    Check if the key has remaining quota for the current month.

    Returns {'allowed': bool, 'used': int, 'limit': int, 'remaining': int}
    """
    plan_info = PLANS.get(plan, PLANS["free"])
    limit = plan_info["max_analyses_per_month"]

    if endpoint != "/analyze":
        return {"allowed": True, "used": 0, "limit": -1, "remaining": -1}

    if limit == -1:  # unlimited
        return {"allowed": True, "used": 0, "limit": -1, "remaining": -1}

    month = _current_month()

    with _db_lock:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT analyses_count FROM usage_monthly WHERE key_id = ? AND month = ?",
                (key_id, month),
            ).fetchone()
        finally:
            conn.close()

    used = row["analyses_count"] if row else 0
    remaining = max(0, limit - used)

    return {
        "allowed": used < limit,
        "used": used,
        "limit": limit,
        "remaining": remaining,
    }


# ── Usage Tracking ──────────────────────────────────────────────────

def record_usage(key_id: int, endpoint: str = "/analyze", is_analysis: bool = False) -> None:
    """Record a request for usage tracking."""
    month = _current_month()
    now = datetime.now(timezone.utc).isoformat()

    with _db_lock:
        conn = _get_conn()
        try:
            conn.execute(
                "INSERT INTO usage_log (key_id, month, endpoint, timestamp) VALUES (?, ?, ?, ?)",
                (key_id, month, endpoint, now),
            )

            conn.execute(
                """INSERT INTO usage_monthly (key_id, month, requests_count, analyses_count)
                   VALUES (?, ?, 1, ?)
                   ON CONFLICT(key_id, month)
                   DO UPDATE SET
                       requests_count = requests_count + 1,
                       analyses_count = analyses_count + ?""",
                (key_id, month, 1 if is_analysis else 0, 1 if is_analysis else 0),
            )
            conn.commit()
        finally:
            conn.close()


def get_usage(key_id: int, month: str | None = None) -> dict[str, Any]:
    """Get usage summary for a key for the given month (defaults to current)."""
    if month is None:
        month = _current_month()

    with _db_lock:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM usage_monthly WHERE key_id = ? AND month = ?",
                (key_id, month),
            ).fetchone()

            recent = conn.execute(
                """SELECT endpoint, timestamp FROM usage_log
                   WHERE key_id = ? AND month = ?
                   ORDER BY id DESC LIMIT 20""",
                (key_id, month),
            ).fetchall()
        finally:
            conn.close()

    return {
        "key_id": key_id,
        "month": month,
        "analyses_count": row["analyses_count"] if row else 0,
        "requests_count": row["requests_count"] if row else 0,
        "recent_requests": [dict(r) for r in recent],
    }


# ── Key Management (CRUD) ──────────────────────────────────────────

def list_keys(include_inactive: bool = False) -> list[dict[str, Any]]:
    """List all API keys (without hashes)."""
    with _db_lock:
        conn = _get_conn()
        try:
            if include_inactive:
                rows = conn.execute(
                    "SELECT id, key_prefix, owner, email, plan, active, created_at, updated_at FROM api_keys ORDER BY id"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, key_prefix, owner, email, plan, active, created_at, updated_at FROM api_keys WHERE active = 1 ORDER BY id"
                ).fetchall()
        finally:
            conn.close()

    result = []
    for row in rows:
        d = dict(row)
        month = _current_month()
        usage = get_usage(d["id"], month)
        d["usage_this_month"] = {
            "analyses": usage["analyses_count"],
            "requests": usage["requests_count"],
        }
        d["plan_info"] = PLANS.get(d["plan"], PLANS["free"])
        result.append(d)

    return result


def get_key_by_id(key_id: int) -> dict[str, Any] | None:
    """Get a key by its ID."""
    with _db_lock:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT id, key_prefix, owner, email, plan, active, created_at, updated_at FROM api_keys WHERE id = ?",
                (key_id,),
            ).fetchone()
        finally:
            conn.close()

    if not row:
        return None
    return dict(row)


def update_key(key_id: int, plan: str | None = None, active: bool | None = None, owner: str | None = None, email: str | None = None) -> bool:
    """Update a key's plan, active status, owner, or email."""
    updates = []
    params: list[Any] = []

    if plan is not None:
        if plan not in PLANS:
            raise ValueError(f"Unknown plan: {plan}")
        updates.append("plan = ?")
        params.append(plan)

    if active is not None:
        updates.append("active = ?")
        params.append(1 if active else 0)

    if owner is not None:
        updates.append("owner = ?")
        params.append(owner)

    if email is not None:
        updates.append("email = ?")
        params.append(email)

    if not updates:
        return False

    updates.append("updated_at = ?")
    params.append(datetime.now(timezone.utc).isoformat())
    params.append(key_id)

    with _db_lock:
        conn = _get_conn()
        try:
            cursor = conn.execute(
                f"UPDATE api_keys SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def revoke_key(key_id: int) -> bool:
    """Revoke (deactivate) an API key."""
    return update_key(key_id, active=False)


def delete_key(key_id: int) -> bool:
    """Permanently delete a key and its usage data."""
    with _db_lock:
        conn = _get_conn()
        try:
            conn.execute("DELETE FROM usage_log WHERE key_id = ?", (key_id,))
            conn.execute("DELETE FROM usage_monthly WHERE key_id = ?", (key_id,))
            cursor = conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


def get_all_usage_summary() -> dict[str, Any]:
    """Get a summary of all API usage for the current month."""
    month = _current_month()
    with _db_lock:
        conn = _get_conn()
        try:
            total_row = conn.execute(
                """SELECT
                       COALESCE(SUM(analyses_count), 0) as total_analyses,
                       COALESCE(SUM(requests_count), 0) as total_requests,
                       COUNT(DISTINCT key_id) as active_keys
                   FROM usage_monthly WHERE month = ?""",
                (month,),
            ).fetchone()

            top_users = conn.execute(
                """SELECT um.key_id, ak.owner, ak.plan, um.analyses_count, um.requests_count
                   FROM usage_monthly um
                   JOIN api_keys ak ON ak.id = um.key_id
                   WHERE um.month = ?
                   ORDER BY um.analyses_count DESC
                   LIMIT 10""",
                (month,),
            ).fetchall()
        finally:
            conn.close()

    return {
        "month": month,
        "total_analyses": total_row["total_analyses"],
        "total_requests": total_row["total_requests"],
        "active_keys": total_row["active_keys"],
        "top_users": [dict(r) for r in top_users],
    }


# Initialize DB on import
init_db()
