from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parents[1]
PIPELINE_SCRIPT = ROOT_DIR / 'alz-finis' / 'run_pipeline.py'
PIPELINE_OUTPUT_DIR = ROOT_DIR / 'backend' / 'runs'
MEMORY_FILE = ROOT_DIR / 'backend' / 'data' / 'memory_records.jsonl'
PROJECT_MEMORY_FILE = ROOT_DIR / 'backend' / 'data' / 'project_memory.jsonl'

ALLOWED_EXTENSIONS = {'.set', '.edf', '.bdf', '.vhdr', '.fif', '.csv', '.txt'}
MAX_UPLOAD_BYTES = int(os.getenv('MAX_UPLOAD_BYTES', str(100 * 1024 * 1024)))
MAX_CONTEXT_LENGTH = int(os.getenv('MAX_CONTEXT_LENGTH', '12000'))
SECURITY_BEARER_TOKEN = os.getenv('SECURITY_BEARER_TOKEN', '').strip()
SECURITY_STRICT_MODE = os.getenv('SECURITY_STRICT_MODE', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}

REQUESTS_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
BLOCK_DURATION_SECONDS = int(os.getenv('RATE_LIMIT_BLOCK_SECONDS', '600'))

_rate_lock = threading.Lock()
_request_windows: dict[str, deque[float]] = defaultdict(deque)
_blocked_until: dict[str, float] = {}
_violations: dict[str, int] = defaultdict(int)

PIPELINE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title='Neuro-Link API', version='0.1.0')

from backend.monitoring import record_request, get_metrics_snapshot, record_page_view, get_page_analytics, logger as mon_logger
from backend.api_keys import (
    generate_api_key,
    validate_key,
    check_quota,
    record_usage,
    get_usage,
    list_keys,
    get_key_by_id,
    update_key,
    revoke_key,
    delete_key,
    get_all_usage_summary,
    PLANS,
)

ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', '').strip()

cors_origins_env = os.getenv('CORS_ALLOW_ORIGINS', '*').strip()
if SECURITY_STRICT_MODE and cors_origins_env == '*':
    cors_origins = ['http://localhost:3000']
else:
    cors_origins = ['*'] if cors_origins_env == '*' else [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]

if SECURITY_STRICT_MODE and not SECURITY_BEARER_TOKEN:
    raise RuntimeError('SECURITY_STRICT_MODE requires SECURITY_BEARER_TOKEN to be set')

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=['*'],
    allow_headers=['*'],
)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get('x-forwarded-for', '').split(',')[0].strip()
    if forwarded:
        return forwarded
    if request.client and request.client.host:
        return request.client.host
    return 'unknown'


def _register_violation(ip: str, weight: int = 1) -> None:
    with _rate_lock:
        _violations[ip] += weight
        if _violations[ip] >= 5:
            _blocked_until[ip] = time.time() + BLOCK_DURATION_SECONDS


def _is_blocked(ip: str) -> bool:
    with _rate_lock:
        blocked_until = _blocked_until.get(ip)
        if not blocked_until:
            return False
        if time.time() >= blocked_until:
            _blocked_until.pop(ip, None)
            _violations.pop(ip, None)
            return False
        return True


def _check_rate_limit(ip: str) -> bool:
    now = time.time()
    with _rate_lock:
        window = _request_windows[ip]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= REQUESTS_PER_MINUTE:
            _violations[ip] += 1
            if _violations[ip] >= 3:
                _blocked_until[ip] = time.time() + BLOCK_DURATION_SECONDS
            return False
        window.append(now)
    return True


def _looks_malicious(text: str) -> bool:
    patterns = [
        r'\b(select|union|drop|insert|delete|update)\b',
        r'<script',
        r'\.\./',
        r'\b(wget|curl|bash\s+-c|powershell)\b',
    ]
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in patterns)


def _require_auth_if_enabled(request: Request) -> None:
    if not SECURITY_BEARER_TOKEN and not SECURITY_STRICT_MODE:
        return
    auth = request.headers.get('authorization', '')
    expected = f'Bearer {SECURITY_BEARER_TOKEN}'
    if auth != expected:
        _register_violation(_client_ip(request), weight=2)
        raise HTTPException(status_code=401, detail='Unauthorized')


def _require_admin(request: Request) -> None:
    """Require ADMIN_TOKEN for admin routes."""
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail='Admin API not configured (set ADMIN_TOKEN env var)')
    auth = request.headers.get('authorization', '')
    if auth != f'Bearer {ADMIN_TOKEN}':
        _register_violation(_client_ip(request), weight=2)
        raise HTTPException(status_code=401, detail='Admin authorization required')


