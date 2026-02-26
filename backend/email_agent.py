"""
Neuro-Link Email Agent — send emails via Gmail SMTP.

Environment variables:
    EMAIL_ADDRESS       Gmail address  (default: neuro.link013@gmail.com)
    EMAIL_APP_PASSWORD  Gmail App Password (16 chars, from Google Account → Security → App Passwords)

Usage (CLI):
    python -m backend.email_agent send \\
        --to "dest@example.com" \\
        --subject "Objet du mail" \\
        --body "Corps du mail en texte" \\
        --html body.html \\
        --attach rapport.pdf

    python -m backend.email_agent send-template \\
        --to "conor@openbci.com" \\
        --template commercial/08_proposition_partenariat_openbci.md

    python -m backend.email_agent test
        → envoie un mail de test à soi-même

Usage (Python):
    from backend.email_agent import EmailAgent
    agent = EmailAgent()
    agent.send(to="dest@example.com", subject="Hello", body="World")
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import smtplib
import ssl
import sys
from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

# ─── Configuration ────────────────────────────────────────────────────────────

DEFAULT_EMAIL = "neuro.link013@gmail.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# Signature HTML par défaut
DEFAULT_SIGNATURE_HTML = """
<br/>
<div style="margin-top:24px; padding-top:16px; border-top:1px solid #e2e8f0; font-family:'Inter',Helvetica,Arial,sans-serif; font-size:13px; color:#64748b; line-height:1.6;">
  <strong style="color:#1e293b; font-size:14px;">Romain Kocupyr</strong><br/>
  Fondateur — <span style="color:#3B82F6;">Neuro-Link</span><br/>
  <span style="font-size:12px;">Dépistage Alzheimer par IA & EEG · Précision 99.95%</span><br/>
  <a href="https://neuro-link.ai" style="color:#3B82F6; text-decoration:none;">neuro-link.ai</a> ·
  <a href="https://github.com/romainsantoli-web/neuro-link" style="color:#3B82F6; text-decoration:none;">GitHub</a><br/>
  <span style="font-size:11px; color:#94a3b8;">Open-source · AGPL v3 · 118 tests · 7 formats EEG</span>
</div>
"""

DEFAULT_SIGNATURE_TEXT = """
--
Romain Kocupyr
Fondateur — Neuro-Link
Dépistage Alzheimer par IA & EEG · Précision 99.95%
https://neuro-link.ai · https://github.com/romainsantoli-web/neuro-link
Open-source · AGPL v3 · 118 tests · 7 formats EEG
"""

# ─── Log file ─────────────────────────────────────────────────────────────────

LOG_DIR = Path(__file__).resolve().parent / "data"
LOG_FILE = LOG_DIR / "email_log.jsonl"


def _log_email(entry: dict[str, Any]) -> None:
    """Append email send event to JSONL log."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ─── Markdown → HTML helper ──────────────────────────────────────────────────

def _md_to_html(md_text: str) -> str:
    """Lightweight Markdown → HTML (headers, bold, italic, links, lists, paragraphs)."""
    lines = md_text.strip().split("\n")
    html_lines: list[str] = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        # Headers
        if stripped.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f'<h3 style="color:#1e293b; margin:18px 0 8px;">{stripped[4:]}</h3>')
            continue
        if stripped.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f'<h2 style="color:#1e293b; margin:24px 0 10px;">{stripped[3:]}</h2>')
            continue
        if stripped.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f'<h1 style="color:#1e293b; margin:28px 0 12px;">{stripped[2:]}</h1>')
            continue

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append('<hr style="border:none; border-top:1px solid #e2e8f0; margin:20px 0;"/>')
            continue

        # List items
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_lines.append('<ul style="padding-left:20px; margin:8px 0;">')
                in_list = True
            content = _inline_format(stripped[2:])
            html_lines.append(f"<li>{content}</li>")
            continue

        # Empty line
        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<br/>")
            continue

        # Regular paragraph
        if in_list:
            html_lines.append("</ul>")
            in_list = False
        content = _inline_format(stripped)
        html_lines.append(f"<p>{content}</p>")

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def _inline_format(text: str) -> str:
    """Bold, italic, links, inline code."""
    # Links [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color:#3B82F6;">\1</a>', text)
    # Bold **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic *text*
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Code `text`
    text = re.sub(r'`(.+?)`', r'<code style="background:#f1f5f9; padding:2px 6px; border-radius:4px; font-size:13px;">\1</code>', text)
    return text


# ─── EmailAgent class ────────────────────────────────────────────────────────

