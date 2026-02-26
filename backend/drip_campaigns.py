"""
Neuro-Link Drip Campaigns — automated email sequences.

Campaign definitions are stored in backend/data/campaigns/ as JSON files.
Tracking state lives in backend/data/campaign_tracker.jsonl.

Each campaign step uses the EmailAIAgent to generate personalized content
based on the full memory context.

Usage (CLI):
    python -m backend.drip_campaigns list
    python -m backend.drip_campaigns start --campaign=prospection_chu --to="dr.martin@chu-montpellier.fr" --name="CHU Montpellier"
    python -m backend.drip_campaigns status
    python -m backend.drip_campaigns check    # process due emails (cron)

Usage (Python):
    from backend.drip_campaigns import CampaignManager
    mgr = CampaignManager()
    mgr.start_campaign("prospection_chu", "dr.martin@chu.fr", "CHU Montpellier")
    mgr.check_and_send_due()  # call from cron or scheduler
"""

from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"
CAMPAIGNS_DIR = DATA_DIR / "campaigns"
TRACKER_FILE = DATA_DIR / "campaign_tracker.jsonl"

# ---------------------------------------------------------------------------
# Built-in campaign templates
# ---------------------------------------------------------------------------

BUILTIN_CAMPAIGNS = {
    "prospection_chu": {
        "name": "Prospection CHU",
        "target_type": "chu",
        "steps": [
            {"day": 0, "type": "intro", "instruction": "Email d'introduction: presenter Neuro-Link, precision 99.95%, integration DPI FHIR, proposer une demo."},
            {"day": 3, "type": "relance_1", "instruction": "Premiere relance douce: rappeler l'email precedent, ajouter un argument sur la validation clinique et l'open-source."},
            {"day": 7, "type": "valeur", "instruction": "Email de valeur ajoutee: partager un cas d'usage concret (pipeline EEG -> diagnostic), mentionner la compatibilite OpenBCI."},
            {"day": 14, "type": "demo", "instruction": "Proposition concrete de demo: proposer un creneau pour une demonstration en visio, rappeler que c'est gratuit et sans engagement."},
            {"day": 21, "type": "dernier", "instruction": "Dernier email de la sequence: remercier, laisser la porte ouverte, donner les coordonnees directes de Romain."},
        ],
    },
    "prospection_ehpad": {
        "name": "Prospection EHPAD",
        "target_type": "ehpad",
        "steps": [
            {"day": 0, "type": "intro", "instruction": "Email d'introduction pour EHPAD: depistage precoce Alzheimer simple et accessible, plan gratuit disponible."},
            {"day": 4, "type": "relance_1", "instruction": "Relance: accent sur la simplicite (upload fichier EEG -> rapport en 7 secondes), pas besoin d'expertise technique."},
            {"day": 10, "type": "temoignage", "instruction": "Email avec argumentaire: benefices pour les residents et les familles, rapport PDF comprehensible par le medecin coordinateur."},
            {"day": 18, "type": "demo", "instruction": "Proposition de demo ou essai gratuit: accompagnement personnalise pour la premiere utilisation."},
        ],
    },
    "prospection_neurologue": {
        "name": "Prospection Neurologue",
        "target_type": "neurologue",
        "steps": [
            {"day": 0, "type": "intro", "instruction": "Email collegial: outil d'aide au diagnostic, compatible avec leur casque EEG, precision 99.95%, export FHIR."},
            {"day": 5, "type": "technique", "instruction": "Email technique: architecture ADFormerHybrid, 267 features, ensemble voting, article preprint disponible."},
            {"day": 12, "type": "demo", "instruction": "Proposition de test: essai gratuit avec un fichier EEG anonymise, support technique inclus."},
        ],
    },
    "prospection_investisseur": {
        "name": "Prospection Investisseur",
        "target_type": "investisseur",
        "steps": [
            {"day": 0, "type": "pitch", "instruction": "Email pitch: marche Alzheimer $30Md, technologie unique (99.95%), open-source pour credibilite, SaaS B2B, equipe."},
            {"day": 5, "type": "metriques", "instruction": "Email metriques: 118 tests, 7 formats EEG, 4 plans tarifaires, pipeline technique, export FHIR, compatibilite OpenBCI."},
            {"day": 10, "type": "call", "instruction": "Proposition d'appel: proposer un call de 30min pour presenter la vision et le business model."},
        ],
    },
    "partenariat_tech": {
        "name": "Partenariat Tech",
        "target_type": "partenaire_tech",
        "steps": [
            {"day": 0, "type": "proposition", "instruction": "Email de proposition de partenariat: compatibilite native, open-source, communaute, benefice mutuel."},
            {"day": 5, "type": "technique", "instruction": "Details techniques: integration BrainFlow/LSL/UDP, support 3 boards, contribution open-source possible."},
            {"day": 12, "type": "next_steps", "instruction": "Prochaines etapes concretes: proposer un appel technique, co-marketing, integration dans la doc."},
        ],
    },
}


