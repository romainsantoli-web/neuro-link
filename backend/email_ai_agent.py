"""
Neuro-Link Email AI Agent — AI-powered email brain.

Uses Mistral AI (free tier) to draft, reply, and manage professional emails.
Stores everything in EmailMemory (FAISS + SentenceTransformers) for persistent
context. Before each action, loads the FULL relevant memory so the AI is always
up-to-date.

Targets: CHU, EHPAD, neurologues, investisseurs, partenaires tech (OpenBCI).

Usage (CLI):
    python -m backend.email_ai_agent draft --type=chu --name="CHU Montpellier"
    python -m backend.email_ai_agent followup --thread-id=em_abc123
    python -m backend.email_ai_agent reply --email-id=em_xyz789
    python -m backend.email_ai_agent analyze --email-id=em_xyz789
    python -m backend.email_ai_agent inbox
    python -m backend.email_ai_agent memory --query="OpenBCI"

Usage (Python):
    from backend.email_ai_agent import EmailAIAgent
    agent = EmailAIAgent()
    draft = agent.draft_prospection("chu", "CHU Montpellier", "Service neuro, Dr Martin")
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.email_memory import EmailMemory
from backend.mistral_client import mistral_chat, mistral_chat_json

# ---------------------------------------------------------------------------
# System prompt — expert B2B email writer for Neuro-Link
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Tu es l'agent email IA de Neuro-Link, une startup francaise de depistage de la maladie d'Alzheimer par intelligence artificielle et analyse EEG.

## Contexte Neuro-Link
- Precision de depistage: 99.95% (screening), 97.79% (staging)
- Architecture: ADFormerHybrid (Transformer dual-branch + 267 features EEG)
- Ensemble voting sur 5 modeles
- Compatible OpenBCI (Cyton, CytonDaisy, Ganglion)
- 7 formats EEG supportes (.set, .edf, .bdf, .fif, .csv, .txt, .bfcsv)
- Open-source AGPL v3 + licence commerciale
- 118 tests (48 frontend + 70 backend)
- Pipeline: Upload EEG -> Preprocessing -> Feature Extraction -> Classification -> Rapport
- Export FHIR R4 (HL7) pour integration DPI
- API SaaS avec 4 plans (Free/Starter/Clinique/Institution)
- Fondateur: Romain Kocupyr
- Site: https://neuro-link.ai
- GitHub: https://github.com/romainsantoli-web/neuro-link

## Ton Role
Tu rediges des emails professionnels B2B en francais elegant. Tu es:
- Expert en communication medicale et technologique
- Precis, factuel, chaleureux mais professionnel
- Toujours adapte au contexte du destinataire
- Capable de prospection, relance, conversion, reponse

## Cibles
- CHU / Hopitaux: accent sur validation clinique, integration DPI (FHIR), precision
- EHPAD / Maisons de retraite: accent sur depistage precoce, simplicite, cout
- Neurologues liberaux: accent sur outil d'aide, precision, gain de temps
- Investisseurs / VCs: accent sur marche, traction, technologie unique, equipe
- Partenaires tech (OpenBCI, etc.): accent sur compatibilite, open-source, communaute

## Regles
1. TOUJOURS lire le contexte memoire fourni avant de rediger
2. Ne jamais inventer de chiffres — utiliser uniquement les donnees ci-dessus
3. Adapter le ton au type de destinataire
4. Inclure un call-to-action clair dans chaque email
5. Repondre en JSON quand demande
6. Les emails de relance doivent faire reference aux precedents sans etre insistants
7. Ne jamais faire de diagnostic medical — Neuro-Link est un outil d'aide au depistage
"""

