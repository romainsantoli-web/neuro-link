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
    "labo_pharma": (
        "Tu ecris a un laboratoire pharmaceutique (ex: Roche, Biogen, Eisai, Eli Lilly, Novo Nordisk). "
        "Accent sur: biomarqueur digital complementaire a leurs molecules anti-amyloide, "
        "screening pre-trial pour enrichir les cohortes d'essais cliniques, "
        "endpoint digital objectif (EEG), reduction du cout de recrutement, "
        "real-world evidence, companion diagnostic potentiel. "
        "Ton formel, scientifique et oriente partenariat strategique."
    ),
    "concurrent_bci": (
        "Tu ecris a un concurrent ou acteur du marche BCI/EEG (ex: OpenBCI, Emotiv, Muse/InteraXon, "
        "Neuroelectrics, g.tec, ANT Neuro, Brain Products, Cognionics). "
        "Accent sur: proposition de collaboration plutot que confrontation, "
        "compatibilite logicielle, marche en croissance pour tous, "
        "complementarite hardware (eux) + IA (nous), co-marketing, "
        "integration native dans notre pipeline. "
        "Ton respectueux, collaboratif et strategique. Ne jamais denigrer leur produit."
    ),
}

# ---------------------------------------------------------------------------
# Tone profiles — detailed discourse guidelines per target type
# ---------------------------------------------------------------------------

