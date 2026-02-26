"""Neuro-Link — Chatbot IA médical via Gemini (fallback multi-modèles).

Permet à l'utilisateur de poser des questions sur le processus d'analyse EEG,
les résultats, et d'être accompagné pendant toute la procédure.
Réutilise la chaîne de fallback et le système de quotas de gemini_report.py.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.gemini_report import (
    GEMINI_API_KEY,
    GEMINI_BASE,
    MODELS,
    TIMEOUT,
    ModelQuota,
    _can_use_model,
    _record_usage,
    estimate_tokens,
)

logger = logging.getLogger('neuro-link.chatbot')

# ═══════════ System prompt du chatbot ═══════════

CHATBOT_SYSTEM_PROMPT = """\
Tu es l'assistant IA de Neuro-Link, une plateforme de dépistage de la maladie \
d'Alzheimer par analyse d'électroencéphalogramme (EEG).

Ton rôle :
• Accompagner l'utilisateur à chaque étape du processus (upload, analyse, résultats)
• Expliquer les résultats de manière claire et accessible, sans jargon inutile
• Répondre aux questions sur l'EEG, les biomarqueurs, la maladie d'Alzheimer
• Rassurer l'utilisateur et l'orienter vers un professionnel de santé si nécessaire
• Rester professionnel, bienveillant et empathique

Règles strictes :
1. Tu ne poses JAMAIS de diagnostic médical définitif — tu expliques les résultats du modèle IA
2. Tu recommandes TOUJOURS de consulter un neurologue pour confirmer
3. Tu réponds en français sauf si l'utilisateur écrit dans une autre langue
4. Tu restes concis (3-8 phrases max par réponse)
5. Si tu ne sais pas, dis-le honnêtement

Tu peux recevoir un contexte d'analyse (résultats, features, rapport) pour personnaliser tes réponses.
"""


# ═══════════ Appel API chat ═══════════

async def _call_chat_model(
    model: ModelQuota,
    messages: list[dict[str, Any]],
) -> str | None:
    """Appel un modèle pour le chat. Retourne le texte ou None."""
    url = f'{GEMINI_BASE}/{model.name}:generateContent'

    # Convertit les messages au format Gemini contents
    contents: list[dict[str, Any]] = []
    for msg in messages:
        role = 'user' if msg['role'] == 'user' else 'model'
        contents.append({
            'role': role,
            'parts': [{'text': msg['content']}],
        })

    payload = {
        'systemInstruction': {
            'parts': [{'text': CHATBOT_SYSTEM_PROMPT}],
        },
        'contents': contents,
        'generationConfig': {
            'temperature': 0.6,
            'topP': 0.9,
            'maxOutputTokens': 1024,
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
            logger.warning('[chat][%s] Rate limited (429)', model.name)
            return None
        if resp.status_code == 404:
            logger.warning('[chat][%s] Model not found (404)', model.name)
            return None
        if resp.status_code != 200:
            logger.error('[chat][%s] API error %d: %s', model.name, resp.status_code, resp.text[:300])
            return None

        data = resp.json()
        candidates = data.get('candidates', [])
        if not candidates:
            logger.warning('[chat][%s] No candidates', model.name)
            return None

        parts = candidates[0].get('content', {}).get('parts', [])
        text = parts[0].get('text', '').strip() if parts else ''

        if text:
            total_input = sum(estimate_tokens(m['content']) for m in messages)
            total_input += estimate_tokens(CHATBOT_SYSTEM_PROMPT)
            output_tokens = estimate_tokens(text)
            _record_usage(model.name, total_input + output_tokens)
            logger.info('[chat][%s] Response: %d chars, ~%d tokens', model.name, len(text), output_tokens)

        return text or None

    except httpx.TimeoutException:
        logger.error('[chat][%s] Timeout', model.name)
        return None
    except Exception as e:
        logger.error('[chat][%s] Error: %s', model.name, e)
        return None


# ═══════════ Fonction principale ═══════════

async def chat_with_gemini(
    messages: list[dict[str, str]],
    analysis_context: dict[str, Any] | None = None,
) -> str:
    """Envoie un message au chatbot Gemini avec fallback multi-modèles.

    Args:
        messages: Historique de la conversation [{"role": "user"|"assistant", "content": "..."}]
        analysis_context: Résultats d'analyse optionnels pour contextualiser les réponses

    Returns:
        Réponse du chatbot (str). Retourne un message d'erreur gracieux si tous les modèles échouent.
    """
    if not GEMINI_API_KEY:
        return ("Je suis temporairement indisponible car la clé API n'est pas configurée. "
                "Vous pouvez toujours utiliser l'analyse EEG normalement.")

    # Injecter le contexte d'analyse dans le premier message si disponible
    enriched_messages = list(messages)
    if analysis_context and enriched_messages:
        ctx_parts = []
        if analysis_context.get('status'):
            ctx_parts.append(f"Statut: {analysis_context['status']}")
        if analysis_context.get('stage'):
            ctx_parts.append(f"Stade: {analysis_context['stage']}")
        if analysis_context.get('confidence') is not None:
            conf = analysis_context['confidence']
            ctx_parts.append(f"Confiance: {conf * 100 if conf <= 1 else conf:.1f}%")
        if analysis_context.get('features'):
            feats = ', '.join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
                              for k, v in analysis_context['features'].items())
            ctx_parts.append(f"Features: {feats}")
        if analysis_context.get('report'):
            ctx_parts.append(f"Rapport: {analysis_context['report'][:1500]}")

        if ctx_parts:
            context_block = (
                "[CONTEXTE D'ANALYSE EN COURS]\n" + '\n'.join(ctx_parts) + "\n[FIN CONTEXTE]\n\n"
            )
            # Prepend context to the latest user message
            last_msg = enriched_messages[-1]
            if last_msg['role'] == 'user':
                enriched_messages[-1] = {
                    'role': 'user',
                    'content': context_block + last_msg['content'],
                }

    # Estimer les tokens de l'ensemble de la conversation
    total_tokens = estimate_tokens(CHATBOT_SYSTEM_PROMPT)
    for m in enriched_messages:
        total_tokens += estimate_tokens(m['content'])

    # Parcourir la chaîne de fallback
    for model in MODELS:
        needed = total_tokens + 1024  # max_output_tokens
        if not _can_use_model(model, needed):
            logger.info('[chat][%s] Quota insuffisant — skip', model.name)
            continue

        logger.info('[chat][%s] Tentative...', model.name)
        result = await _call_chat_model(model, enriched_messages)
        if result:
            return result

    # Tous les modèles épuisés
    return ("Je suis momentanément surchargé. Votre analyse EEG fonctionne normalement — "
            "seul l'assistant conversationnel est temporairement indisponible. "
            "Réessayez dans quelques minutes.")