def _ensure_campaigns_dir():
    """Write built-in campaigns to disk if not already present."""
    CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)
    for cid, campaign in BUILTIN_CAMPAIGNS.items():
        path = CAMPAIGNS_DIR / f"{cid}.json"
        if not path.exists():
            path.write_text(json.dumps(campaign, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_campaign(campaign_id: str) -> dict[str, Any]:
    """Load a campaign definition."""
    _ensure_campaigns_dir()
    path = CAMPAIGNS_DIR / f"{campaign_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if campaign_id in BUILTIN_CAMPAIGNS:
        return BUILTIN_CAMPAIGNS[campaign_id]
    raise FileNotFoundError(f"Campagne '{campaign_id}' introuvable.")


def _load_tracker() -> list[dict[str, Any]]:
    """Load all campaign tracking entries."""
    if not TRACKER_FILE.exists():
        return []
    entries = []
    with open(TRACKER_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def _append_tracker(entry: dict[str, Any]):
    """Append a tracker entry."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(TRACKER_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class CampaignManager:
    """Manage drip email campaigns."""

    def list_campaigns(self) -> list[dict[str, Any]]:
        """List all available campaign templates."""
        _ensure_campaigns_dir()
        campaigns = []
        for cid, c in BUILTIN_CAMPAIGNS.items():
            campaigns.append({
                "id": cid,
                "name": c["name"],
                "target_type": c["target_type"],
                "steps": len(c["steps"]),
            })
        return campaigns

    def start_campaign(
        self,
        campaign_id: str,
        to: str,
        target_name: str,
        target_info: str = "",
    ) -> dict[str, Any]:
        """Start a new campaign for a specific contact."""
        campaign = _load_campaign(campaign_id)
        instance_id = f"camp_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)

        tracker_entry = {
            "instance_id": instance_id,
            "campaign_id": campaign_id,
            "campaign_name": campaign.get("name", ""),
            "to": to,
            "target_name": target_name,
            "target_type": campaign.get("target_type", ""),
            "target_info": target_info,
            "started_at": now.isoformat(),
            "current_step": 0,
            "total_steps": len(campaign.get("steps", [])),
            "status": "active",
            "steps_completed": [],
        }
        _append_tracker(tracker_entry)

        # Immediately process step 0 (day 0)
        self._process_step(tracker_entry, campaign)

        return tracker_entry

    def get_active_campaigns(self) -> list[dict[str, Any]]:
        """Get all active campaign instances."""
        entries = _load_tracker()
        # Deduplicate by instance_id (keep latest)
        by_id: dict[str, dict[str, Any]] = {}
        for e in entries:
            iid = e.get("instance_id", "")
            if iid:
                by_id[iid] = e
        return [e for e in by_id.values() if e.get("status") == "active"]

    def get_all_campaigns_status(self) -> list[dict[str, Any]]:
        """Get status of all campaign instances."""
        entries = _load_tracker()
        by_id: dict[str, dict[str, Any]] = {}
        for e in entries:
            iid = e.get("instance_id", "")
            if iid:
                by_id[iid] = e
        return list(by_id.values())

    def check_and_send_due(self) -> list[dict[str, Any]]:
        """Check all active campaigns and send any steps that are due.

        Should be called periodically (e.g., by cron every hour).
        Returns list of processed steps.
        """
        active = self.get_active_campaigns()
        processed = []
        now = datetime.now(timezone.utc)

        for instance in active:
            campaign_id = instance.get("campaign_id", "")
            try:
                campaign = _load_campaign(campaign_id)
            except FileNotFoundError:
                continue

            steps = campaign.get("steps", [])
            current = instance.get("current_step", 0)
            started = datetime.fromisoformat(instance["started_at"])

            if current >= len(steps):
                # Campaign complete
                instance["status"] = "completed"
                _append_tracker(instance)
                continue

            step = steps[current]
            due_date = started + timedelta(days=step.get("day", 0))

            if now >= due_date:
                result = self._process_step(instance, campaign)
                if result:
                    processed.append(result)

        return processed

    def _process_step(
        self, instance: dict[str, Any], campaign: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Process a single campaign step: draft + store."""
        steps = campaign.get("steps", [])
        current = instance.get("current_step", 0)

        if current >= len(steps):
            return None

        step = steps[current]

        from backend.email_ai_agent import EmailAIAgent

        agent = EmailAIAgent()
        draft = agent.draft_prospection(
            target_type=instance.get("target_type", campaign.get("target_type", "")),
            target_name=instance.get("target_name", ""),
            target_info=instance.get("target_info", ""),
            extra_context=(
                f"Ceci est l'etape {current + 1}/{len(steps)} de la campagne "
                f"'{campaign.get('name', '')}'. "
                f"Type d'etape: {step.get('type', '')}. "
                f"Instruction specifique: {step.get('instruction', '')}"
            ),
        )

        # Update campaign_id on the draft in memory
        draft["campaign_id"] = instance.get("instance_id", "")

        # Update tracker
        instance["current_step"] = current + 1
        instance["steps_completed"] = instance.get("steps_completed", []) + [{
            "step": current,
            "type": step.get("type", ""),
            "draft_id": draft.get("id", ""),
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }]

        if instance["current_step"] >= len(steps):
            instance["status"] = "completed"

        _append_tracker(instance)

        return {
            "instance_id": instance.get("instance_id", ""),
            "step": current,
            "step_type": step.get("type", ""),
            "draft_id": draft.get("id", ""),
            "to": instance.get("to", ""),
            "subject": draft.get("subject", ""),
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="neuro-link-campaigns",
        description="Neuro-Link Drip Campaigns",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List available campaign templates")

    p = sub.add_parser("start", help="Start a new campaign")
    p.add_argument("--campaign", "-c", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--name", "-n", required=True)
    p.add_argument("--info", "-i", default="")

    sub.add_parser("status", help="Show all campaigns status")
    sub.add_parser("check", help="Process due campaign emails (cron)")

    args = parser.parse_args()
    mgr = CampaignManager()

    if args.command == "list":
        campaigns = mgr.list_campaigns()
        for c in campaigns:
            print(f"  {c['id']}: {c['name']} ({c['steps']} steps, target: {c['target_type']})")

    elif args.command == "start":
        result = mgr.start_campaign(args.campaign, args.to, args.name, args.info)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "status":
        statuses = mgr.get_all_campaigns_status()
        for s in statuses:
            steps_done = len(s.get("steps_completed", []))
            total = s.get("total_steps", 0)
            print(
                f"  [{s.get('status', '?').upper()}] {s.get('campaign_name', '?')} "
                f"-> {s.get('to', '?')} ({steps_done}/{total} steps)"
            )

    elif args.command == "check":
        processed = mgr.check_and_send_due()
        if processed:
            for p_item in processed:
                print(
                    f"  Processed: {p_item.get('step_type', '?')} "
                    f"-> {p_item.get('to', '?')} "
                    f"(draft: {p_item.get('draft_id', '?')})"
                )
        else:
            print("  Aucune etape due pour le moment.")


if __name__ == "__main__":
    main()
