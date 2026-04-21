#!/usr/bin/env bash
# =============================================================================
# SaludPR — Nginx + Let's Encrypt setup
#
# Run as root AFTER:
#   1. DNS for api.saludpr.org points to this VM's public IP
#   2. setup-vm.sh has run successfully
#   3. Repo is cloned to /opt/saludpr/repo
# =============================================================================

set -euo pipefail

readonly REPO_DIR="/opt/saludpr/repo"
readonly NGINX_CONF_SRC="${REPO_DIR}/infra/nginx/saludpr-api.conf"
readonly NGINX_CONF_DST="/etc/nginx/sites-available/saludpr-api"
readonly DOMAIN="${SALUDPR_API_DOMAIN:-api.saludpr.org}"
readonly EMAIL="${SALUDPR_CERT_EMAIL:-carlos.perez@dataurea.com}"

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: must run as root" >&2
    exit 1
fi

echo "[nginx] Installing config..."
cp "${NGINX_CONF_SRC}" "${NGINX_CONF_DST}"
ln -sf "${NGINX_CONF_DST}" /etc/nginx/sites-enabled/saludpr-api

# Prepare ACME challenge directory
install -d -o www-data -g www-data /var/www/certbot

# Remove default site if still present
rm -f /etc/nginx/sites-enabled/default

echo "[nginx] Testing config..."
nginx -t

echo "[nginx] Reloading..."
systemctl reload nginx

echo "[certbot] Requesting Let's Encrypt certificate for ${DOMAIN}..."
echo "  (make sure DNS A record points to this VM's public IP before continuing)"
read -rp "Press Enter to continue, Ctrl+C to abort..."

certbot --nginx \
    --non-interactive \
    --agree-tos \
    --email "${EMAIL}" \
    --domains "${DOMAIN}" \
    --redirect

echo "[nginx] ✅ Done. Certbot auto-renew is enabled via systemd timer."
systemctl list-timers certbot.timer --no-pager || true