# Target-specific context
TARGET_CONTEXT = {
    "chu": (
        "Tu ecris a un CHU (Centre Hospitalier Universitaire). "
        "Accent sur: validation clinique multicentrique, integration DPI via FHIR R4, "
        "precision 99.95%, protocole ethique, publication scientifique, "
        "collaboration recherche. Ton formel et academique."
    ),
    "ehpad": (
        "Tu ecris a un EHPAD ou maison de retraite. "
        "Accent sur: depistage precoce Alzheimer pour les residents, "
        "simplicite d'utilisation (upload EEG -> resultat), cout accessible (plan Free), "
        "rapport PDF clair pour le medecin coordinateur. Ton bienveillant et pratique."
    ),
    "neurologue": (
        "Tu ecris a un neurologue liberal ou un cabinet de neurologie. "
        "Accent sur: outil d'aide au diagnostic (pas de remplacement), precision 99.95%, "
        "gain de temps, compatible avec leur casque EEG existant (OpenBCI, BrainVision, etc.), "
        "export FHIR pour leur DPI. Ton collegial entre professionnels."
    ),
    "investisseur": (
        "Tu ecris a un investisseur ou VC. "
        "Accent sur: marche Alzheimer ($30Md mondial), technologie unique (ADFormerHybrid), "
        "precision inegalee (99.95%), open-source (credibilite), "
        "pipeline SaaS B2B, equipe technique solide. Ton business et ambitieux."
    ),
    "partenaire_tech": (
        "Tu ecris a un partenaire technologique (ex: OpenBCI, fabricant EEG). "
        "Accent sur: compatibilite native, open-source, communaute, "
        "integration technique (BrainFlow, LSL, UDP), benefice mutuel. "
        "Ton technique et collaboratif."
    ),
}


