"""Neuro-Link — Gemini AI Report Generator avec fallback multi-modèles.

Chaîne de fallback automatique du modèle le plus performant au plus léger,
avec compteur de tokens et suivi des quotas par modèle.

Modèles gratuits disponibles (février 2026) :
  1. gemini-3-flash-preview  — 5 RPM, 250K TPM, 20 RPD
  2. gemini-2.5-flash        — 5 RPM, 250K TPM, 20 RPD
  3. gemini-2.5-flash-lite   — 10 RPM, 250K TPM, 20 RPD
  4. gemma-3-27b-it          — 30 RPM, 15K TPM, 14.4K RPD
  5. gemma-3-12b-it          — 30 RPM, 15K TPM, 14.4K RPD

Docs : https://ai.google.dev/gemini-api/docs
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger('neuro-link.gemini')

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
GEMINI_BASE = 'https://generativelanguage.googleapis.com/v1beta/models'
TIMEOUT = httpx.Timeout(60.0, connect=10.0)


# ═══════════ Modèles & Quotas ═══════════

@dataclass
class ModelQuota:
    """Quota tier gratuit pour un modèle Gemini."""
    name: str               # identifiant API
    rpm: int                 # requêtes par minute
    tpm: int                 # tokens par minute
    rpd: int                 # requêtes par jour
    max_output_tokens: int = 2048


# Chaîne de fallback : du plus performant au plus léger
MODELS: list[ModelQuota] = [
    ModelQuota('gemini-3-flash-preview',  rpm=5,  tpm=250_000, rpd=20),
    ModelQuota('gemini-2.5-flash',        rpm=5,  tpm=250_000, rpd=20),
    ModelQuota('gemini-2.5-flash-lite',   rpm=10, tpm=250_000, rpd=20),
    ModelQuota('gemma-3-27b-it',          rpm=30, tpm=15_000,  rpd=14_400),
    ModelQuota('gemma-3-12b-it',          rpm=30, tpm=15_000,  rpd=14_400),
]


# ═══════════ Compteur de tokens ═══════════

def estimate_tokens(text: str) -> int:
    """Estimation rapide du nombre de tokens.

    Règle empirique pour le français :
      ~1 token ≈ 3.5 caractères (un peu plus dense que l'anglais).
    On ajoute une marge de 10% pour la sécurité.
    """
    return int(len(text) / 3.5 * 1.1)


# ═══════════ Suivi des quotas ═══════════

@dataclass
class _UsageWindow:
    """Fenêtre glissante pour le suivi des requêtes et tokens."""
    timestamps: list[float] = field(default_factory=list)
    token_counts: list[tuple[float, int]] = field(default_factory=list)
    daily_count: int = 0
    daily_reset: float = 0.0


_lock = threading.Lock()
_usage: dict[str, _UsageWindow] = {}


def _get_usage(model: str) -> _UsageWindow:
    if model not in _usage:
        _usage[model] = _UsageWindow()
    return _usage[model]


def _can_use_model(model: ModelQuota, estimated_tokens: int) -> bool:
    """Vérifie si le modèle a encore du quota disponible."""
    now = time.time()
    with _lock:
        u = _get_usage(model.name)

        # Reset quotas journaliers à minuit
        if now - u.daily_reset > 86400:
            u.daily_count = 0
            u.daily_reset = now

        # RPD check
        if u.daily_count >= model.rpd:
            return False

        # RPM check — nettoyer les timestamps > 60s
        cutoff_1m = now - 60
        u.timestamps = [t for t in u.timestamps if t > cutoff_1m]
        if len(u.timestamps) >= model.rpm:
            return False

        # TPM check — nettoyer les tokens > 60s
        u.token_counts = [(t, c) for t, c in u.token_counts if t > cutoff_1m]
        tokens_used = sum(c for _, c in u.token_counts)
        if tokens_used + estimated_tokens > model.tpm:
            return False

    return True


def _record_usage(model_name: str, tokens: int) -> None:
    """Enregistre l'utilisation après un appel réussi."""
    now = time.time()
    with _lock:
        u = _get_usage(model_name)
        u.timestamps.append(now)
        u.token_counts.append((now, tokens))
        u.daily_count += 1


def get_usage_stats() -> dict[str, Any]:
    """Retourne les statistiques d'utilisation (pour /metrics)."""
    now = time.time()
    stats: dict[str, Any] = {}
    with _lock:
        for name, u in _usage.items():
            cutoff = now - 60
            rpm_used = len([t for t in u.timestamps if t > cutoff])
            tpm_used = sum(c for t, c in u.token_counts if t > cutoff)
            stats[name] = {
                'rpm_used': rpm_used,
                'tpm_used': tpm_used,
                'rpd_used': u.daily_count,
            }
    return stats


# ═══════════ Prompts ═══════════

SYSTEM_PROMPT = """\
Tu es un neurologue expérimenté et chercheur en neurosciences spécialisé dans \
la maladie d'Alzheimer. Tu rédiges des rapports EEG clairs, professionnels et \
compréhensibles par des patients, familles et médecins non spécialistes.

RÈGLES STRICTES :
1. Rédige TOUJOURS en français.
2. Utilise un ton professionnel mais accessible — pas de jargon non expliqué.
3. Structure le rapport avec des sections claires (titres en majuscules).
4. Inclus les marqueurs [IMAGE_XAI] et [IMAGE_QR] à la fin du rapport, \
   chacun sur sa propre ligne, pour l'intégration des visualisations dans le frontend.
5. Ajoute TOUJOURS un avertissement en fin de rapport : cet outil est expérimental \
   et ne remplace pas un diagnostic médical professionnel.
6. Ne fabrique JAMAIS de données. Utilise uniquement les résultats fournis.
7. Si le résultat est "NORMAL" ou "CN", rassure le patient tout en recommandant un suivi.
8. Si le résultat est "ALZHEIMER" ou "AD", sois empathique, factuel et encourage \
   la consultation d'un spécialiste.
9. Mentionne le niveau de confiance de manière compréhensible.
10. Le rapport doit faire entre 300 et 600 mots.
"""

USER_PROMPT_TEMPLATE = """\
Voici les résultats de l'analyse EEG par le système Neuro-Link v18 \
(modèle ADFormerHybrid, ensemble de 5 modèles, architecture Transformer hybride).

RÉSULTATS :
- Statut du dépistage : {status}
- Stade identifié : {stage}
- Niveau de confiance : {confidence_pct:.1f}%
- Date de l'analyse : {date}

CARACTÉRISTIQUES EEG EXTRAITES :
{features_text}

RAPPORT BRUT DU PIPELINE :
{raw_report}

---
Rédige maintenant un rapport médical professionnel et compréhensible \
à partir de ces résultats. Utilise la structure suivante :

1. EN-TÊTE (titre, date, identifiant)
2. RÉSUMÉ EXÉCUTIF (2-3 phrases)
3. ANALYSE DÉTAILLÉE (interprétation des biomarqueurs EEG)
4. CONCLUSION ET RECOMMANDATIONS
5. [IMAGE_XAI]
6. [IMAGE_QR]
7. AVERTISSEMENT LÉGAL
"""


def _format_features(features: dict[str, Any]) -> str:
    """Format features dict into readable bullet list."""
    if not features:
        return '  (aucune caractéristique disponible)'
    lines = []
    for key, val in features.items():
        if isinstance(val, float):
            lines.append(f'  • {key} : {val:.4f}')
        else:
            lines.append(f'  • {key} : {val}')
    return '\n'.join(lines)


# ═══════════ Appel API ═══════════

async def _call_model(model: ModelQuota, prompt_text: str) -> str | None:
    """Appelle un modèle spécifique. Retourne le texte ou None."""
    url = f'{GEMINI_BASE}/{model.name}:generateContent'

    payload = {
        'contents': [
            {
                'role': 'user',
                'parts': [{'text': prompt_text}],
            }
        ],
        'generationConfig': {
            'temperature': 0.4,
            'topP': 0.9,
            'maxOutputTokens': model.max_output_tokens,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                url,
                params={'key': GEMINI_API_KEY},
                json=payload,
                headers={'Content-Type': 'application/json'},
            )

        if resp.status_code == 429:
            logger.warning('[%s] Rate limited (429) — trying next model', model.name)
            return None

        if resp.status_code == 404:
            logger.warning('[%s] Model not found (404) — trying next model', model.name)
            return None

        if resp.status_code != 200:
            logger.error('[%s] API error %d: %s', model.name, resp.status_code, resp.text[:300])
            return None

        data = resp.json()
        candidates = data.get('candidates', [])
        if not candidates:
            logger.warning('[%s] No candidates returned', model.name)
            return None

        parts = candidates[0].get('content', {}).get('parts', [])
        if not parts:
            return None

        text = parts[0].get('text', '')
        if text:
            output_tokens = estimate_tokens(text)
            _record_usage(model.name, estimate_tokens(prompt_text) + output_tokens)
            logger.info(
                '[%s] ✓ Report generated (%d chars, ~%d tokens)',
                model.name, len(text), output_tokens,
            )
        return text or None

    except httpx.TimeoutException:
        logger.error('[%s] Timeout after 60s', model.name)
        return None
    except Exception as e:
        logger.error('[%s] Unexpected error: %s', model.name, e)
        return None


# ═══════════ Fonction principale avec fallback ═══════════

async def generate_gemini_report(
    status: str,
    stage: str,
    confidence: float,
    features: dict[str, Any],
    raw_report: str,
) -> str | None:
    """Génère un rapport professionnel via Gemini avec fallback multi-modèles.

    Parcourt la chaîne de modèles du plus performant au plus léger.
    Vérifie les quotas avant chaque tentative.
    Retourne None si tous les modèles sont épuisés (le pipeline utilisera
    le rapport brut comme fallback).
    """
    if not GEMINI_API_KEY:
        logger.warning('GEMINI_API_KEY not set — skipping AI report generation')
        return None

    now = datetime.now()

    user_prompt = USER_PROMPT_TEMPLATE.format(
        status=status,
        stage=stage,
        confidence_pct=confidence * 100 if confidence <= 1 else confidence,
        date=now.strftime('%d/%m/%Y à %H:%M'),
        features_text=_format_features(features),
        raw_report=raw_report[:3000] if raw_report else '(aucun rapport brut)',
    )

    full_prompt = f'{SYSTEM_PROMPT}\n\n{user_prompt}'
    input_tokens = estimate_tokens(full_prompt)

    logger.info('Prompt: %d chars, ~%d tokens estimés', len(full_prompt), input_tokens)

    # Parcourir la chaîne de fallback
    for model in MODELS:
        if not _can_use_model(model, input_tokens + model.max_output_tokens):
            logger.info('[%s] Quota insuffisant — skip', model.name)
            continue

        logger.info('[%s] Tentative de génération...', model.name)
        result = await _call_model(model, full_prompt)

        if result:
            return result

        # Si 429 ou erreur, on continue au modèle suivant

    logger.warning('Tous les modèles Gemini épuisés — fallback rapport brut')
    return None
