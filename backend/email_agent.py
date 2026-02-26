"""
Neuro-Link Email Agent  --  send emails via Resend API.

Environment variables:
    RESEND_API_KEY      Resend API key  (re_xxxxx)
    EMAIL_FROM          Sender address  (default: onboarding@resend.dev for sandbox)

Usage (CLI):
    python -m backend.email_agent send \
        --to "dest@example.com" \
        --subject "Objet du mail" \
        --body "Corps du mail en texte"

    python -m backend.email_agent send-template \
        --to "conor@openbci.com" \
        --template commercial/08_proposition_partenariat_openbci.md

    python -m backend.email_agent test
        -> envoie un mail de test a neuro.link013@gmail.com

    python -m backend.email_agent log

Usage (Python):
    from backend.email_agent import EmailAgent
    agent = EmailAgent()
    agent.send(to="dest@example.com", subject="Hello", body="World")
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --- Configuration --------------------------------------------------------

DEFAULT_FROM = "Neuro-Link <onboarding@resend.dev>"
OWNER_EMAIL = "neuro.link013@gmail.com"
RESEND_API_URL = "https://api.resend.com/emails"

# --- Signature HTML -------------------------------------------------------

SIGNATURE_HTML = (
    '<br/>'
    '<div style="margin-top:24px; padding-top:16px; border-top:1px solid #e2e8f0;'
    " font-family:'Inter',Helvetica,Arial,sans-serif; font-size:13px;"
    ' color:#64748b; line-height:1.6;">'
    '  <strong style="color:#1e293b; font-size:14px;">Romain Kocupyr</strong><br/>'
    '  Fondateur &mdash; <span style="color:#3B82F6;">Neuro-Link</span><br/>'
    '  <span style="font-size:12px;">Depistage Alzheimer par IA &amp; EEG'
    " &middot; Precision 99.95%</span><br/>"
    '  <a href="https://neuro-link.ai" style="color:#3B82F6;'
    ' text-decoration:none;">neuro-link.ai</a> &middot;'
    '  <a href="https://github.com/romainsantoli-web/neuro-link"'
    ' style="color:#3B82F6; text-decoration:none;">GitHub</a><br/>'
    '  <span style="font-size:11px; color:#94a3b8;">Open-source &middot;'
    " AGPL v3 &middot; 118 tests &middot; 7 formats EEG</span>"
    "</div>"
)

SIGNATURE_TEXT = (
    "\n--\n"
    "Romain Kocupyr\n"
    "Fondateur - Neuro-Link\n"
    "Depistage Alzheimer par IA & EEG - Precision 99.95%\n"
    "https://neuro-link.ai - https://github.com/romainsantoli-web/neuro-link\n"
    "Open-source - AGPL v3 - 118 tests - 7 formats EEG\n"
)

# --- Log ------------------------------------------------------------------

LOG_DIR = Path(__file__).resolve().parent / "data"
LOG_FILE = LOG_DIR / "email_log.jsonl"


def _log(entry: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# --- Markdown to HTML -----------------------------------------------------


def _md_to_html(md: str) -> str:
    lines = md.strip().split("\n")
    out: list[str] = []
    in_list = False

    for line in lines:
        s = line.strip()
        if s.startswith("### "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(
                '<h3 style="color:#1e293b;margin:18px 0 8px;">'
                + s[4:]
                + "</h3>"
            )
        elif s.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(
                '<h2 style="color:#1e293b;margin:24px 0 10px;">'
                + s[3:]
                + "</h2>"
            )
        elif s.startswith("# "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(
                '<h1 style="color:#1e293b;margin:28px 0 12px;">'
                + s[2:]
                + "</h1>"
            )
        elif s in ("---", "***", "___"):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(
                '<hr style="border:none;border-top:1px solid #e2e8f0;'
                'margin:20px 0;"/>'
            )
        elif s.startswith("- ") or s.startswith("* "):
            if not in_list:
                out.append('<ul style="padding-left:20px;margin:8px 0;">')
                in_list = True
            out.append("<li>" + _inline(s[2:]) + "</li>")
        elif not s:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append("<br/>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append("<p>" + _inline(s) + "</p>")

    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def _inline(t: str) -> str:
    t = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" style="color:#3B82F6;">\1</a>',
        t,
    )
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    t = re.sub(
        r"`(.+?)`",
        r'<code style="background:#f1f5f9;padding:2px 6px;'
        r'border-radius:4px;font-size:13px;">\1</code>',
        t,
    )
    return t


# --- Resend API call ------------------------------------------------------


def _resend_send(api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Call Resend POST /emails.  Returns {"id": "..."} on success."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        RESEND_API_URL,
        data=data,
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "User-Agent": "NeuroLink-EmailAgent/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError("Resend API error " + str(e.code) + ": " + body)


# --- EmailAgent -----------------------------------------------------------


class EmailAgent:
    """Resend-based email agent for Neuro-Link."""

    def __init__(
        self,
        api_key: str | None = None,
        from_addr: str | None = None,
    ):
        self.api_key = api_key or os.getenv("RESEND_API_KEY", "")
        self.from_addr = from_addr or os.getenv("EMAIL_FROM", DEFAULT_FROM)

        if not self.api_key:
            raise ValueError(
                "RESEND_API_KEY non defini.\n"
                "  1. Cree un compte sur https://resend.com\n"
                "  2. Dashboard -> API Keys -> Create API Key\n"
                "  3. export RESEND_API_KEY='re_xxxxxxxxxx'"
            )

    # --- send -------------------------------------------------------------

    def send(
        self,
        to: str | list[str],
        subject: str,
        body: str = "",
        html: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        reply_to: str | None = None,
        add_signature: bool = True,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Send an email via Resend."""
        to_list = [to] if isinstance(to, str) else list(to)
        cc_list = ([cc] if isinstance(cc, str) else list(cc)) if cc else []
        bcc_list = ([bcc] if isinstance(bcc, str) else list(bcc)) if bcc else []

        # Build text
        text_body = body
        if add_signature:
            text_body += SIGNATURE_TEXT

        # Build HTML
        if html:
            html_body = html
        elif body:
            html_body = body.replace("\n", "<br/>\n")
        else:
            html_body = ""

        if html_body and add_signature:
            html_body += SIGNATURE_HTML

        if html_body:
            html_body = (
                "<!DOCTYPE html>\n"
                '<html><head><meta charset="utf-8"/></head>\n'
                "<body style=\"font-family:'Inter',Helvetica,Arial,sans-serif;"
                "font-size:15px;color:#1e293b;line-height:1.7;"
                'max-width:680px;margin:0 auto;padding:20px;">\n'
                + html_body
                + "\n</body></html>"
            )

        # Resend payload
        payload: dict[str, Any] = {
            "from": self.from_addr,
            "to": to_list,
            "subject": subject,
        }
        if text_body:
            payload["text"] = text_body
        if html_body:
            payload["html"] = html_body
        if cc_list:
            payload["cc"] = cc_list
        if bcc_list:
            payload["bcc"] = bcc_list
        if reply_to:
            payload["reply_to"] = reply_to

        # Dry run
        if dry_run:
            result = {
                "status": "dry_run",
                "to": to_list,
                "cc": cc_list,
                "subject": subject,
            }
            _log({**result, "from": self.from_addr})
            return result

        # Send via Resend
        resp = _resend_send(self.api_key, payload)
        result = {
            "status": "sent",
            "id": resp.get("id", ""),
            "to": to_list,
            "cc": cc_list,
            "subject": subject,
        }
        _log({**result, "from": self.from_addr})
        print("  Email envoye a " + ", ".join(to_list) + "  (id: " + result["id"] + ")")
        return result

    # --- send_template ----------------------------------------------------

    def send_template(
        self,
        to: str | list[str],
        template_path: str | Path,
        subject: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        reply_to: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Send from a Markdown template.  First '# ' line becomes subject."""
        path = Path(template_path)
        if not path.exists():
            raise FileNotFoundError("Template introuvable : " + str(path))

        content = path.read_text(encoding="utf-8")
        extracted = subject
        body_lines: list[str] = []

        for line in content.split("\n"):
            s = line.strip()
            if not extracted:
                if s.startswith("# "):
                    extracted = s[2:].strip()
                    continue
                if s.lower().startswith("subject:"):
                    extracted = s.split(":", 1)[1].strip()
                    continue
            body_lines.append(line)

        if not extracted:
            extracted = "[Neuro-Link] " + path.stem

        body_text = "\n".join(body_lines).strip()
        body_html = _md_to_html(body_text)

        return self.send(
            to=to,
            subject=extracted,
            body=body_text,
            html=body_html,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
            dry_run=dry_run,
        )

    # --- send_test --------------------------------------------------------

    def send_test(self) -> dict[str, Any]:
        """Send a test email to the owner."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return self.send(
            to=OWNER_EMAIL,
            subject="[Neuro-Link] Test Email Agent",
            body=(
                "Ceci est un email de test envoye par l'Email Agent de Neuro-Link.\n\n"
                "Date : " + now + "\n"
                "Statut : Agent operationnel\n\n"
                "Si vous recevez ce message, l'agent email fonctionne correctement."
            ),
        )

    # --- get_log ----------------------------------------------------------

    def get_log(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the last *limit* entries from the email log."""
        if not LOG_FILE.exists():
            return []
        entries: list[dict[str, Any]] = []
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries[-limit:]


# --- CLI ------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="neuro-link-email",
        description="Neuro-Link Email Agent (Resend)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # send
    p_send = sub.add_parser("send", help="Send an email")
    p_send.add_argument("--to", required=True, help="Recipient(s), comma-separated")
    p_send.add_argument("--subject", "-s", required=True)
    p_send.add_argument("--body", "-b", default="")
    p_send.add_argument("--html", default=None, help="Path to HTML file")
    p_send.add_argument("--cc", default=None)
    p_send.add_argument("--bcc", default=None)
    p_send.add_argument("--reply-to", default=None)
    p_send.add_argument("--no-signature", action="store_true")
    p_send.add_argument("--dry-run", action="store_true")

    # send-template
    p_tpl = sub.add_parser("send-template", help="Send from Markdown template")
    p_tpl.add_argument("--to", required=True)
    p_tpl.add_argument("--template", "-t", required=True)
    p_tpl.add_argument("--subject", "-s", default=None)
    p_tpl.add_argument("--cc", default=None)
    p_tpl.add_argument("--bcc", default=None)
    p_tpl.add_argument("--reply-to", default=None)
    p_tpl.add_argument("--dry-run", action="store_true")

    # test
    sub.add_parser("test", help="Send test email")

    # log
    p_log = sub.add_parser("log", help="Show email log")
    p_log.add_argument("--limit", "-n", type=int, default=20)

    args = parser.parse_args()

    if args.command == "test":
        agent = EmailAgent()
        result = agent.send_test()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "send":
        agent = EmailAgent()
        html_content = None
        if args.html:
            html_content = Path(args.html).read_text("utf-8")
        to_list = [x.strip() for x in args.to.split(",")]
        cc_list = [x.strip() for x in args.cc.split(",")] if args.cc else None
        bcc_list = [x.strip() for x in args.bcc.split(",")] if args.bcc else None
        result = agent.send(
            to=to_list,
            subject=args.subject,
            body=args.body,
            html=html_content,
            cc=cc_list,
            bcc=bcc_list,
            reply_to=args.reply_to,
            add_signature=not args.no_signature,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "send-template":
        agent = EmailAgent()
        to_list = [x.strip() for x in args.to.split(",")]
        cc_list = [x.strip() for x in args.cc.split(",")] if args.cc else None
        bcc_list = [x.strip() for x in args.bcc.split(",")] if args.bcc else None
        result = agent.send_template(
            to=to_list,
            template_path=args.template,
            subject=args.subject,
            cc=cc_list,
            bcc=bcc_list,
            reply_to=args.reply_to,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "log":
        agent = EmailAgent.__new__(EmailAgent)
        entries = agent.get_log(args.limit)
        for e in entries:
            ts = e.get("timestamp", "?")[:19]
            status = e.get("status", "?")
            to_str = ", ".join(e.get("to", []))
            subj = e.get("subject", "")
            if status == "sent":
                icon = "+"
            elif "error" in status:
                icon = "x"
            else:
                icon = "o"
            print("  " + icon + " " + ts + "  -> " + to_str + "  [" + subj + "]")


if __name__ == "__main__":
    main()