TONE_PROFILES = {
    "chu": (
        "TON: Formel, academique, respectueux de la hierarchie hospitaliere.\n"
        "VOUVOIEMENT: Obligatoire. Utiliser les titres (Professeur, Docteur, Madame/Monsieur le Directeur).\n"
        "VOCABULAIRE: Medical et scientifique precis. Mentionner les publications, protocoles ethiques, CPP.\n"
        "STRUCTURE: Introduction institutionnelle > Proposition de valeur clinique > Donnees probantes > "
        "Proposition de RDV/visio avec references.\n"
        "ARGUMENTS CLES: Validation multicentrique, integration DPI (FHIR R4 HL7), precision 99.95%, "
        "protocole non-invasif (EEG), complementarite avec imagerie existante, potentiel de publication.\n"
        "NE PAS: Etre trop commercial, utiliser du jargon startup, promettre un diagnostic.\n"
        "SIGNATURE: Romain Kocupyr, Fondateur & CEO, Neuro-Link | Depistage IA de la maladie d'Alzheimer"
    ),
    "ehpad": (
        "TON: Bienveillant, pratique, rassurant. Empathie pour les residents et les equipes.\n"
        "VOUVOIEMENT: Obligatoire. Adresser le directeur/la directrice, le medecin coordinateur.\n"
        "VOCABULAIRE: Accessible, eviter le jargon technique excessif. Parler de 'residents', "
        "'accompagnement', 'qualite de vie', 'depistage precoce'.\n"
        "STRUCTURE: Accroche humaine > Problematique concr\u00e8te > Solution simple > Impact pour "
        "les residents et familles > Proposition de demonstration.\n"
        "ARGUMENTS CLES: Simplicite d'utilisation, plan gratuit (Free), rapport PDF clair, "
        "depistage non-invasif, tranquillite pour les familles, detection precoce.\n"
        "NE PAS: Etre trop technique, mentionner les prix eleves, parler de 'staging' avance.\n"
        "SIGNATURE: Romain Kocupyr, Fondateur, Neuro-Link | Au service du depistage precoce"
    ),
    "neurologue": (
        "TON: Collegial, entre professionnels de sante. De pair a pair.\n"
        "VOUVOIEMENT: Oui, mais ton plus decontracte que pour un CHU. 'Cher Docteur', 'Cher confrere'.\n"
        "VOCABULAIRE: Technique mais accessible. EEG, biomarqueurs, sensibilite/specificite, "
        "features extraction, Transformer. Montrer la competence technique.\n"
        "STRUCTURE: Accroche par un probleme clinique commun > Solution technique > Donnees de "
        "performance > Compatibilite materiel > Proposition d'essai gratuit.\n"
        "ARGUMENTS CLES: Precision 99.95%, compatible casques existants (OpenBCI, BrainVision), "
        "gain de temps (analyse en minutes), outil d'AIDE (pas de remplacement), export FHIR.\n"
        "NE PAS: Pretendre remplacer le clinicien, etre condescendant, trop 'vendeur'.\n"
        "SIGNATURE: Romain Kocupyr, Fondateur, Neuro-Link | Intelligence Artificielle × Neurologie"
    ),
    "investisseur": (
        "TON: Business, ambitieux, data-driven. Confiant mais pas arrogant.\n"
        "TUTOIEMENT/VOUVOIEMENT: Vouvoiement initial, sauf si l'investisseur tutoie d'abord.\n"
        "VOCABULAIRE: Business/VC: MRR, ARR, TAM/SAM/SOM, runway, traction, moat, defensibilite, "
        "competitive advantage, unit economics.\n"
        "STRUCTURE: Hook percutant (marche/probleme) > Solution unique > Traction/metriques > "
        "Marche ($30Md Alzheimer) > Equipe > Ask clair (montant, utilisation).\n"
        "ARGUMENTS CLES: Marche colossal ($30Md), technologie unique (ADFormerHybrid), "
        "precision inegalee (99.95%), open-source = credibilite, SaaS B2B scalable, "
        "4 plans tarifaires, 118 tests, equipe technique solide.\n"
        "NE PAS: Etre timide sur les chiffres, s'excuser, donner trop de details techniques.\n"
        "SIGNATURE: Romain Kocupyr, Founder & CEO, Neuro-Link | AI-Powered Alzheimer's Screening"
    ),
    "partenaire_tech": (
        "TON: Technique, collaboratif, communaute open-source. Entre ingenieurs/makers.\n"
        "TUTOIEMENT: Acceptable si l'interlocuteur est dans le milieu tech/open-source.\n"
        "VOCABULAIRE: Technique pur: API, SDK, BrainFlow, LSL, UDP, sampling rate, "
        "electrode layout, AGPL v3, pull request, integration.\n"
        "STRUCTURE: Contexte technique commun > Compatibilite existante > Proposition de "
        "collaboration > Benefice mutuel > Repo GitHub.\n"
        "ARGUMENTS CLES: 7 formats EEG supportes, compatibilite native OpenBCI, "
        "open-source AGPL v3, communaute active, integration BrainFlow/LSL, "
        "benefice mutuel (leur materiel + notre IA).\n"
        "NE PAS: Etre trop formel, parler uniquement business, ignorer l'aspect communaute.\n"
        "SIGNATURE: Romain Kocupyr, Founder, Neuro-Link | Open-Source Alzheimer's Detection"
    ),
    "labo_pharma": (
        "TON: Formel, scientifique, oriente partnership strategique. Credibilite maximale.\n"
        "VOUVOIEMENT: Obligatoire. Titres (Docteur, Directeur Medical, VP R&D).\n"
        "VOCABULAIRE: Pharma/biotech: essais cliniques phase II/III, biomarqueur digital, "
        "companion diagnostic, endpoint, enrichissement de cohorte, screening pre-trial, "
        "real-world evidence (RWE), pre-symptomatic, anti-amyloid, anti-tau, "
        "FDA/EMA, CE marking, CRO, DSMB.\n"
        "STRUCTURE: Contexte molecule/pipeline du labo > Probleme de recrutement/screening > "
        "Notre solution comme outil complementaire > Donnees de performance (99.95%) > "
        "Proposition de pilote ou partenariat > Appel a RDV.\n"
        "ARGUMENTS CLES: Biomarqueur digital non-invasif (EEG vs PET/LCR), screening massif "
        "a faible cout pour enrichir les cohortes, precision 99.95%, staging Braak, "
        "compatible FHIR pour interop CRO, detection pre-symptomatique, 4 stades FAST, "
        "potentiel companion diagnostic pour molecules anti-amyloide (Lecanemab, Donanemab, etc).\n"
        "NE PAS: Pretendre remplacer les biomarqueurs existants (PET amyloide, LCR), "
        "promettre une approbation regulatoire, etre trop startup/informel.\n"
        "SIGNATURE: Romain Kocupyr, Founder & CEO, Neuro-Link | AI Biomarker for Alzheimer's"
    ),
    "concurrent_bci": (
        "TON: Respectueux, collaboratif, strategique. D'egal a egal entre acteurs du marche.\n"
        "VOUVOIEMENT: Initial, adaptable selon la culture de l'entreprise.\n"
        "VOCABULAIRE: BCI/neurotechnologie: sampling rate, electrode count, dry/wet electrodes, "
        "impedance, BrainFlow, LSL, EDF+, signal quality, artefact rejection, "
        "FDA 510(k), CE medical, neurofeedback, research-grade.\n"
        "STRUCTURE: Reference a leur produit/expertise > Reconnaissance de leur position marche > "
        "Opportunite de collaboration win-win > Notre IA comme valeur ajoutee pour leur hardware > "
        "Proposition concrete (integration, co-branding, API).\n"
        "ARGUMENTS CLES: Notre IA ajoute de la valeur a LEUR hardware, 7 formats deja supportes, "
        "integration native BrainFlow, marche en croissance pour tous ($5.2Md BCI d'ici 2030), "
        "open-source = compatibilite garantie, co-marketing aupres des chercheurs/cliniciens, "
        "nouveau use case clinique (Alzheimer) qui valorise leur materiel.\n"
        "NE PAS: Denigrer ou comparer negativement leur produit, se positionner comme concurrent, "
        "pretendre que notre solution est superieure a la leur, etre agressif commercialement.\n"
        "SIGNATURE: Romain Kocupyr, Founder, Neuro-Link | Open-Source Alzheimer's Detection × BCI"
    ),
    "default": (
        "TON: Professionnel, courtois, adapte au contexte.\n"
        "VOUVOIEMENT: Par defaut.\n"
        "STRUCTURE: Introduction > Proposition de valeur > Call-to-action.\n"
        "SIGNATURE: Romain Kocupyr, Fondateur, Neuro-Link"
    ),
}