def _get_api_key_info(request: Request) -> dict[str, Any] | None:
    """
    Extract and validate API key from X-API-Key header.
    Returns key info dict or None if no key provided.
    Raises 401/403 if key is invalid or quota exceeded.
    """
    api_key = request.headers.get('x-api-key', '').strip()
    if not api_key:
        return None

    key_info = validate_key(api_key)
    if key_info is None:
        _register_violation(_client_ip(request), weight=2)
        raise HTTPException(status_code=401, detail='Invalid API key')

    return key_info


@app.middleware('http')
async def security_middleware(request: Request, call_next):
    ip = _client_ip(request)
    t0 = time.time()

    if _is_blocked(ip):
        return JSONResponse(status_code=429, content={'detail': 'Client temporarily blocked'})

    if not _check_rate_limit(ip):
        return JSONResponse(status_code=429, content={'detail': 'Rate limit exceeded'})

    try:
        response = await call_next(request)
    except HTTPException:
        raise

    duration_ms = (time.time() - t0) * 1000
    route = request.url.path
    is_err = response.status_code >= 400
    record_request(route, duration_ms, is_error=is_err)

    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers['Cache-Control'] = 'no-store'
    return response


class MemoryContextRequest(BaseModel):
    query: str = Field(min_length=1)
    sessionId: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class ProjectMemoryRecord(BaseModel):
    category: str = Field(description='task | decision | milestone | context')
    taskId: str = ''
    title: str
    status: str = ''
    phase: str = ''
    notes: str = ''


class ChatMessage(BaseModel):
    role: str = Field(description='user | assistant')
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    analysisContext: dict[str, Any] | None = None


class MemoryIngestRequest(BaseModel):
    sessionId: str
    fileName: str
    diagnosisStatus: str | None = None
    stage: str = ''
    confidence: float = 0.0
    report: str = ''
    features: dict[str, float] = Field(default_factory=dict)
    createdAt: str = ''


def _extract_json_from_stdout(stdout: str) -> dict[str, Any]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith('{') and line.endswith('}'):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f'Pipeline JSON parsing failed: {exc}') from exc


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-ZÀ-ÿ0-9_\-]+", text.lower()) if len(token) > 2}


def _read_memory_records() -> list[dict[str, Any]]:
    if not MEMORY_FILE.exists():
        return []

    records: list[dict[str, Any]] = []
    for line in MEMORY_FILE.read_text(encoding='utf-8', errors='ignore').splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _append_memory_record(record: dict[str, Any]) -> None:
    with MEMORY_FILE.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + '\n')


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok', 'service': 'neuro-link-api'}


@app.get('/metrics')
def metrics(request: Request) -> dict[str, Any]:
    _require_auth_if_enabled(request)
    snapshot = get_metrics_snapshot()
    try:
        from backend.gemini_report import get_usage_stats
        snapshot['gemini'] = get_usage_stats()
    except Exception:
        pass
    return snapshot


@app.get('/t')
def tracking_pixel(request: Request, p: str = 'unknown'):
    """Privacy-first 1×1 transparent pixel. No cookies, no PII."""
    referrer = request.headers.get('referer')
    record_page_view(page=p, referrer=referrer)
    # Return 1×1 transparent GIF
    PIXEL = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    from starlette.responses import Response
    return Response(content=PIXEL, media_type='image/gif', headers={
        'Cache-Control': 'no-store, no-cache, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
    })


@app.get('/analytics')
def analytics_endpoint(request: Request) -> dict[str, Any]:
    """Aggregated page view analytics (no PII). Auth-protected."""
    _require_auth_if_enabled(request)
    return get_page_analytics()


# ═══════════ Public Plan Endpoints ═══════════

@app.get('/plans')
def public_plans() -> dict[str, Any]:
    """List available plans and pricing (public, no auth)."""
    return {'plans': {k: {'label': v['label'], 'price_eur': v['price_eur'],
                          'max_analyses_per_month': v['max_analyses_per_month']}
                      for k, v in PLANS.items()}}


class SignupRequest(BaseModel):
    plan: str = Field(default='free')
    owner: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=200)
    organization: str = Field(default='', max_length=200)


@app.post('/signup')
def public_signup(payload: SignupRequest) -> dict[str, Any]:
    """Self-service signup for free plan. Creates an API key and returns the prefix."""
    if payload.plan != 'free':
        raise HTTPException(status_code=400, detail='Self-service signup is only available for the free plan. Contact us for paid plans.')

    try:
        result = generate_api_key(owner=payload.owner, email=payload.email, plan='free')
        mon_logger.info('Self-service signup: owner=%s email=%s', payload.owner, payload.email)
        return {
            'status': 'ok',
            'message': 'Compte créé avec succès. Votre clé API a été générée.',
            'key_prefix': result['key_prefix'],
            'api_key': result['raw_key'],
            'plan': 'free',
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class ContactRequest(BaseModel):
    plan: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=200)
    organization: str = Field(default='', max_length=200)


