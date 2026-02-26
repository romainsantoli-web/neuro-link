#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Neuro-Link v18 — Script de déploiement automatisé
# Cible : Oracle Cloud Always Free (ARM Ampere A1)
#         4 OCPUs · 24 GB RAM · 200 GB · Ubuntu 22.04
# ═══════════════════════════════════════════════════════════════
#
# Usage :
#   ssh ubuntu@<IP_VPS> 'bash -s' < deploy/vps-setup.sh
#
# Ou après avoir cloné le repo :
#   chmod +x deploy/vps-setup.sh && sudo ./deploy/vps-setup.sh
#
# Ce script installe TOUT de zéro sur un Ubuntu 22.04+ propre.
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# ── Couleurs ──
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${CYAN}[→]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1" >&2; }

# ── Variables configurables ──
DOMAIN="${DOMAIN:-}"
APP_DIR="/opt/neuro-link-v18"
REPO_URL="${REPO_URL:-https://github.com/Romainmusic/neuro-link-v18.git}"
PYTHON_VERSION="3.11"
NODE_VERSION="20"
API_PORT=8000
BRANCH="${BRANCH:-main}"

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║   Neuro-Link v18 — Déploiement VPS Automatisé       ║"
echo "║   Oracle Cloud Always Free (ARM Ampere A1)           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ══════════════ 1. Système ══════════════
info "1/9 — Mise à jour système..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -yqq
apt-get install -yqq \
    build-essential \
    curl \
    git \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw \
    fail2ban \
    software-properties-common \
    libgomp1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    unzip \
    htop \
    jq
log "Système mis à jour"

# ══════════════ 2. Python 3.11 ══════════════
info "2/9 — Installation Python ${PYTHON_VERSION}..."
if ! command -v "python${PYTHON_VERSION}" &>/dev/null; then
    add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
    apt-get update -qq
    apt-get install -yqq \
        "python${PYTHON_VERSION}" \
        "python${PYTHON_VERSION}-venv" \
        "python${PYTHON_VERSION}-dev"
fi
log "Python $(python${PYTHON_VERSION} --version) installé"

# ══════════════ 3. Node.js 20 ══════════════
info "3/9 — Installation Node.js ${NODE_VERSION}..."
if ! command -v node &>/dev/null || [[ "$(node -v)" != v${NODE_VERSION}* ]]; then
    curl -fsSL "https://deb.nodesource.com/setup_${NODE_VERSION}.x" | bash -
    apt-get install -yqq nodejs
fi
log "Node.js $(node -v) installé"

# ══════════════ 4. Code source ══════════════
info "4/9 — Récupération du code source..."
if [ -d "${APP_DIR}/.git" ]; then
    cd "${APP_DIR}"
    git fetch origin "${BRANCH}"
    git reset --hard "origin/${BRANCH}"
    log "Code mis à jour (branch ${BRANCH})"
else
    git clone --branch "${BRANCH}" --depth 1 "${REPO_URL}" "${APP_DIR}"
    log "Repo cloné dans ${APP_DIR}"
fi
cd "${APP_DIR}"

# ══════════════ 5. Environnement Python ══════════════
info "5/9 — Création/mise à jour de l'environnement Python..."
if [ ! -d "${APP_DIR}/.venv" ]; then
    "python${PYTHON_VERSION}" -m venv "${APP_DIR}/.venv"
fi
source "${APP_DIR}/.venv/bin/activate"

pip install --upgrade pip wheel setuptools -q
pip install -r backend/requirements.txt -q
pip install -r requirements-ml.txt -q 2>/dev/null || {
    info "Installation ML sans PyTorch CUDA (CPU only pour Oracle ARM)..."
    pip install torch --index-url https://download.pytorch.org/whl/cpu -q
    pip install mne scipy numpy scikit-learn antropy pykalman h5py joblib matplotlib -q
}
log "Environnement Python prêt ($(pip list --format=columns | wc -l) packages)"

