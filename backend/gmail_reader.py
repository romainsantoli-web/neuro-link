"""
Neuro-Link Gmail Reader — read inbox via Gmail API (OAuth2).

First run will open a browser for OAuth2 consent.
Subsequent runs use the cached token in backend/data/gmail_token.json.

Environment variables (optional):
    GMAIL_CREDENTIALS_PATH   Path to credentials.json (default: backend/data/gmail_credentials.json)

Usage (CLI):
    python -m backend.gmail_reader recent          # last 10 emails
    python -m backend.gmail_reader recent -n 20    # last 20
    python -m backend.gmail_reader search "OpenBCI"
    python -m backend.gmail_reader thread <thread_id>
    python -m backend.gmail_reader auth             # force re-auth

Usage (Python):
    from backend.gmail_reader import GmailReader
    reader = GmailReader()
    emails = reader.fetch_recent(max_results=10)
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_CREDENTIALS = DATA_DIR / "gmail_credentials.json"
TOKEN_PATH = DATA_DIR / "gmail_token.json"

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailReader:
    """Read Gmail inbox via OAuth2 API."""

    def __init__(self, credentials_path: str | Path | None = None):
        self.credentials_path = Path(
            credentials_path
            or os.getenv("GMAIL_CREDENTIALS_PATH", str(DEFAULT_CREDENTIALS))
        )
        self._service = None

    @property
    def service(self):
        """Lazy-init the Gmail API service with OAuth2."""
        if self._service is None:
            self._service = self._build_service()
        return self._service

    def _build_service(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None

        # Load existing token
        if TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

        # Refresh or re-auth
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"Gmail credentials introuvables: {self.credentials_path}\n"
                        "  1. Va sur https://console.cloud.google.com/apis/credentials\n"
                        "  2. Telecharge le JSON OAuth2 client\n"
                        "  3. Place-le dans backend/data/gmail_credentials.json"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token for next run
            TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

        return build("gmail", "v1", credentials=creds)

    def fetch_recent(self, max_results: int = 10) -> list[dict[str, Any]]:
        """Fetch the most recent emails from the inbox."""
        results = (
            self.service.users()
            .messages()
            .list(userId="me", maxResults=max_results, labelIds=["INBOX"])
            .execute()
        )
        messages = results.get("messages", [])
        return [self._get_message(m["id"]) for m in messages]

    def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Search emails by Gmail query string."""
        results = (
            self.service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        messages = results.get("messages", [])
        return [self._get_message(m["id"]) for m in messages]

    def fetch_thread(self, thread_id: str) -> list[dict[str, Any]]:
        """Fetch all messages in a Gmail thread."""
        thread = (
            self.service.users()
            .threads()
            .get(userId="me", id=thread_id, format="full")
            .execute()
        )
        return [self._parse_message(m) for m in thread.get("messages", [])]

    def _get_message(self, msg_id: str) -> dict[str, Any]:
        """Fetch and parse a single message by ID."""
        msg = (
            self.service.users()
            .messages()
            .get(userId="me", id=msg_id, format="full")
            .execute()
        )
        return self._parse_message(msg)

    @staticmethod
    def _parse_message(msg: dict[str, Any]) -> dict[str, Any]:
        """Parse a Gmail API message into a clean dict."""
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

        # Extract body
        body = ""
        payload = msg.get("payload", {})
        parts = payload.get("parts", [])
        if parts:
            for part in parts:
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                        break
            if not body:
                for part in parts:
                    if part.get("mimeType") == "text/html":
                        data = part.get("body", {}).get("data", "")
                        if data:
                            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                            break
        else:
            data = payload.get("body", {}).get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        return {
            "gmail_id": msg.get("id", ""),
            "thread_id": msg.get("threadId", ""),
            "from_addr": headers.get("from", ""),
            "to": headers.get("to", ""),
            "subject": headers.get("subject", ""),
            "date": headers.get("date", ""),
            "body": body[:5000],
            "labels": msg.get("labelIds", []),
            "snippet": msg.get("snippet", ""),
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="neuro-link-gmail",
        description="Neuro-Link Gmail Reader (OAuth2)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("recent", help="Fetch recent emails")
    p.add_argument("-n", "--count", type=int, default=10)

    p = sub.add_parser("search", help="Search emails")
    p.add_argument("query")
    p.add_argument("-n", "--count", type=int, default=10)

    p = sub.add_parser("thread", help="Fetch a thread")
    p.add_argument("thread_id")

    sub.add_parser("auth", help="Force re-authentication")

    args = parser.parse_args()
    reader = GmailReader()

    if args.command == "auth":
        if TOKEN_PATH.exists():
            TOKEN_PATH.unlink()
            print("  Token supprime. Re-authentification au prochain appel.")
        _ = reader.service
        print("  Authentification reussie.")

    elif args.command == "recent":
        emails = reader.fetch_recent(max_results=args.count)
        for e in emails:
            print(f"  [{e['date'][:20]}] {e['from_addr'][:40]}")
            print(f"    {e['subject']}")
            print()

    elif args.command == "search":
        emails = reader.search(args.query, max_results=args.count)
        print(f"  {len(emails)} resultats pour '{args.query}':\n")
        for e in emails:
            print(f"  [{e['date'][:20]}] {e['from_addr'][:40]}")
            print(f"    {e['subject']}")
            print()

    elif args.command == "thread":
        messages = reader.fetch_thread(args.thread_id)
        print(f"  Thread {args.thread_id} ({len(messages)} messages):\n")
        for m in messages:
            print(f"  [{m['date'][:20]}] {m['from_addr']}")
            print(f"    {m['subject']}")
            print(f"    {m['body'][:200]}")
            print()


if __name__ == "__main__":
    main()