@app.post('/contact')
def public_contact(payload: ContactRequest) -> dict[str, Any]:
    """Record a contact/subscription request for paid plans."""
    # Store in a simple JSON log
    import json
    contact_file = Path(__file__).resolve().parent / 'data' / 'contact_requests.jsonl'
    contact_file.parent.mkdir(parents=True, exist_ok=True)

    record = {
        'ts': datetime.utcnow().isoformat() + 'Z',
        'plan': payload.plan,
        'name': payload.name,
        'email': payload.email,
        'organization': payload.organization,
    }
    with open(contact_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')

    mon_logger.info('Contact request: plan=%s name=%s email=%s', payload.plan, payload.name, payload.email)
    return {
        'status': 'ok',
        'message': 'Demande enregistrée. Notre équipe vous contactera sous 24h.',
    }


@app.post('/analyze')
async def analyze(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = Form(default='session_default'),
    memory_context: str = Form(default=''),
) -> dict[str, Any]:
    _require_auth_if_enabled(request)

    # ── API Key auth + quota check ──
    key_info = _get_api_key_info(request)
    if key_info:
        quota = check_quota(key_info['id'], key_info['plan'], endpoint='/analyze')
        if not quota['allowed']:
            raise HTTPException(
                status_code=429,
                detail=f"Quota mensuel atteint ({quota['used']}/{quota['limit']} analyses). Passez au plan supérieur.",
            )

    if not PIPELINE_SCRIPT.exists():
        raise HTTPException(status_code=500, detail=f'Pipeline script not found: {PIPELINE_SCRIPT}')

    session_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', session_id)[:64] or 'session_default'
    if _looks_malicious(session_id) or _looks_malicious(memory_context):
        _register_violation(_client_ip(request), weight=2)
        raise HTTPException(status_code=400, detail='Suspicious payload rejected')

    if len(memory_context) > MAX_CONTEXT_LENGTH:
        raise HTTPException(status_code=413, detail='memory_context too large')

    suffix = Path(file.filename or 'input.set').suffix or '.set'
    if suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f'Unsupported file extension: {suffix}')

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail='Empty file')
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        _register_violation(_client_ip(request))
        raise HTTPException(status_code=413, detail='File too large')

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(file_bytes)

    command = [
        sys.executable,
        str(PIPELINE_SCRIPT),
        '--file',
        str(tmp_path),
        '--name',
        session_id,
        '--output_dir',
        str(PIPELINE_OUTPUT_DIR),
    ]

    if memory_context.strip():
        metadata_path = PIPELINE_OUTPUT_DIR / f'{session_id}_memory_context.txt'
        metadata_path.write_text(memory_context, encoding='utf-8')

    process = subprocess.run(command, capture_output=True, text=True, cwd=str(ROOT_DIR))

    try:
        result = _extract_json_from_stdout(process.stdout)
    finally:
        tmp_path.unlink(missing_ok=True)

    if process.returncode != 0:
        return {
            'error': 'Pipeline failed',
            'status': 'INCONCLUSIVE',
            'stage': 'Inconnu',
            'confidence': 0.0,
            'features': {},
            'report': 'Inference failed. Check backend logs and model/runtime dependencies.',
        }

    status = result.get('status', 'INCONCLUSIVE')
    stage = result.get('stage', 'Inconnu')
    confidence = float(result.get('confidence', 0.0))
    features = result.get('features', {})
    raw_report = result.get('report', '')

    # ── Gemini AI: generate professional report ──
    ai_report = raw_report
    try:
        from backend.gemini_report import generate_gemini_report
        gemini_text = await generate_gemini_report(
            status=status,
            stage=stage,
            confidence=confidence,
            features=features,
            raw_report=raw_report,
        )
        if gemini_text:
            ai_report = gemini_text
    except Exception as exc:
        import logging
        logging.getLogger('neuro-link').warning('Gemini report generation failed: %s', exc)

    # ── Track API key usage ──
    if key_info:
        record_usage(key_info['id'], endpoint='/analyze', is_analysis=True)

    return {
        'status': status,
        'stage': stage,
        'confidence': confidence,
        'features': features,
        'report': ai_report,
        'raw_report': raw_report,
        'pipeline': result.get('pipeline', {}),
    }


@app.get('/memory/health')
def memory_health() -> dict[str, str]:
    return {'status': 'ok', 'service': 'memory'}