# ══════════════ 6. Frontend build ══════════════
info "6/9 — Build du frontend React..."
npm ci --ignore-scripts --no-audit -q 2>/dev/null
npm run build
mkdir -p /var/www/neuro-link-v18
cp -r dist/* /var/www/neuro-link-v18/
log "Frontend compilé → /var/www/neuro-link-v18/"

# ══════════════ 7. Systemd service ══════════════
info "7/9 — Configuration du service systemd..."
mkdir -p /etc/neuro-link
mkdir -p "${APP_DIR}/backend/data" "${APP_DIR}/backend/runs"

# Générer le token si absent
if [ ! -f /etc/neuro-link/backend.env ]; then
    TOKEN=$(openssl rand -hex 32)
    cat > /etc/neuro-link/backend.env <<ENVEOF
SECURITY_STRICT_MODE=true
SECURITY_BEARER_TOKEN=${TOKEN}
CORS_ALLOW_ORIGINS=${DOMAIN:+https://$DOMAIN}
RATE_LIMIT_PER_MINUTE=40
RATE_LIMIT_BLOCK_SECONDS=900
MAX_UPLOAD_BYTES=20971520
ENVEOF
    chmod 600 /etc/neuro-link/backend.env
    log "Token API généré : ${TOKEN:0:8}... (sauvé dans /etc/neuro-link/backend.env)"
else
    log "backend.env existant conservé"
fi

cp deploy/systemd/neuro-link-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable neuro-link-api
systemctl restart neuro-link-api
sleep 2

if systemctl is-active --quiet neuro-link-api; then
    log "Service neuro-link-api actif ✓"
else
    err "Le service n'a pas démarré ! Vérifier : journalctl -u neuro-link-api -n 50"
    systemctl status neuro-link-api --no-pager || true
fi

# ══════════════ 8. Nginx + TLS ══════════════
info "8/9 — Configuration Nginx..."
NGINX_CONF="/etc/nginx/sites-available/neuro-link.conf"

if [ -n "${DOMAIN}" ]; then
    # Remplacer le placeholder par le vrai domaine
    sed "s/your-domain.com/${DOMAIN}/g" deploy/nginx/neuro-link.conf > "${NGINX_CONF}"
    ln -sf "${NGINX_CONF}" /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default

    nginx -t && systemctl reload nginx
    log "Nginx configuré pour ${DOMAIN}"

    info "Obtention du certificat TLS (Let's Encrypt)..."
    certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos \
        --email "${CERTBOT_EMAIL:-admin@${DOMAIN}}" \
        --redirect 2>/dev/null || {
        info "Certbot a échoué — le domaine pointe-t-il vers cette IP ?"
        info "Relancer manuellement : certbot --nginx -d ${DOMAIN}"
    }
else
    # Pas de domaine — config HTTP simple
    cat > "${NGINX_CONF}" <<'HTTPCONF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 20M;

    root /var/www/neuro-link-v18;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location = /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
HTTPCONF
    ln -sf "${NGINX_CONF}" /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl reload nginx
    log "Nginx configuré en HTTP (pas de domaine fourni)"
    info "Pour ajouter HTTPS : DOMAIN=neuro-link.example.com sudo ./deploy/vps-setup.sh"
fi

# ══════════════ 9. Firewall ══════════════
info "9/9 — Configuration du firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable
log "Firewall UFW actif (SSH + HTTP + HTTPS)"

# ══════════════ Résumé ══════════════
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║         🚀 Déploiement Neuro-Link terminé !          ║${NC}"
echo -e "${BOLD}╠══════════════════════════════════════════════════════╣${NC}"

PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "<IP_VPS>")

if [ -n "${DOMAIN}" ]; then
    echo -e "${BOLD}║${NC}  Frontend : ${GREEN}https://${DOMAIN}${NC}"
    echo -e "${BOLD}║${NC}  API       : ${GREEN}https://${DOMAIN}/api/${NC}"
else
    echo -e "${BOLD}║${NC}  Frontend : ${GREEN}http://${PUBLIC_IP}${NC}"
    echo -e "${BOLD}║${NC}  API       : ${GREEN}http://${PUBLIC_IP}/api/${NC}"
fi

echo -e "${BOLD}║${NC}  Health    : ${GREEN}http://${PUBLIC_IP}/health${NC}"
echo -e "${BOLD}║${NC}  Metrics   : voir /api/metrics (auth requise)"
echo -e "${BOLD}║${NC}"
echo -e "${BOLD}║${NC}  Token API : cat /etc/neuro-link/backend.env"
echo -e "${BOLD}║${NC}  Logs      : journalctl -u neuro-link-api -f"
echo -e "${BOLD}║${NC}  Status    : systemctl status neuro-link-api"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