class EmailAgent:
    """Gmail SMTP email agent for Neuro-Link."""

    def __init__(
        self,
        email: str | None = None,
        app_password: str | None = None,
        signature_html: str = DEFAULT_SIGNATURE_HTML,
        signature_text: str = DEFAULT_SIGNATURE_TEXT,
    ):
        self.email = email or os.getenv("EMAIL_ADDRESS", DEFAULT_EMAIL)
        self.app_password = app_password or os.getenv("EMAIL_APP_PASSWORD", "")
        self.signature_html = signature_html
        self.signature_text = signature_text

        if not self.app_password:
            raise ValueError(
                "EMAIL_APP_PASSWORD non défini. "
                "Créez un App Password : Google Account → Sécurité → Mots de passe des applications. "
                "Puis export EMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx'"
            )

    def send(
        self,
        to: str | list[str],
        subject: str,
        body: str = "",
        html: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        attachments: list[str | Path] | None = None,
        reply_to: str | None = None,
        add_signature: bool = True,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Send an email.

        Args:
            to: Recipient(s).
            subject: Email subject.
            body: Plain text body.
            html: Optional HTML body. If not provided, body is used.
            cc: CC recipient(s).
            bcc: BCC recipient(s).
            attachments: List of file paths to attach.
            reply_to: Reply-To address.
            add_signature: Append Neuro-Link signature.
            dry_run: If True, build the message but don't actually send.

        Returns:
            Dict with status, message_id, recipients.
        """
        # Normalize recipients
        to_list = [to] if isinstance(to, str) else list(to)
        cc_list = ([cc] if isinstance(cc, str) else list(cc)) if cc else []
        bcc_list = ([bcc] if isinstance(bcc, str) else list(bcc)) if bcc else []
        all_recipients = to_list + cc_list + bcc_list

        # Build message
        msg = MIMEMultipart("alternative")
        msg["From"] = f"Romain Kocupyr — Neuro-Link <{self.email}>"
        msg["To"] = ", ".join(to_list)
        msg["Subject"] = subject
        msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        if reply_to:
            msg["Reply-To"] = reply_to

        # Custom headers
        msg["X-Mailer"] = "Neuro-Link Email Agent v1.0"

        # Text part
        text_body = body
        if add_signature:
            text_body += self.signature_text
        msg.attach(MIMEText(text_body, "plain", "utf-8"))

        # HTML part
        if html:
            html_body = html
        elif body:
            # Auto-convert text to basic HTML
            html_body = body.replace("\n", "<br/>\n")
        else:
            html_body = ""

        if html_body and add_signature:
            html_body += self.signature_html

        if html_body:
            full_html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"/></head>
<body style="font-family:'Inter',Helvetica,Arial,sans-serif; font-size:15px; color:#1e293b; line-height:1.7; max-width:680px; margin:0 auto; padding:20px;">
{html_body}
</body>
</html>"""
            msg.attach(MIMEText(full_html, "html", "utf-8"))

        # Attachments
        if attachments:
            # Switch to mixed multipart to support attachments
            outer = MIMEMultipart("mixed")
            for key in ("From", "To", "Subject", "Date", "Cc", "Reply-To", "X-Mailer"):
                if msg[key]:
                    outer[key] = msg[key]
            outer.attach(msg)

            for filepath in attachments:
                path = Path(filepath)
                if not path.exists():
                    raise FileNotFoundError(f"Pièce jointe introuvable : {path}")

                ctype, _ = mimetypes.guess_type(str(path))
                if ctype is None:
                    ctype = "application/octet-stream"
                maintype, subtype = ctype.split("/", 1)

                with open(path, "rb") as f:
                    attachment = MIMEBase(maintype, subtype)
                    attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=path.name,
                )
                outer.attach(attachment)
            msg = outer

        # Dry run
        if dry_run:
            result = {
                "status": "dry_run",
                "to": to_list,
                "cc": cc_list,
                "subject": subject,
                "size_bytes": len(msg.as_string()),
            }
            _log_email({**result, "from": self.email})
            return result

        # Send via SMTP
        context = ssl.create_default_context()
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(self.email, self.app_password)
                server.sendmail(self.email, all_recipients, msg.as_string())

            result = {
                "status": "sent",
                "to": to_list,
                "cc": cc_list,
                "subject": subject,
                "message_size": len(msg.as_string()),
            }
            _log_email({**result, "from": self.email})
            print(f"✓ Email envoyé à {', '.join(to_list)}")
            return result

        except smtplib.SMTPAuthenticationError:
            error = (
                "Authentification Gmail échouée. Vérifiez :\n"
                "  1. L'adresse EMAIL_ADDRESS est correcte\n"
                "  2. EMAIL_APP_PASSWORD est un App Password (pas votre mot de passe Google)\n"
                "  3. La vérification en 2 étapes est activée sur le compte Google\n"
                "  → https://myaccount.google.com/apppasswords"
            )
            _log_email({"status": "auth_error", "to": to_list, "from": self.email})
            raise RuntimeError(error)

        except Exception as e:
            _log_email({"status": "error", "to": to_list, "from": self.email, "error": str(e)})
            raise

    def send_template(
        self,
        to: str | list[str],
        template_path: str | Path,
        subject: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        attachments: list[str | Path] | None = None,
        reply_to: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Send an email from a Markdown template file.

        The first line starting with '# ' or 'Subject: ' is used as subject
        if not provided explicitly.
        """
        path = Path(template_path)
        if not path.exists():
            raise FileNotFoundError(f"Template introuvable : {path}")

        content = path.read_text(encoding="utf-8")

        # Extract subject from template if not provided
        extracted_subject = subject
        body_lines: list[str] = []
        for line in content.split("\n"):
            stripped = line.strip()
            if not extracted_subject:
                if stripped.startswith("# "):
                    extracted_subject = stripped[2:].strip()
                    continue
                if stripped.lower().startswith("subject:"):
                    extracted_subject = stripped.split(":", 1)[1].strip()
                    continue
            body_lines.append(line)

        if not extracted_subject:
            extracted_subject = f"[Neuro-Link] {path.stem}"

        body_text = "\n".join(body_lines).strip()
        body_html = _md_to_html(body_text)

        return self.send(
            to=to,
            subject=extracted_subject,
            body=body_text,
            html=body_html,
            cc=cc,
            bcc=bcc,
            attachments=attachments,
            reply_to=reply_to,
            dry_run=dry_run,
        )

    def send_test(self) -> dict[str, Any]:
        """Send a test email to yourself."""
        return self.send(
            to=self.email,
            subject="[Neuro-Link] Test Email Agent ✓",
            body=(
                "Ceci est un email de test envoyé par l'Email Agent de Neuro-Link.\n\n"
                f"Date : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
                "Statut : Agent opérationnel\n\n"
                "Si vous recevez ce message, l'agent email fonctionne correctement."
            ),
        )

    def get_log(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent email log entries."""
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


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="neuro-link-email",
        description="Neuro-Link Email Agent — Send emails via Gmail SMTP",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── send ──
    p_send = sub.add_parser("send", help="Send an email")
    p_send.add_argument("--to", required=True, help="Recipient email(s), comma-separated")
    p_send.add_argument("--subject", "-s", required=True, help="Email subject")
    p_send.add_argument("--body", "-b", default="", help="Plain text body")
    p_send.add_argument("--html", default=None, help="Path to HTML body file")
    p_send.add_argument("--cc", default=None, help="CC recipient(s), comma-separated")
    p_send.add_argument("--bcc", default=None, help="BCC recipient(s), comma-separated")
    p_send.add_argument("--attach", nargs="*", default=[], help="File(s) to attach")
    p_send.add_argument("--reply-to", default=None, help="Reply-To address")
    p_send.add_argument("--no-signature", action="store_true", help="Don't add Neuro-Link signature")
    p_send.add_argument("--dry-run", action="store_true", help="Build message without sending")

    # ── send-template ──
    p_tpl = sub.add_parser("send-template", help="Send from a Markdown template")
    p_tpl.add_argument("--to", required=True, help="Recipient email(s), comma-separated")
    p_tpl.add_argument("--template", "-t", required=True, help="Path to .md template file")
    p_tpl.add_argument("--subject", "-s", default=None, help="Override subject (auto-detected from template)")
    p_tpl.add_argument("--cc", default=None, help="CC recipient(s)")
    p_tpl.add_argument("--bcc", default=None, help="BCC recipient(s)")
    p_tpl.add_argument("--attach", nargs="*", default=[], help="File(s) to attach")
    p_tpl.add_argument("--reply-to", default=None, help="Reply-To address")
    p_tpl.add_argument("--dry-run", action="store_true", help="Build message without sending")

    # ── test ──
    sub.add_parser("test", help="Send a test email to yourself")

    # ── log ──
    p_log = sub.add_parser("log", help="Show recent email log")
    p_log.add_argument("--limit", "-n", type=int, default=20, help="Number of entries")

    args = parser.parse_args()

    if args.command == "test":
        agent = EmailAgent()
        result = agent.send_test()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "send":
        agent = EmailAgent()
        html_content = None
        if args.html:
            html_content = Path(args.html).read_text(encoding="utf-8")

        result = agent.send(
            to=[x.strip() for x in args.to.split(",")],
            subject=args.subject,
            body=args.body,
            html=html_content,
            cc=[x.strip() for x in args.cc.split(",")] if args.cc else None,
            bcc=[x.strip() for x in args.bcc.split(",")] if args.bcc else None,
            attachments=args.attach or None,
            reply_to=args.reply_to,
            add_signature=not args.no_signature,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "send-template":
        agent = EmailAgent()
        result = agent.send_template(
            to=[x.strip() for x in args.to.split(",")],
            template_path=args.template,
            subject=args.subject,
            cc=[x.strip() for x in args.cc.split(",")] if args.cc else None,
            bcc=[x.strip() for x in args.bcc.split(",")] if args.bcc else None,
            attachments=args.attach or None,
            reply_to=args.reply_to,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "log":
        agent = EmailAgent.__new__(EmailAgent)
        entries = agent.get_log(limit=args.limit)
        for entry in entries:
            ts = entry.get("timestamp", "?")[:19]
            status = entry.get("status", "?")
            to = ", ".join(entry.get("to", []))
            subject = entry.get("subject", "")
            icon = "✓" if status == "sent" else "✗" if "error" in status else "○"
            print(f"  {icon} {ts}  → {to}  [{subject}]")
        if not entries:
            print("  (aucun email envoyé)")


if __name__ == "__main__":
    main()
