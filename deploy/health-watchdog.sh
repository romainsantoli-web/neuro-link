#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# Neuro-Link — Health check cron + auto-restart
# Installer : sudo cp deploy/health-watchdog.sh /usr/local/bin/
#             sudo chmod +x /usr/local/bin/health-watchdog.sh
#             echo "*/5 * * * * root /usr/local/bin/health-watchdog.sh" | sudo tee /etc/cron.d/neuro-link-watchdog
# ═══════════════════════════════════════════════════════════

set -euo pipefail

LOG_FILE="/var/log/neuro-link-watchdog.log"
MAX_LOG_LINES=500
API_URL="http://127.0.0.1:8000/health"
SERVICE="neuro-link-api"

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }

# Trim log file
if [ -f "$LOG_FILE" ] && [ "$(wc -l < "$LOG_FILE")" -gt "$MAX_LOG_LINES" ]; then
    tail -n 200 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi

# Check API health
if curl -sf --max-time 10 "$API_URL" > /dev/null 2>&1; then
    echo "$(timestamp) OK — API healthy" >> "$LOG_FILE"
else
    echo "$(timestamp) WARN — API unreachable, restarting ${SERVICE}..." >> "$LOG_FILE"
    systemctl restart "$SERVICE" 2>> "$LOG_FILE"
    sleep 5

    if curl -sf --max-time 10 "$API_URL" > /dev/null 2>&1; then
        echo "$(timestamp) OK — Service restarted successfully" >> "$LOG_FILE"
    else
        echo "$(timestamp) ERROR — Service restart failed!" >> "$LOG_FILE"
    fi
fi
