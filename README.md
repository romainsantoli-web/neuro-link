<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/drive/1e__R1OH8bPSK1TDGD8A3yyJHHKpFbPey

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local) to your Gemini API key
3. Run the app:
   `npm run dev`

## Run Backend API (/health, /analyze, /memory/*)

1. Install backend dependencies:
   `python3 -m pip install -r backend/requirements.txt`
2. Start API server:
   `npm run api`

The frontend auto-connects to:

- `/api` first (if reverse proxy is configured)
- then fallback to `http://localhost:8000`

`POST /analyze` now calls `alz-finis/run_pipeline.py` (screening first, staging only if AD-positive) and returns normalized JSON for the dashboard.

### Security hardening (dynamic)

The backend now includes dynamic protections:

- per-IP rate limiting with temporary blocking
- suspicious payload detection (basic injection/path-traversal/script patterns)
- strict upload validation (allowed EEG extensions, max file size)
- optional bearer-token protection for sensitive routes
- security headers on all responses (`nosniff`, frame deny, no-store)

Optional environment variables:

- `SECURITY_BEARER_TOKEN` (if set, required as `Authorization: Bearer <token>`)
- `SECURITY_STRICT_MODE` (default `false`; if `true`, bearer token is mandatory)
- `RATE_LIMIT_PER_MINUTE` (default `60`)
- `RATE_LIMIT_BLOCK_SECONDS` (default `600`)
- `MAX_UPLOAD_BYTES` (default `20971520` = 20 MB)
- `MAX_CONTEXT_LENGTH` (default `12000`)
- `CORS_ALLOW_ORIGINS` (default `*`, comma-separated for production)

Production template:

- Copy `backend/.env.prod.example` and set a strong `SECURITY_BEARER_TOKEN`.
- In strict mode, sensitive routes (`/analyze`, `/memory/context`, `/memory/ingest`) reject requests without a valid bearer token.

### Model module resolution

The missing shared model module has been centralized at:

- `alz-finis/adformer_hybrid_voting_full.py`

This resolves imports used by staging/screening scripts.

## Nginx Production Setup (TLS + Protection)

Provided files:

- `deploy/nginx/neuro-link.conf` (reverse proxy + TLS + rate limit + security headers)
- `deploy/nginx/backend.env.example` (strict backend env template)

Quick activation (Linux server):

1. Build frontend and copy `dist` to `/var/www/neuro-link-v18/dist`.
2. Copy `deploy/nginx/neuro-link.conf` to `/etc/nginx/sites-available/neuro-link.conf`.
3. Replace `your-domain.com` and TLS cert paths.
4. Enable config:
   - `sudo ln -s /etc/nginx/sites-available/neuro-link.conf /etc/nginx/sites-enabled/neuro-link.conf`
5. Validate and reload:
   - `sudo nginx -t && sudo systemctl reload nginx`
6. Copy `deploy/nginx/backend.env.example` to your backend env file and set a strong token.

Once enabled, frontend calls `/api/*` via Nginx and backend strict mode remains enforced.

## systemd Service (auto-start backend)

Provided files:

- `deploy/systemd/neuro-link-api.service`
- `deploy/systemd/backend.env.example`

Quick setup (Linux server):

1. Ensure project is deployed at `/opt/neuro-link-v18` and venv python exists at `/opt/neuro-link-v18/.venv/bin/python`.
2. Copy env template:
   - `sudo mkdir -p /etc/neuro-link`
   - `sudo cp deploy/systemd/backend.env.example /etc/neuro-link/backend.env`
   - Edit token/domain values.
3. Install service:
   - `sudo cp deploy/systemd/neuro-link-api.service /etc/systemd/system/neuro-link-api.service`
4. Reload systemd and enable:
   - `sudo systemctl daemon-reload`
   - `sudo systemctl enable --now neuro-link-api`
5. Check status/logs:
   - `sudo systemctl status neuro-link-api`
   - `sudo journalctl -u neuro-link-api -f`

If your deploy path/user differs, update `WorkingDirectory`, `ExecStart`, `User`, and `Group` in the service file.

## Memory Pipeline Integration (Memory-os-ai)

The frontend now supports an optional memory service on the same backend base URL used for analysis.

Expected API routes:

- `GET /health` -> kernel health check
- `POST /analyze` -> EEG analysis endpoint
- `GET /memory/health` -> memory pipeline health check
- `POST /memory/context` -> returns retrieval context for current session
- `POST /memory/ingest` -> stores the latest analysis into memory

When memory is online:

- a context payload is fetched before `/analyze` and attached as `memory_context`
- `session_id` is attached to analysis requests
- analysis results are pushed to `/memory/ingest` after completion

If memory endpoints are unavailable, analysis still works (non-blocking fallback).

## OpenBCI Compatibility

The EEG pipeline now supports OpenBCI exports in addition to MNE-native files.

- Supported input formats: `.set`, `.edf`, `.bdf`, `.vhdr`, `.fif`, `.csv`, `.txt`
- OpenBCI `.csv/.txt` inputs are normalized to model expectations: band-pass filtered, resampled to `128 Hz`, and adapted to `19 channels`.
- New optional CLI arg on pipeline scripts: `--openbci_fs` (default `250.0`) used when timestamp-based sampling rate cannot be inferred.

Workflow stays unchanged:

- Step 1: screening (AD/CN)
- Step 2: staging only if screening is AD-positive

## Unified EEG Pipeline Runner

You can run a single command for:

1) screening (AD/CN)
2) staging only when screening is AD-positive

Command:

`python3 alz-finis/run_pipeline.py --file <path_to_eeg_file>`

OpenBCI example:

`python3 alz-finis/run_pipeline.py --file <openbci_export.csv> --openbci_fs 250`

Outputs:

- JSON on stdout (ready for backend `/analyze` integration)
- run folder under `alz-finis/results_pipeline/`
- normalized final result at `result.json`