@app.post('/memory/context')
def memory_context(payload: MemoryContextRequest, request: Request) -> dict[str, Any]:
    _require_auth_if_enabled(request)
    if _looks_malicious(payload.query) or _looks_malicious(payload.sessionId):
        _register_violation(_client_ip(request), weight=2)
        raise HTTPException(status_code=400, detail='Suspicious query rejected')

    records = _read_memory_records()
    query_tokens = _tokenize(payload.query)

    scored_records: list[tuple[int, dict[str, Any]]] = []
    for record in records:
        if record.get('sessionId') != payload.sessionId:
            continue

        haystack = ' '.join(
            [
                str(record.get('fileName', '')),
                str(record.get('diagnosisStatus', '')),
                str(record.get('stage', '')),
                str(record.get('report', '')),
            ]
        )
        score = len(query_tokens.intersection(_tokenize(haystack)))
        if score > 0:
            scored_records.append((score, record))

    scored_records.sort(key=lambda item: item[0], reverse=True)
    top_records = [record for _, record in scored_records[: payload.limit]]

    context_parts = []
    for record in top_records:
        context_parts.append(
            f"File={record.get('fileName')} | Status={record.get('diagnosisStatus')} | Stage={record.get('stage')} | Confidence={record.get('confidence')}"
        )

    context_text = '\n'.join(context_parts)
    return {'context': context_text, 'sourceCount': len(top_records)}


@app.post('/memory/ingest')
def memory_ingest(payload: MemoryIngestRequest, request: Request) -> dict[str, Any]:
    _require_auth_if_enabled(request)
    if _looks_malicious(payload.sessionId) or _looks_malicious(payload.fileName):
        _register_violation(_client_ip(request), weight=2)
        raise HTTPException(status_code=400, detail='Suspicious payload rejected')

    record = {
        **payload.model_dump(),
        'ingestedAt': datetime.utcnow().isoformat() + 'Z',
    }
    _append_memory_record(record)
    return {'status': 'ok'}


# ═══════════ Chatbot IA ═══════════

@app.post('/chat')
async def chat(payload: ChatRequest, request: Request) -> dict[str, Any]:
    _require_auth_if_enabled(request)
    messages = [{'role': m.role, 'content': m.content} for m in payload.messages]

    # validate roles
    for m in messages:
        if m['role'] not in ('user', 'assistant'):
            raise HTTPException(status_code=400, detail=f"Invalid role: {m['role']}")

    # limit conversation length
    if len(messages) > 50:
        messages = messages[-50:]

    try:
        from backend.gemini_chat import chat_with_gemini
        reply = await chat_with_gemini(
            messages=messages,
            analysis_context=payload.analysisContext,
        )
        return {'reply': reply}
    except Exception as exc:
        import logging
        logging.getLogger('neuro-link').error('Chat error: %s', exc)
        return {'reply': "Désolé, une erreur s'est produite. L'assistant est temporairement indisponible."}


# ═══════════ Project Memory ═══════════

def _read_project_memory() -> list[dict[str, Any]]:
    if not PROJECT_MEMORY_FILE.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in PROJECT_MEMORY_FILE.read_text(encoding='utf-8', errors='ignore').splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _write_project_memory(records: list[dict[str, Any]]) -> None:
    with PROJECT_MEMORY_FILE.open('w', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


@app.get('/project/tasks')
def project_tasks(request: Request) -> dict[str, Any]:
    _require_auth_if_enabled(request)
    records = _read_project_memory()
    return {'tasks': records, 'count': len(records)}


@app.post('/project/upsert')
def project_upsert(payload: ProjectMemoryRecord, request: Request) -> dict[str, Any]:
    _require_auth_if_enabled(request)
    records = _read_project_memory()
    payload_dict = {**payload.model_dump(), 'updatedAt': datetime.utcnow().isoformat() + 'Z'}

    updated = False
    if payload.taskId:
        for i, r in enumerate(records):
            if r.get('taskId') == payload.taskId:
                records[i] = payload_dict
                updated = True
                break

    if not updated:
        records.append(payload_dict)

    _write_project_memory(records)
    return {'status': 'ok', 'action': 'updated' if updated else 'created'}


@app.get('/project/summary')
def project_summary(request: Request) -> dict[str, Any]:
    _require_auth_if_enabled(request)
    records = [r for r in _read_project_memory() if r.get('category') == 'task']
    total = len(records)
    done = sum(1 for r in records if r.get('status') == 'completed')
    progress = sum(1 for r in records if r.get('status') == 'in-progress')
    todo = sum(1 for r in records if r.get('status') == 'not-started')
    return {
        'total': total,
        'completed': done,
        'inProgress': progress,
        'notStarted': todo,
        'percentComplete': round(done / total * 100, 1) if total > 0 else 0,
    }


# ═══════════ PDF Export ═══════════

class PdfReportRequest(BaseModel):
    status: str = 'INCONCLUSIVE'
    stage: str = 'Inconnu'
    confidence: float = 0.0
    features: dict[str, Any] = {}
    report: str = ''
    pipeline: dict[str, Any] = {}
    patientId: str = 'Anonyme'


@app.post('/report/pdf')
def report_pdf(payload: PdfReportRequest, request: Request):
    _require_auth_if_enabled(request)
    try:
        from backend.pdf_report import generate_pdf_report
    except ImportError:
        raise HTTPException(status_code=501, detail='reportlab is not installed on the server')

    analysis = payload.model_dump()
    patient_id = analysis.pop('patientId', 'Anonyme')
    pdf_bytes = generate_pdf_report(analysis, patient_id=patient_id)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="neuro-link-report.pdf"'},
    )


