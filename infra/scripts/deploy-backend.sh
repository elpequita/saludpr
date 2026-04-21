#!/usr/bin/env bash
# =============================================================================
# SaludPR — Backend Deployment Script
#
# Pulls latest code, installs deps via uv, runs migrations, restarts service.
# Idempotent — safe to run repeatedly.
#
# Run as root:
#   sudo bash deploy-backend.sh
# =============================================================================

set -euo pipefail

readonly SALUDPR_USER="saludpr"
readonly SALUDPR_HOME="/opt/saludpr"
readonly REPO_DIR="${SALUDPR_HOME}/repo"
readonly BACKEND_DIR="${REPO_DIR}/backend"
readonly BRANCH="${SALUDPR_BRANCH:-main}"

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: must run as root" >&2
    exit 1
fi

if [[ ! -d "${REPO_DIR}" ]]; then
    echo "ERROR: repo not cloned yet at ${REPO_DIR}"
    echo "First time? Run:"
    echo "  sudo -u ${SALUDPR_USER} git clone git@github.com:elpequita/saludpr.git ${REPO_DIR}"
    exit 1
fi

echo "[deploy] Pulling latest on ${BRANCH}..."
sudo -u "${SALUDPR_USER}" git -C "${REPO_DIR}" fetch origin
sudo -u "${SALUDPR_USER}" git -C "${REPO_DIR}" checkout "${BRANCH}"
sudo -u "${SALUDPR_USER}" git -C "${REPO_DIR}" pull --ff-only

echo "[deploy] Installing backend dependencies..."
cd "${BACKEND_DIR}"
sudo -u "${SALUDPR_USER}" uv sync --frozen

echo "[deploy] Ensuring .env exists..."
if [[ ! -f "${BACKEND_DIR}/.env" ]]; then
    if [[ -f /root/saludpr-db-credentials.txt ]]; then
        cp /root/saludpr-db-credentials.txt "${BACKEND_DIR}/.env"
        # Append app settings
        cat >> "${BACKEND_DIR}/.env" <<EOF
APP_ENV=production
APP_DEBUG=false
APP_CORS_ORIGINS=https://saludpr.org,https://www.saludpr.org
LOG_LEVEL=INFO
LOG_FORMAT=json
RATE_LIMIT_PER_MINUTE=120
EOF
        chown "${SALUDPR_USER}:${SALUDPR_USER}" "${BACKEND_DIR}/.env"
        chmod 600 "${BACKEND_DIR}/.env"
    else
        echo "ERROR: /root/saludpr-db-credentials.txt missing. Run setup-vm.sh first."
        exit 1
    fi
fi

echo "[deploy] Running Alembic migrations..."
sudo -u "${SALUDPR_USER}" bash -c "cd ${BACKEND_DIR} && uv run alembic upgrade head"

echo "[deploy] Installing systemd service..."
cp "${REPO_DIR}/infra/systemd/saludpr-api.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable saludpr-api.service

echo "[deploy] Restarting API service..."
systemctl restart saludpr-api.service

sleep 2
if systemctl is-active --quiet saludpr-api.service; then
    echo "[deploy] ✅ Backend deployed successfully"
    systemctl status saludpr-api.service --no-pager -l | head -15
else
    echo "[deploy] ❌ Service failed to start"
    journalctl -u saludpr-api.service --no-pager -n 30
    exit 1
fi