class EmailAIAgent:
    """AI-powered email agent for Neuro-Link."""

    def __init__(self):
        self.memory = EmailMemory()

    # --- Research target (web search) ----------------------------------------

    def research_target(
        self,
        target_name: str,
        target_type: str = "",
        extra_keywords: str = "",
    ) -> dict[str, Any]:
        """Research a company/org/person via web search + scraping.

        Uses DuckDuckGo search and page scraping to gather intelligence
        about a target before drafting a prospection email.
        Results are always saved to memory for future reference.

        Returns:
            Dict with search_results, scraped_pages, research_summary, memory_id
        """
        from backend.web_search import research_company
        data = research_company(
            company_name=target_name,
            company_type=target_type,
            extra_keywords=extra_keywords,
        )

        # Save research to memory so the agent remembers it
        memory_record = {
            "type": "research",
            "target_name": target_name,
            "target_type": target_type,
            "subject": f"Recherche web: {target_name} ({target_type})",
            "body": data.get("research_summary", "")[:3000],
            "research_summary": data.get("research_summary", ""),
            "search_results_count": len(data.get("search_results", [])),
            "scraped_pages_count": len(data.get("scraped_pages", [])),
            "extracted_emails": data.get("extracted_emails", []),
            "extra_keywords": extra_keywords,
        }
        memory_id = self.memory.ingest(memory_record)
        data["memory_id"] = memory_id

        return data

    # --- Draft prospection email -------------------------------------------

    def draft_prospection(
        self,
        target_type: str,
        target_name: str,
        target_info: str = "",
        extra_context: str = "",
        auto_research: bool = True,
    ) -> dict[str, Any]:
        """Draft a prospection email for a specific target.

        Smart pipeline:
        1. Check memory for past research on this target
        2. If no past research (or auto_research), do live web search
        3. Collect all extracted emails from research
        4. Load full contact history from memory
        5. Apply target-type-specific tone profile
        6. Draft email with Mistral AI using all context

        Returns:
            Dict with keys: id, subject, body, to, to_suggestion, target_type,
            target_name, extracted_emails, research
        """
        # 1. Check past research from memory
        past_research = self.memory.get_research_for_target(target_name)
        past_research_text = ""
        if past_research:
            latest = past_research[0]  # most recent
            past_research_text = (
                f"\n\n--- RECHERCHE PRECEDENTE ({latest.get('timestamp', '?')[:16]}) ---\n"
                f"{latest.get('research_summary', '')[:3000]}"
            )

        # 2. Live web research (or re-use past if available)
        research_text = ""
        research_data = None
        if auto_research:
            try:
                research_data = self.research_target(target_name, target_type, target_info)
                research_text = f"\n\nRECHERCHE WEB LIVE:\n{research_data['research_summary'][:4000]}"
            except Exception as e:
                research_text = f"\n\n[Recherche web échouée: {e}]"
        elif past_research_text:
            research_text = past_research_text

        # 3. Collect all extracted emails for this target
        extracted_emails = self.memory.get_all_extracted_emails(target_name)
        if research_data:
            for em in research_data.get("extracted_emails", []):
                if em.lower() not in {e.lower() for e in extracted_emails}:
                    extracted_emails.append(em)

        emails_text = ""
        if extracted_emails:
            emails_text = (
                f"\n\n--- EMAILS EXTRAITS (trouvés lors des recherches web) ---\n"
                + "\n".join(f"  • {em}" for em in extracted_emails)
            )

        # 4. Load full context from memory
        memory_context = self.memory.load_full_context(
            query=f"{target_type} {target_name} prospection"
        )

        # Check all past interactions with this target
        target_history = self.memory.get_by_target_name(target_name)
        contact_history = self.memory.get_by_contact(target_name)
        all_history = {r.get('id'): r for r in target_history + contact_history}
        sorted_history = sorted(all_history.values(), key=lambda r: r.get('timestamp', ''))

        history_text = ""
        if sorted_history:
            history_text = "\n\n--- HISTORIQUE COMPLET AVEC CETTE CIBLE ---\n"
            for r in sorted_history[-8:]:
                history_text += EmailMemory._format_record(r) + "\n"

        # 5. Target-specific tone profile
        target_ctx = TARGET_CONTEXT.get(target_type, "")
        tone_profile = TONE_PROFILES.get(target_type, TONE_PROFILES["default"])

        # 6. Build the prompt
        user_msg = (
            f"Redige un email de prospection pour:\n"
            f"- Destinataire: {target_name}\n"
            f"- Type: {target_type}\n"
            f"- Infos: {target_info}\n"
            f"- Contexte supplementaire: {extra_context}\n\n"
            f"PROFIL DE TON À ADOPTER:\n{tone_profile}\n\n"
            f"MEMOIRE EMAIL:\n{memory_context}\n{history_text}\n\n"
            f"CONTEXTE CIBLE:\n{target_ctx}\n"
            f"{research_text}\n"
            f"{past_research_text if auto_research and past_research_text else ''}\n"
            f"{emails_text}\n\n"
            f"INSTRUCTIONS CRITIQUES:\n"
            f"1. Utilise les informations de la recherche web pour personnaliser "
            f"l'email. Mentionne des details concrets (projets, equipes, actualites) "
            f"pour montrer que tu connais leur travail.\n"
            f"2. Si des emails ont ete extraits, propose le plus pertinent comme destinataire.\n"
            f"3. Adapte STRICTEMENT le ton au profil indique ci-dessus.\n"
            f"4. Si un historique existe, fais reference aux echanges precedents.\n"
            f"5. Inclus un call-to-action clair et specifique.\n"
            f"6. Sign\u00e9 par Romain Kocupyr, Fondateur de Neuro-Link.\n\n"
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

        # Attach research data + extracted emails
        draft["extracted_emails"] = extracted_emails
        if research_data:
            draft["research"] = {
                "search_results": research_data.get("search_results", [])[:6],
                "scraped_pages": research_data.get("scraped_pages", []),
                "memory_id": research_data.get("memory_id", ""),
            }

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

    def process_inbox(self, max_emails: int = 20, auto_reply: bool = True, auto_send: bool = False) -> dict[str, Any]:
        """Process inbox: classify all emails, auto-reply to relevant ones.

        Full pipeline:
        1. Fetch recent emails from Gmail
        2. Skip already-processed emails (check memory by gmail_id)
        3. Classify each email (spam/pub/pro/etc.)
        4. Store relevant emails in memory
        5. Auto-draft replies for professional emails
        6. If auto_send=True, send the drafted replies immediately
        7. Return full processing report

        Args:
            max_emails: Max emails to fetch from Gmail
            auto_reply: Whether to auto-draft replies for relevant emails
            auto_send: Whether to auto-send drafted replies (requires auto_reply=True)

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
            "auto_replies_sent": 0,
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
                        draft_id = draft.get("id")
                        email_result["draft_id"] = draft_id
                        report["auto_replies_drafted"] += 1

                        # Auto-send if enabled
                        if auto_send and draft_id:
                            try:
                                send_result = self.send_draft(draft_id, approve=True)
                                email_result["sent"] = True
                                email_result["resend_id"] = send_result.get("resend_id", "")
                                report["auto_replies_sent"] += 1
                            except Exception as se:
                                email_result["sent"] = False
                                report["errors"].append(
                                    f"Auto-send failed for {gmail_id}: {se}"
                                )
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