# ═══════════ FHIR Export (HL7 FHIR R4) ═══════════

class FhirExportRequest(BaseModel):
    status: str = 'INCONCLUSIVE'
    stage: str = 'Inconnu'
    confidence: float = 0.0
    features: dict[str, float] = {}
    report: str = ''
    patientId: str = 'Anonyme'


@app.post('/report/fhir')
def report_fhir(payload: FhirExportRequest, request: Request) -> dict[str, Any]:
    """Export analysis results as a FHIR R4 Bundle (DiagnosticReport + Observations)."""
    _require_auth_if_enabled(request)

    # API key tracking (optional)
    key_info = _get_api_key_info(request)
    if key_info:
        record_usage(key_info['id'], endpoint='/report/fhir', is_analysis=False)

    from backend.fhir_export import create_fhir_bundle, validate_bundle_structure

    bundle = create_fhir_bundle(
        status=payload.status,
        stage=payload.stage,
        confidence=payload.confidence,
        features=payload.features,
        report_text=payload.report,
        patient_id=payload.patientId,
    )

    errors = validate_bundle_structure(bundle)
    if errors:
        return {'bundle': bundle, 'validation_errors': errors}

    return bundle


@app.post('/report/fhir/json')
def report_fhir_json(payload: FhirExportRequest, request: Request):
    """Export FHIR Bundle as downloadable JSON file."""
    _require_auth_if_enabled(request)

    from backend.fhir_export import create_fhir_bundle, bundle_to_json

    bundle = create_fhir_bundle(
        status=payload.status,
        stage=payload.stage,
        confidence=payload.confidence,
        features=payload.features,
        report_text=payload.report,
        patient_id=payload.patientId,
    )

    json_str = bundle_to_json(bundle)
    return StreamingResponse(
        io.BytesIO(json_str.encode('utf-8')),
        media_type='application/fhir+json',
        headers={'Content-Disposition': 'attachment; filename="neuro-link-fhir-report.json"'},
    )


# ═══════════ Admin – API Key Management (SaaS) ═══════════

class CreateKeyRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=200)
    email: str = Field(default='', max_length=200)
    plan: str = Field(default='free')


class UpdateKeyRequest(BaseModel):
    plan: str | None = None
    active: bool | None = None
    owner: str | None = None
    email: str | None = None


@app.get('/admin/plans')
def admin_plans(request: Request) -> dict[str, Any]:
    """List available SaaS plans and their quotas."""
    _require_admin(request)
    return {'plans': PLANS}


@app.post('/admin/keys')
def admin_create_key(payload: CreateKeyRequest, request: Request) -> dict[str, Any]:
    """Generate a new API key for a client."""
    _require_admin(request)
    try:
        result = generate_api_key(owner=payload.owner, email=payload.email, plan=payload.plan)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result


@app.get('/admin/keys')
def admin_list_keys(request: Request, include_inactive: bool = False) -> dict[str, Any]:
    """List all API keys with usage info."""
    _require_admin(request)
    keys = list_keys(include_inactive=include_inactive)
    return {'keys': keys, 'count': len(keys)}


@app.get('/admin/keys/{key_id}')
def admin_get_key(key_id: int, request: Request) -> dict[str, Any]:
    """Get details for a specific API key."""
    _require_admin(request)
    key = get_key_by_id(key_id)
    if not key:
        raise HTTPException(status_code=404, detail='API key not found')
    usage = get_usage(key_id)
    key['usage'] = usage
    key['plan_info'] = PLANS.get(key['plan'], PLANS['free'])
    return key


