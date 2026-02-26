"""
Neuro-Link Mistral AI Client — chat completion via Mistral free tier.

Environment variables:
    MISTRAL_API_KEY     Mistral API key

Models (free tier):
    - mistral-small-latest   (context 128K, best quality free)
    - mistral-tiny-latest    (fallback, faster)

Usage:
    from backend.mistral_client import mistral_chat, mistral_chat_json
    response = mistral_chat("Tu es un assistant.", [{"role": "user", "content": "Bonjour"}])
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Model priority chain (free tier)
MODELS = [
    "mistral-small-latest",
    "mistral-tiny-latest",
]

# Rate limiting for free tier
_call_timestamps: list[float] = []
_MAX_RPM = 25  # conservative for free tier


def _rate_limit():
    """Simple sliding-window rate limiter."""
    global _call_timestamps
    now = time.time()
    _call_timestamps = [t for t in _call_timestamps if now - t < 60]
    if len(_call_timestamps) >= _MAX_RPM:
        wait = 60 - (now - _call_timestamps[0])
        if wait > 0:
            time.sleep(wait)
    _call_timestamps.append(time.time())


def _call_mistral(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    response_format: dict | None = None,
) -> dict[str, Any]:
    """Raw call to Mistral chat completions API."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        MISTRAL_API_URL,
        data=data,
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "User-Agent": "NeuroLink-EmailAI/1.0",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def mistral_chat(
    system_prompt: str,
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    api_key: str | None = None,
) -> str:
    """Send a chat completion request to Mistral. Returns assistant text.

    Tries models in priority order, falling back on errors.
    """
    key = api_key or os.getenv("MISTRAL_API_KEY", "")
    if not key:
        raise ValueError(
            "MISTRAL_API_KEY non defini.\n"
            "  1. Va sur https://console.mistral.ai/api-keys\n"
            "  2. Cree une cle API (gratuit)\n"
            "  3. export MISTRAL_API_KEY='...'"
        )

    full_messages = [{"role": "system", "content": system_prompt}] + messages
    _rate_limit()

    last_error = None
    for model in MODELS:
        try:
            result = _call_mistral(key, model, full_messages, temperature, max_tokens)
            content = result["choices"][0]["message"]["content"]
            return content.strip()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            last_error = f"Mistral {model} error {e.code}: {body}"
            if e.code == 429:
                time.sleep(5)
                continue
            if e.code >= 500:
                continue
            raise RuntimeError(last_error)
        except Exception as e:
            last_error = str(e)
            continue

    raise RuntimeError("All Mistral models failed. Last error: " + str(last_error))


def mistral_chat_json(
    system_prompt: str,
    messages: list[dict[str, str]],
    temperature: float = 0.3,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Send a chat request expecting JSON output. Returns parsed dict."""
    key = api_key or os.getenv("MISTRAL_API_KEY", "")
    if not key:
        raise ValueError("MISTRAL_API_KEY non defini.")

    full_messages = [{"role": "system", "content": system_prompt}] + messages
    _rate_limit()

    last_error = None
    for model in MODELS:
        try:
            result = _call_mistral(
                key, model, full_messages, temperature, 4096,
                response_format={"type": "json_object"},
            )
            content = result["choices"][0]["message"]["content"].strip()
            return json.loads(content)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            last_error = f"Mistral {model} error {e.code}: {body}"
            if e.code in (429, 500, 502, 503):
                time.sleep(3)
                continue
            raise RuntimeError(last_error)
        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {e}"
            continue
        except Exception as e:
            last_error = str(e)
            continue

    raise RuntimeError("All Mistral models failed (JSON). Last error: " + str(last_error))
