# ──────────────  Neuro-Link v18 — Dockerfile  ──────────────
# Multi-stage build: Python ML backend + Vite frontend

# ═══════════ Stage 1: Frontend build ═══════════
FROM node:20-slim AS frontend
WORKDIR /app
COPY package.json tsconfig.json vite.config.ts index.html ./
RUN npm ci --ignore-scripts
COPY components/ components/
COPY public/ public/
COPY *.tsx *.ts ./
RUN npm run build

# ═══════════ Stage 2: Python runtime ═══════════
FROM python:3.11-slim AS runtime

# System dependencies for MNE, scipy, and reportlab
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY backend/requirements.txt backend/requirements.txt
COPY requirements-ml.txt requirements-ml.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    -r requirements-ml.txt \
    reportlab

# Copy backend
COPY backend/ backend/
COPY alz-finis/ alz-finis/

# Copy built frontend
COPY --from=frontend /app/dist /app/frontend-dist

# Create data directories
RUN mkdir -p backend/data backend/runs

# Environment
ENV PYTHONUNBUFFERED=1 \
    PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