@app.patch('/admin/keys/{key_id}')
def admin_update_key(key_id: int, payload: UpdateKeyRequest, request: Request) -> dict[str, Any]:
    """Update an API key (plan, status, owner, email)."""
    _require_admin(request)
    try:
        success = update_key(
            key_id,
            plan=payload.plan,
            active=payload.active,
            owner=payload.owner,
            email=payload.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not success:
        raise HTTPException(status_code=404, detail='API key not found or no changes')
    return {'status': 'ok', 'key_id': key_id}


@app.post('/admin/keys/{key_id}/revoke')
def admin_revoke_key(key_id: int, request: Request) -> dict[str, Any]:
    """Revoke (deactivate) an API key."""
    _require_admin(request)
    if not revoke_key(key_id):
        raise HTTPException(status_code=404, detail='API key not found')
    return {'status': 'revoked', 'key_id': key_id}


@app.delete('/admin/keys/{key_id}')
def admin_delete_key(key_id: int, request: Request) -> dict[str, Any]:
    """Permanently delete an API key and its usage data."""
    _require_admin(request)
    if not delete_key(key_id):
        raise HTTPException(status_code=404, detail='API key not found')
    return {'status': 'deleted', 'key_id': key_id}


@app.get('/admin/keys/{key_id}/usage')
def admin_key_usage(key_id: int, request: Request, month: str | None = None) -> dict[str, Any]:
    """Get usage details for a specific API key."""
    _require_admin(request)
    key = get_key_by_id(key_id)
    if not key:
        raise HTTPException(status_code=404, detail='API key not found')
    return get_usage(key_id, month=month)


@app.get('/admin/usage/summary')
def admin_usage_summary(request: Request) -> dict[str, Any]:
    """Get overall usage summary for the current month."""
    _require_admin(request)
    return get_all_usage_summary()


@app.get('/api/quota')
def api_quota(request: Request) -> dict[str, Any]:
    """
    Public endpoint: check remaining quota for the provided API key.
    Requires X-API-Key header.
    """
    key_info = _get_api_key_info(request)
    if not key_info:
        raise HTTPException(status_code=401, detail='X-API-Key header required')
    quota = check_quota(key_info['id'], key_info['plan'])
    usage = get_usage(key_info['id'])
    return {
        'plan': key_info['plan'],
        'plan_info': PLANS.get(key_info['plan'], PLANS['free']),
        'quota': quota,
        'usage': {
            'analyses': usage['analyses_count'],
            'requests': usage['requests_count'],
            'month': usage['month'],
        },
    }


# ═══════════ Stripe Billing ═══════════

class CheckoutRequest(BaseModel):
    plan: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    email: str = Field(default='')
    api_key_id: int = Field(gt=0)


@app.get('/stripe/config')
def stripe_config(request: Request) -> dict[str, Any]:
    """Check Stripe configuration status (admin only)."""
    _require_admin(request)
    from backend.stripe_billing import get_stripe_config
    return get_stripe_config()


@app.post('/stripe/checkout')
def stripe_checkout(payload: CheckoutRequest, request: Request) -> dict[str, Any]:
    """Create a Stripe Checkout Session for a plan subscription."""
    _require_admin(request)
    from backend.stripe_billing import create_checkout_session, is_configured

    if not is_configured():
        raise HTTPException(status_code=503, detail='Stripe not configured (set STRIPE_* env vars)')

    key = get_key_by_id(payload.api_key_id)
    if not key:
        raise HTTPException(status_code=404, detail='API key not found')

    try:
        result = create_checkout_session(
            plan=payload.plan,
            owner=payload.owner,
            email=payload.email,
            api_key_id=payload.api_key_id,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post('/stripe/portal')
def stripe_portal(request: Request) -> dict[str, Any]:
    """Create a Stripe Customer Portal session. Requires customer_id in body."""
    _require_admin(request)
    from backend.stripe_billing import create_portal_session, is_configured

    if not is_configured():
        raise HTTPException(status_code=503, detail='Stripe not configured')

    body = {}
    # Parse JSON body for customer_id
    import asyncio
    # Sync route, use simple approach
    customer_id = request.query_params.get('customer_id', '')
    if not customer_id:
        raise HTTPException(status_code=400, detail='customer_id query param required')

    try:
        return create_portal_session(customer_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post('/stripe/webhook')
async def stripe_webhook(request: Request) -> dict[str, Any]:
    """Handle Stripe webhook events. No auth required (verified by signature)."""
    from backend.stripe_billing import construct_webhook_event, handle_webhook_event

    payload = await request.body()
    sig_header = request.headers.get('stripe-signature', '')

    try:
        event = construct_webhook_event(payload, sig_header)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    result = handle_webhook_event(event)
    return {'status': 'ok', **result}


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL AGENT ROUTES (admin-only)
# ═══════════════════════════════════════════════════════════════════════════════

class EmailSendPayload(BaseModel):
    to: list[str] = Field(min_length=1)
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(default='')
    html: str | None = None
    cc: list[str] | None = None
    bcc: list[str] | None = None
    reply_to: str | None = None
    add_signature: bool = True
    dry_run: bool = False

class EmailTemplatePayload(BaseModel):
    to: list[str] = Field(min_length=1)
    template_path: str = Field(min_length=1)
    subject: str | None = None
    cc: list[str] | None = None
    bcc: list[str] | None = None
    reply_to: str | None = None
    dry_run: bool = False


@app.post('/admin/email/send')
def admin_email_send(payload: EmailSendPayload, request: Request) -> dict[str, Any]:
    """Send an email via the Neuro-Link Email Agent. Requires admin token."""
    _require_admin(request)
    from backend.email_agent import EmailAgent

    try:
        agent = EmailAgent()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    try:
        result = agent.send(
            to=payload.to,
            subject=payload.subject,
            body=payload.body,
            html=payload.html,
            cc=payload.cc,
            bcc=payload.bcc,
            reply_to=payload.reply_to,
            add_signature=payload.add_signature,
            dry_run=payload.dry_run,
        )
        mon_logger.info('Email sent: to=%s subject=%s', payload.to, payload.subject)
        return result
    except Exception as exc:
        mon_logger.error('Email send failed: %s', exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post('/admin/email/send-template')
def admin_email_send_template(payload: EmailTemplatePayload, request: Request) -> dict[str, Any]:
    """Send an email from a Markdown template. Requires admin token."""
    _require_admin(request)
    from backend.email_agent import EmailAgent

    try:
        agent = EmailAgent()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    try:
        result = agent.send_template(
            to=payload.to,
            template_path=payload.template_path,
            subject=payload.subject,
            cc=payload.cc,
            bcc=payload.bcc,
            reply_to=payload.reply_to,
            dry_run=payload.dry_run,
        )
        mon_logger.info('Email template sent: to=%s template=%s', payload.to, payload.template_path)
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        mon_logger.error('Email template send failed: %s', exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post('/admin/email/test')
def admin_email_test(request: Request) -> dict[str, Any]:
    """Send a test email to the agent's own address. Requires admin token."""
    _require_admin(request)
    from backend.email_agent import EmailAgent

    try:
        agent = EmailAgent()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    try:
        return agent.send_test()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get('/admin/email/log')
def admin_email_log(request: Request, limit: int = 50) -> list[dict[str, Any]]:
    """Get recent email send log. Requires admin token."""
    _require_admin(request)
    from backend.email_agent import EmailAgent

    agent = EmailAgent.__new__(EmailAgent)
    return agent.get_log(limit=limit)


# ===========================================================================
# Email AI Agent — routes
# ===========================================================================

class EmailAIComposePayload(BaseModel):
    instruction: str = Field(min_length=1)
    to: str | None = None

class EmailAIDraftPayload(BaseModel):
    target_type: str = Field(min_length=1)
    target_name: str = Field(min_length=1)
    target_info: str = ''

class EmailAIReplyPayload(BaseModel):
    email_id: str | None = None
    from_addr: str | None = None
    subject: str | None = None
    body: str | None = None

class EmailAISendPayload(BaseModel):
    draft_id: str = Field(min_length=1)

class EmailAICampaignStartPayload(BaseModel):
    campaign_id: str = Field(min_length=1)
    to: str = Field(min_length=1)
    target_name: str = Field(min_length=1)
    target_info: str = ''


@app.post('/admin/email-ai/compose')
def admin_email_ai_compose(payload: EmailAIComposePayload, request: Request) -> dict[str, Any]:
    """Free-form AI email composition."""
    _require_admin(request)
    from backend.email_ai_agent import EmailAIAgent
    agent = EmailAIAgent()
    draft = agent.compose(instruction=payload.instruction, to=payload.to)
    return draft


@app.post('/admin/email-ai/draft')
def admin_email_ai_draft(payload: EmailAIDraftPayload, request: Request) -> dict[str, Any]:
    """Generate a prospection draft."""
    _require_admin(request)
    from backend.email_ai_agent import EmailAIAgent
    agent = EmailAIAgent()
    draft = agent.draft_prospection(
        target_type=payload.target_type,
        target_name=payload.target_name,
        target_info=payload.target_info,
    )
    return draft


@app.post('/admin/email-ai/reply')
def admin_email_ai_reply(payload: EmailAIReplyPayload, request: Request) -> dict[str, Any]:
    """Generate an AI reply to an email."""
    _require_admin(request)
    from backend.email_ai_agent import EmailAIAgent
    agent = EmailAIAgent()
    if payload.email_id:
        draft = agent.draft_reply(payload.email_id)
    else:
        email_dict = {
            'from': payload.from_addr or '',
            'subject': payload.subject or '',
            'body': payload.body or '',
        }
        draft = agent.analyze_incoming(email_dict)
    return draft


@app.post('/admin/email-ai/send')
def admin_email_ai_send(payload: EmailAISendPayload, request: Request) -> dict[str, Any]:
    """Send an approved draft."""
    _require_admin(request)
    from backend.email_ai_agent import EmailAIAgent
    agent = EmailAIAgent()
    result = agent.send_draft(payload.draft_id, approve=True)
    return result


@app.get('/admin/email-ai/inbox')
def admin_email_ai_inbox(request: Request, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch recent Gmail inbox messages."""
    _require_admin(request)
    from backend.gmail_reader import GmailReader
    reader = GmailReader()
    messages = reader.fetch_recent(max_results=limit)
    return messages


@app.get('/admin/email-ai/memory')
def admin_email_ai_memory(request: Request, q: str = '', limit: int = 20) -> dict[str, Any]:
    """Query email memory. ?q=search_term or return recent."""
    _require_admin(request)
    from backend.email_memory import EmailMemory
    mem = EmailMemory()
    if q:
        results = mem.search(q, limit=limit)
    else:
        results = mem.get_recent(limit)
    return {'query': q, 'count': len(results), 'results': results}


@app.post('/admin/email-ai/campaign/start')
def admin_email_ai_campaign_start(payload: EmailAICampaignStartPayload, request: Request) -> dict[str, Any]:
    """Start a drip campaign."""
    _require_admin(request)
    from backend.drip_campaigns import CampaignManager
    mgr = CampaignManager()
    result = mgr.start_campaign(
        campaign_id=payload.campaign_id,
        to=payload.to,
        target_name=payload.target_name,
        target_info=payload.target_info,
    )
    return result


@app.get('/admin/email-ai/campaign/status')
def admin_email_ai_campaign_status(request: Request) -> list[dict[str, Any]]:
    """Get all campaigns status."""
    _require_admin(request)
    from backend.drip_campaigns import CampaignManager
    mgr = CampaignManager()
    return mgr.get_all_campaigns_status()


@app.get('/admin/email-ai/campaign/list')
def admin_email_ai_campaign_list(request: Request) -> list[dict[str, Any]]:
    """List available campaign templates."""
    _require_admin(request)
    from backend.drip_campaigns import CampaignManager
    mgr = CampaignManager()
    return mgr.list_campaigns()


@app.post('/admin/email-ai/campaign/check')
def admin_email_ai_campaign_check(request: Request) -> list[dict[str, Any]]:
    """Process due campaign steps (cron trigger)."""
    _require_admin(request)
    from backend.drip_campaigns import CampaignManager
    mgr = CampaignManager()
    return mgr.check_and_send_due()


@app.get('/admin/email-ai/drafts')
def admin_email_ai_drafts(request: Request) -> list[dict[str, Any]]:
    """List all draft emails from memory."""
    _require_admin(request)
    from backend.email_ai_agent import EmailAIAgent
    agent = EmailAIAgent()
    all_records = agent.memory.get_all()
    drafts = [r for r in all_records if r.get('type') == 'draft']
    drafts.sort(key=lambda r: r.get('timestamp', ''), reverse=True)
    return drafts


class ProcessInboxPayload(BaseModel):
    max_emails: int = Field(default=20, ge=1, le=100)
    auto_reply: bool = True
    auto_send: bool = False


@app.post('/admin/email-ai/process-inbox')
def admin_email_ai_process_inbox(payload: ProcessInboxPayload, request: Request) -> dict[str, Any]:
    """Process inbox: classify emails (spam/pub/pro), auto-reply to prospects."""
    _require_admin(request)
    from backend.email_ai_agent import EmailAIAgent
    agent = EmailAIAgent()
    return agent.process_inbox(
        max_emails=payload.max_emails,
        auto_reply=payload.auto_reply,
        auto_send=payload.auto_send,
    )


class ClassifyEmailPayload(BaseModel):
    from_addr: str = ''
    subject: str = ''
    body: str = ''
    snippet: str = ''


@app.post('/admin/email-ai/classify')
def admin_email_ai_classify(payload: ClassifyEmailPayload, request: Request) -> dict[str, Any]:
    """Classify a single email (spam/pub/pro/etc)."""
    _require_admin(request)
    from backend.email_ai_agent import EmailAIAgent
    agent = EmailAIAgent()
    return agent.classify_email({
        'from_addr': payload.from_addr,
        'subject': payload.subject,
        'body': payload.body,
        'snippet': payload.snippet,
    })