class EmailAIAgent:
    """AI-powered email agent for Neuro-Link."""

    def __init__(self):
        self.memory = EmailMemory()

    # --- Draft prospection email -------------------------------------------

    def draft_prospection(
        self,
        target_type: str,
        target_name: str,
        target_info: str = "",
        extra_context: str = "",
    ) -> dict[str, Any]:
        """Draft a prospection email for a specific target.

        Args:
            target_type: One of chu, ehpad, neurologue, investisseur, partenaire_tech
            target_name: Name of the organization/person
            target_info: Additional info about the target
            extra_context: Any additional context to include

        Returns:
            Dict with keys: id, subject, body, to_suggestion, target_type, target_name
        """
        # Load full context from memory
        memory_context = self.memory.load_full_context(
            query=f"{target_type} {target_name} prospection"
        )

        # Check for existing interactions with this target
        contact_history = self.memory.get_by_contact(target_name)
        history_text = ""
        if contact_history:
            history_text = "\n\n--- HISTORIQUE AVEC CE CONTACT ---\n"
            for r in contact_history[-5:]:
                history_text += EmailMemory._format_record(r) + "\n"

        target_ctx = TARGET_CONTEXT.get(target_type, "")

        user_msg = (
            f"Redige un email de prospection pour:\n"
            f"- Destinataire: {target_name}\n"
            f"- Type: {target_type}\n"
            f"- Infos: {target_info}\n"
            f"- Contexte supplementaire: {extra_context}\n\n"
            f"MEMOIRE EMAIL:\n{memory_context}\n{history_text}\n\n"
            f"CONTEXTE CIBLE:\n{target_ctx}\n\n"
            f"Reponds en JSON avec les cles: subject, body, to_suggestion"
        )

        result = mistral_chat_json(SYSTEM_PROMPT, [{"role": "user", "content": user_msg}])

        # Store as draft in memory
        draft_id = f"em_{uuid.uuid4().hex[:12]}"
        draft = {
            "id": draft_id,
            "type": "draft",
            "subject": result.get("subject", ""),
            "body": result.get("body", ""),
            "to": result.get("to_suggestion", ""),
            "target_type": target_type,
            "target_name": target_name,
            "thread_id": f"thread_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.ingest(draft)

        return draft

    # --- Draft follow-up ---------------------------------------------------

    def draft_followup(self, thread_id: str, extra_context: str = "") -> dict[str, Any]:
        """Draft a follow-up email based on a thread."""
        thread = self.memory.get_thread(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} introuvable en memoire.")

        memory_context = self.memory.load_full_context(query=thread_id)

        thread_text = "\n\n--- THREAD COMPLET ---\n"
        for r in thread:
            thread_text += EmailMemory._format_record(r) + "\n"

        last = thread[-1]
        target_type = last.get("target_type", "")
        target_ctx = TARGET_CONTEXT.get(target_type, "")

        user_msg = (
            f"Redige un email de relance/suivi pour ce thread:\n"
            f"{thread_text}\n\n"
            f"MEMOIRE EMAIL:\n{memory_context}\n\n"
            f"CONTEXTE CIBLE:\n{target_ctx}\n\n"
            f"Contexte supplementaire: {extra_context}\n\n"
            f"Reponds en JSON avec les cles: subject, body"
        )

        result = mistral_chat_json(SYSTEM_PROMPT, [{"role": "user", "content": user_msg}])

        draft_id = f"em_{uuid.uuid4().hex[:12]}"
        draft = {
            "id": draft_id,
            "type": "draft",
            "subject": result.get("subject", ""),
            "body": result.get("body", ""),
            "to": last.get("to") or last.get("from_addr", ""),
            "target_type": target_type,
            "target_name": last.get("target_name", ""),
            "thread_id": thread_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.ingest(draft)

        return draft

    # --- Analyze incoming email --------------------------------------------

    def classify_email(self, email: dict[str, Any]) -> dict[str, Any]:
        """Classify an email: spam, pub, pro-prospect, pro-client, etc.

        Fast classification without full memory load — used for batch triage.

        Returns:
            Dict with keys: classification, urgency, action, summary, target_type
        """
        user_msg = (
            f"Classe cet email recu par Neuro-Link (startup depistage Alzheimer par EEG/IA):\n"
            f"- De: {email.get('from_addr', '?')}\n"
            f"- Sujet: {email.get('subject', '?')}\n"
            f"- Extrait: {email.get('body', '')[:1500] or email.get('snippet', '')[:500]}\n\n"
            f"Reponds en JSON strict avec ces cles:\n"
            f"- classification: spam | publicite | newsletter | notification_auto | "
            f"prospect_entrant | client | partenaire | investisseur | candidature | support | autre\n"
            f"- is_relevant: true si c'est un email professionnel pertinent pour Neuro-Link, false sinon\n"
            f"- urgency: haute | moyenne | basse\n"
            f"- action: repondre_auto | ignorer | archiver | transferer\n"
            f"  IMPORTANT: utilise 'repondre_auto' pour TOUT email pertinent (prospect, client, "
            f"partenaire, investisseur, support, candidature). N'utilise 'ignorer' que pour spam/pub/newsletter/notifications.\n"
            f"- summary: resume en 1 phrase courte\n"
            f"- target_type: chu | ehpad | neurologue | investisseur | partenaire_tech | inconnu\n"
            f"- reply_tone: formel | collegial | enthousiaste | prudent | aucun"
        )
        return mistral_chat_json(SYSTEM_PROMPT, [{"role": "user", "content": user_msg}])

    def analyze_incoming(self, email: dict[str, Any]) -> dict[str, Any]:
        """Analyze an incoming email: classify, determine urgency, recommend action.

        Args:
            email: dict with keys from_addr, subject, body, date

        Returns:
            Dict with keys: category, urgency, recommended_action, summary
        """
        memory_context = self.memory.load_full_context(
            query=f"{email.get('from_addr', '')} {email.get('subject', '')}"
        )

        contact_history = self.memory.get_by_contact(email.get("from_addr", ""))
        history_text = ""
        if contact_history:
            history_text = "\n\n--- HISTORIQUE AVEC CET EXPEDITEUR ---\n"
            for r in contact_history[-5:]:
                history_text += EmailMemory._format_record(r) + "\n"

        user_msg = (
            f"Analyse cet email entrant:\n"
            f"- De: {email.get('from_addr', '?')}\n"
            f"- Sujet: {email.get('subject', '?')}\n"
            f"- Date: {email.get('date', '?')}\n"
            f"- Corps:\n{email.get('body', '')[:2000]}\n\n"
            f"MEMOIRE EMAIL:\n{memory_context}\n{history_text}\n\n"
            f"Reponds en JSON avec les cles:\n"
            f"- category: prospect|client|partenaire|support|spam|autre\n"
            f"- urgency: haute|moyenne|basse\n"
            f"- recommended_action: repondre|ignorer|transferer|planifier_relance\n"
            f"- summary: resume en 1-2 phrases\n"
            f"- suggested_reply_tone: formel|collegial|enthousiaste|prudent"
        )

        result = mistral_chat_json(SYSTEM_PROMPT, [{"role": "user", "content": user_msg}])

        # Store the incoming email in memory
        record = {
            "type": "received",
            "from_addr": email.get("from_addr", ""),
            "to": email.get("to", "neuro.link013@gmail.com"),
            "subject": email.get("subject", ""),
            "body": email.get("body", "")[:3000],
            "date": email.get("date", ""),
            "analysis": result,
            "thread_id": email.get("thread_id", f"thread_{uuid.uuid4().hex[:8]}"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.ingest(record)

        return {**result, "memory_id": record["id"]}

    # --- Draft reply -------------------------------------------------------

    def draft_reply(self, email_id: str, extra_context: str = "") -> dict[str, Any]:
        """Draft a reply to an email stored in memory."""
        all_records = self.memory.get_all()
        target_email = None
        for r in all_records:
            if r.get("id") == email_id:
                target_email = r
                break

        if not target_email:
            raise ValueError(f"Email {email_id} introuvable en memoire.")

        thread_id = target_email.get("thread_id", "")
        thread = self.memory.get_thread(thread_id) if thread_id else [target_email]

        memory_context = self.memory.load_full_context(
            query=f"{target_email.get('from_addr', '')} {target_email.get('subject', '')}"
        )

        thread_text = "\n\n--- CONVERSATION ---\n"
        for r in thread:
            thread_text += EmailMemory._format_record(r) + "\n"

        analysis = target_email.get("analysis", {})
        tone = analysis.get("suggested_reply_tone", "professionnel")

        user_msg = (
            f"Redige une reponse a cet email:\n"
            f"- De: {target_email.get('from_addr', '?')}\n"
            f"- Sujet: {target_email.get('subject', '?')}\n"
            f"- Corps:\n{target_email.get('body', '')[:2000]}\n\n"
            f"Ton suggere: {tone}\n"
            f"{thread_text}\n\n"
            f"MEMOIRE EMAIL:\n{memory_context}\n\n"
            f"Contexte supplementaire: {extra_context}\n\n"
            f"Reponds en JSON avec les cles: subject, body"
        )

        result = mistral_chat_json(SYSTEM_PROMPT, [{"role": "user", "content": user_msg}])

        draft_id = f"em_{uuid.uuid4().hex[:12]}"
        draft = {
            "id": draft_id,
            "type": "draft",
            "subject": result.get("subject", ""),
            "body": result.get("body", ""),
            "to": target_email.get("from_addr", ""),
            "in_reply_to": email_id,
            "thread_id": thread_id or f"thread_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.ingest(draft)

        return draft

    # --- Send a draft (with approval) --------------------------------------

    def send_draft(self, draft_id: str, approve: bool = True) -> dict[str, Any]:
        """Send an approved draft via the Resend-based EmailAgent."""
        all_records = self.memory.get_all()
        draft = None
        for r in all_records:
            if r.get("id") == draft_id and r.get("type") == "draft":
                draft = r
                break

        if not draft:
            raise ValueError(f"Brouillon {draft_id} introuvable.")

        if not approve:
            return {"status": "cancelled", "draft_id": draft_id}

        from backend.email_agent import EmailAgent

        agent = EmailAgent()
        result = agent.send(
            to=draft["to"],
            subject=draft["subject"],
            body=draft["body"],
        )

        # Record the sent email in memory
        sent_record = {
            "type": "sent",
            "to": draft["to"],
            "subject": draft["subject"],
            "body": draft["body"],
            "target_type": draft.get("target_type", ""),
            "target_name": draft.get("target_name", ""),
            "thread_id": draft.get("thread_id", ""),
            "campaign_id": draft.get("campaign_id", ""),
            "resend_id": result.get("id", ""),
            "sent_from_draft": draft_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.ingest(sent_record)

        return {
            "status": "sent",
            "draft_id": draft_id,
            "resend_id": result.get("id", ""),
            "to": draft["to"],
            "subject": draft["subject"],
        }

    # --- Free-form AI email composition ------------------------------------

    def process_inbox(self, max_emails: int = 20, auto_reply: bool = True) -> dict[str, Any]:
        """Process inbox: classify all emails, auto-reply to relevant ones.

        Full pipeline:
        1. Fetch recent emails from Gmail
        2. Skip already-processed emails (check memory by gmail_id)
        3. Classify each email (spam/pub/pro/etc.)
        4. Store relevant emails in memory
        5. Auto-draft replies for professional emails
        6. Return full processing report

        Args:
            max_emails: Max emails to fetch from Gmail
            auto_reply: Whether to auto-draft replies for relevant emails

        Returns:
            Dict with processed, skipped, classifications, drafts, errors
        """
        from backend.gmail_reader import GmailReader

        reader = GmailReader()
        emails = reader.fetch_recent(max_results=max_emails)

        # Get already-processed gmail_ids from memory
        all_records = self.memory.get_all()
        processed_gmail_ids = {
            r.get("gmail_id") for r in all_records if r.get("gmail_id")
        }

        report: dict[str, Any] = {
            "total_fetched": len(emails),
            "already_processed": 0,
            "newly_processed": 0,
            "classifications": {
                "spam": 0,
                "publicite": 0,
                "newsletter": 0,
                "notification_auto": 0,
                "prospect_entrant": 0,
                "client": 0,
                "partenaire": 0,
                "investisseur": 0,
                "candidature": 0,
                "support": 0,
                "autre": 0,
            },
            "auto_replies_drafted": 0,
            "emails": [],
            "errors": [],
        }

        for email in emails:
            gmail_id = email.get("gmail_id", "")

            # Skip already processed
            if gmail_id in processed_gmail_ids:
                report["already_processed"] += 1
                continue

            try:
                # Step 1: Classify
                classification = self.classify_email(email)
                cls = classification.get("classification", "autre")
                is_relevant = classification.get("is_relevant", False)

                # Count
                if cls in report["classifications"]:
                    report["classifications"][cls] += 1
                else:
                    report["classifications"]["autre"] += 1

                # Step 2: Store in memory
                record = {
                    "type": "received",
                    "gmail_id": gmail_id,
                    "thread_id": email.get("thread_id", f"thread_{uuid.uuid4().hex[:8]}"),
                    "from_addr": email.get("from_addr", ""),
                    "to": email.get("to", "neuro.link013@gmail.com"),
                    "subject": email.get("subject", ""),
                    "body": email.get("body", "")[:3000],
                    "date": email.get("date", ""),
                    "classification": cls,
                    "is_relevant": is_relevant,
                    "analysis": classification,
                    "target_type": classification.get("target_type", "inconnu"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                memory_id = self.memory.ingest(record)
                record["id"] = memory_id  # ensure record has its id

                email_result: dict[str, Any] = {
                    "gmail_id": gmail_id,
                    "from_addr": email.get("from_addr", ""),
                    "subject": email.get("subject", ""),
                    "classification": cls,
                    "is_relevant": is_relevant,
                    "urgency": classification.get("urgency", "basse"),
                    "action": classification.get("action", "ignorer"),
                    "summary": classification.get("summary", ""),
                    "memory_id": memory_id,
                    "draft_id": None,
                }

                # Step 3: Auto-reply if relevant and action = repondre_auto
                action = classification.get("action", "ignorer")
                if auto_reply and is_relevant and action not in ("ignorer", "archiver"):
                    try:
                        draft = self._auto_reply(record, classification)
                        email_result["draft_id"] = draft.get("id")
                        report["auto_replies_drafted"] += 1
                    except Exception as e:
                        report["errors"].append(
                            f"Auto-reply failed for {gmail_id}: {e}"
                        )

                report["emails"].append(email_result)
                report["newly_processed"] += 1

            except Exception as e:
                report["errors"].append(f"Processing {gmail_id}: {e}")

        return report

    def _auto_reply(
        self, email_record: dict[str, Any], classification: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate an automatic reply draft for a relevant incoming email.

        Uses full memory context + classification to craft an appropriate response.
        The draft is stored but NOT sent — requires admin approval.
        """
        memory_context = self.memory.load_full_context(
            query=f"{email_record.get('from_addr', '')} {email_record.get('subject', '')}"
        )

        contact_history = self.memory.get_by_contact(email_record.get("from_addr", ""))
        history_text = ""
        if contact_history:
            history_text = "\n\n--- HISTORIQUE AVEC CET EXPEDITEUR ---\n"
            for r in contact_history[-5:]:
                history_text += EmailMemory._format_record(r) + "\n"

        target_type = classification.get("target_type", "")
        target_ctx = TARGET_CONTEXT.get(target_type, "")
        tone = classification.get("reply_tone", "professionnel")
        cls = classification.get("classification", "autre")

        user_msg = (
            f"Redige une reponse professionnelle a cet email entrant.\n\n"
            f"EMAIL RECU:\n"
            f"- De: {email_record.get('from_addr', '?')}\n"
            f"- Sujet: {email_record.get('subject', '?')}\n"
            f"- Date: {email_record.get('date', '?')}\n"
            f"- Corps:\n{email_record.get('body', '')[:2000]}\n\n"
            f"CLASSIFICATION: {cls}\n"
            f"TON SUGGERE: {tone}\n"
            f"TYPE DE CONTACT: {target_type}\n\n"
            f"MEMOIRE EMAIL:\n{memory_context}\n{history_text}\n\n"
            f"CONTEXTE CIBLE:\n{target_ctx}\n\n"
            f"REGLES POUR LA REPONSE:\n"
            f"- Remercie pour l'interet porte a Neuro-Link\n"
            f"- Reponds a ses questions / sa demande specifique\n"
            f"- Propose une prochaine etape concrete (demo, appel, docs)\n"
            f"- Signe au nom de Romain Kocupyr, fondateur Neuro-Link\n"
            f"- Ne jamais promettre de diagnostic — c'est un outil d'aide au depistage\n\n"
            f"Reponds en JSON avec les cles: subject, body"
        )

        result = mistral_chat_json(SYSTEM_PROMPT, [{"role": "user", "content": user_msg}])

        draft_id = f"em_{uuid.uuid4().hex[:12]}"
        draft = {
            "id": draft_id,
            "type": "draft",
            "subject": result.get("subject", ""),
            "body": result.get("body", ""),
            "to": email_record.get("from_addr", ""),
            "in_reply_to": email_record.get("id", ""),
            "thread_id": email_record.get("thread_id", f"thread_{uuid.uuid4().hex[:8]}"),
            "target_type": target_type,
            "auto_reply": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.ingest(draft)

        return draft

    def compose(self, instruction: str) -> dict[str, Any]:
        """Free-form email composition from a natural language instruction."""
        memory_context = self.memory.load_full_context(query=instruction)

        user_msg = (
            f"Instruction: {instruction}\n\n"
            f"MEMOIRE EMAIL:\n{memory_context}\n\n"
            f"Reponds en JSON avec les cles: to, subject, body, target_type"
        )

        result = mistral_chat_json(SYSTEM_PROMPT, [{"role": "user", "content": user_msg}])

        draft_id = f"em_{uuid.uuid4().hex[:12]}"
        draft = {
            "id": draft_id,
            "type": "draft",
            "to": result.get("to", ""),
            "subject": result.get("subject", ""),
            "body": result.get("body", ""),
            "target_type": result.get("target_type", ""),
            "thread_id": f"thread_{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.memory.ingest(draft)

        return draft

    # --- Memory query ------------------------------------------------------

    def query_memory(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search email memory semantically."""
        return self.memory.search(query, limit=limit)

    def get_memory_context(self, query: str = "") -> str:
        """Get formatted memory context string."""
        return self.memory.load_full_context(query=query)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="neuro-link-email-ai",
        description="Neuro-Link Email AI Agent (Mistral + FAISS Memory)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # draft
    p = sub.add_parser("draft", help="Draft a prospection email")
    p.add_argument("--type", "-t", required=True,
                   choices=["chu", "ehpad", "neurologue", "investisseur", "partenaire_tech"])
    p.add_argument("--name", "-n", required=True, help="Target name")
    p.add_argument("--info", "-i", default="", help="Additional target info")

    # followup
    p = sub.add_parser("followup", help="Draft a follow-up email")
    p.add_argument("--thread-id", required=True)

    # reply
    p = sub.add_parser("reply", help="Draft a reply to an email")
    p.add_argument("--email-id", required=True)

    # analyze
    p = sub.add_parser("analyze", help="Analyze an incoming email")
    p.add_argument("--from", dest="from_addr", required=True)
    p.add_argument("--subject", "-s", required=True)
    p.add_argument("--body", "-b", required=True)

    # compose
    p = sub.add_parser("compose", help="Free-form AI email composition")
    p.add_argument("--instruction", "-i", required=True)

    # send
    p = sub.add_parser("send", help="Send an approved draft")
    p.add_argument("--draft-id", required=True)

    # memory
    p = sub.add_parser("memory", help="Search email memory")
    p.add_argument("--query", "-q", default="", help="Search query")
    p.add_argument("--limit", "-n", type=int, default=10)

    # inbox (requires gmail_reader)
    sub.add_parser("inbox", help="Fetch and analyze recent inbox")

    args = parser.parse_args()
    agent = EmailAIAgent()

    if args.command == "draft":
        result = agent.draft_prospection(args.type, args.name, args.info)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "followup":
        result = agent.draft_followup(args.thread_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "reply":
        result = agent.draft_reply(args.email_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "analyze":
        email = {
            "from_addr": args.from_addr,
            "subject": args.subject,
            "body": args.body,
        }
        result = agent.analyze_incoming(email)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "compose":
        result = agent.compose(args.instruction)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "send":
        result = agent.send_draft(args.draft_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "memory":
        if args.query:
            results = agent.query_memory(args.query, args.limit)
            for r in results:
                print(EmailMemory._format_record(r))
        else:
            ctx = agent.get_memory_context()
            print(ctx)

    elif args.command == "inbox":
        try:
            from backend.gmail_reader import GmailReader
            reader = GmailReader()
            emails = reader.fetch_recent(max_results=10)
            print(f"  {len(emails)} emails recents:\n")
            for email in emails:
                analysis = agent.analyze_incoming(email)
                print(f"  De: {email.get('from_addr', '?')}")
                print(f"  Sujet: {email.get('subject', '?')}")
                print(f"  Categorie: {analysis.get('category', '?')}")
                print(f"  Urgence: {analysis.get('urgency', '?')}")
                print(f"  Action: {analysis.get('recommended_action', '?')}")
                print(f"  Resume: {analysis.get('summary', '?')}")
                print()
        except ImportError:
            print("Gmail Reader non disponible. Installez google-auth-oauthlib.")
        except Exception as e:
            print(f"Erreur inbox: {e}")


if __name__ == "__main__":
    main()
