#!/usr/bin/env bash
# =============================================================================
# SaludPR — Azure VM Provisioning Script
# Target: Ubuntu 24.04 LTS (Noble Numbat)
#
# Installs and configures:
#   - System updates, UFW firewall, fail2ban
#   - PostgreSQL 16 + PostGIS 3
#   - Python 3.12 (default in 24.04)
#   - Node.js 20 LTS (for any server-side tooling)
#   - Nginx + Certbot (Let's Encrypt)
#   - Creates saludpr system user + directory layout
#
# Run as root or with sudo:
#   sudo bash setup-vm.sh
# =============================================================================

set -euo pipefail

# --- Colors for output ---
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'

log()   { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $*"; }
warn()  { echo -e "${YELLOW}[$(date +%H:%M:%S)] WARN:${NC} $*"; }
error() { echo -e "${RED}[$(date +%H:%M:%S)] ERROR:${NC} $*" >&2; }

# --- Must run as root ---
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (use sudo)"
    exit 1
fi

# --- Config ---
readonly SALUDPR_USER="saludpr"
readonly SALUDPR_HOME="/opt/saludpr"
readonly SALUDPR_DB_NAME="saludpr"
readonly SALUDPR_DB_USER="saludpr_app"
# The app-user DB password is generated below; save it to /root/saludpr-db-credentials.txt

# =============================================================================
# 1. System update & base packages
# =============================================================================
log "Updating apt and installing base packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq

apt-get install -y -qq \
    build-essential \
    curl wget git unzip \
    ca-certificates gnupg lsb-release \
    ufw fail2ban \
    htop tmux vim jq \
    software-properties-common

# =============================================================================
# 2. UFW firewall
# =============================================================================
log "Configuring UFW firewall..."
ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp comment "HTTP"
ufw allow 443/tcp comment "HTTPS"
ufw --force enable

# =============================================================================
# 3. fail2ban
# =============================================================================
log "Enabling fail2ban for SSH protection..."
systemctl enable --now fail2ban

# =============================================================================
# 4. PostgreSQL 16 + PostGIS 3
# =============================================================================
log "Installing PostgreSQL 16 + PostGIS..."

# Use official PostgreSQL apt repo for latest versions
install -d /usr/share/postgresql-common/pgdg
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc

echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] \
https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
    > /etc/apt/sources.list.d/pgdg.list

apt-get update -qq
apt-get install -y -qq \
    postgresql-16 \
    postgresql-16-postgis-3 \
    postgresql-16-postgis-3-scripts \
    postgresql-contrib-16

systemctl enable --now postgresql

# --- Create DB + app user with random password ---
if [[ ! -f /root/saludpr-db-credentials.txt ]]; then
    log "Generating database credentials (first run)..."
    SALUDPR_DB_PASSWORD="$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)"

    sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
CREATE DATABASE ${SALUDPR_DB_NAME};
CREATE USER ${SALUDPR_DB_USER} WITH PASSWORD '${SALUDPR_DB_PASSWORD}';
GRANT ALL PRIVILEGES ON DATABASE ${SALUDPR_DB_NAME} TO ${SALUDPR_DB_USER};
\c ${SALUDPR_DB_NAME}
GRANT ALL ON SCHEMA public TO ${SALUDPR_DB_USER};
SQL

    # Save credentials to root-only file
    cat > /root/saludpr-db-credentials.txt <<EOF
# SaludPR DB Credentials — generated $(date -u +%Y-%m-%dT%H:%M:%SZ)
# Keep this file secret. Never commit.
DATABASE_URL=postgresql+psycopg://${SALUDPR_DB_USER}:${SALUDPR_DB_PASSWORD}@localhost:5432/${SALUDPR_DB_NAME}
EOF
    chmod 600 /root/saludpr-db-credentials.txt
    log "DB credentials saved to /root/saludpr-db-credentials.txt"
else
    warn "DB credentials already exist at /root/saludpr-db-credentials.txt — skipping user creation"
fi

# --- Enable PostGIS in the saludpr database ---
log "Enabling PostGIS extensions in ${SALUDPR_DB_NAME} database..."
sudo -u postgres psql -d "${SALUDPR_DB_NAME}" -v ON_ERROR_STOP=1 <<SQL
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
GRANT ALL ON ALL TABLES IN SCHEMA public TO ${SALUDPR_DB_USER};
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO ${SALUDPR_DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${SALUDPR_DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${SALUDPR_DB_USER};
SQL

# --- Tune PostgreSQL for a small VM ---
# Safe defaults for a 2-4GB RAM machine
PG_CONF="/etc/postgresql/16/main/postgresql.conf"
if ! grep -q "# SaludPR tuning" "${PG_CONF}"; then
    log "Applying PostgreSQL tuning defaults..."
    cat >> "${PG_CONF}" <<'EOF'

# SaludPR tuning
shared_buffers = 512MB
effective_cache_size = 1GB
maintenance_work_mem = 128MB
work_mem = 16MB
random_page_cost = 1.1
effective_io_concurrency = 200
EOF
    systemctl restart postgresql
fi

# =============================================================================
# 5. Python 3.12 + uv (fast Python package manager)
# =============================================================================
log "Installing Python 3.12 + uv..."
apt-get install -y -qq \
    python3.12 python3.12-venv python3.12-dev \
    python3-pip pipx

# Install uv system-wide for fast dep installs (recommended for Codex audits too)
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
fi

# =============================================================================
# 6. Node.js 20 LTS
# =============================================================================
log "Installing Node.js 20 LTS..."
if ! command -v node >/dev/null 2>&1 || [[ "$(node -v)" != v20* ]]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -qq nodejs
fi

# Enable corepack for pnpm
corepack enable
corepack prepare pnpm@latest --activate

# =============================================================================
# 7. Nginx + Certbot
# =============================================================================
log "Installing Nginx + Certbot..."
apt-get install -y -qq nginx certbot python3-certbot-nginx
systemctl enable --now nginx

# =============================================================================
# 8. SaludPR system user + directory layout
# =============================================================================
log "Creating ${SALUDPR_USER} system user and directories..."

if ! id "${SALUDPR_USER}" &>/dev/null; then
    useradd --system --home "${SALUDPR_HOME}" --shell /bin/bash "${SALUDPR_USER}"
fi

install -d -o "${SALUDPR_USER}" -g "${SALUDPR_USER}" \
    "${SALUDPR_HOME}" \
    "${SALUDPR_HOME}/backend" \
    "${SALUDPR_HOME}/etl" \
    "${SALUDPR_HOME}/data" \
    /var/log/saludpr

# =============================================================================
# 9. Summary
# =============================================================================
log "============================================================"
log " SaludPR VM setup complete!"
log "============================================================"
log ""
log " PostgreSQL 16:    $(sudo -u postgres psql -tAc 'SELECT version();' | head -c 60)..."
log " PostGIS version:  $(sudo -u postgres psql -d ${SALUDPR_DB_NAME} -tAc 'SELECT PostGIS_Version();')"
log " Python:           $(python3.12 --version)"
log " Node.js:          $(node --version)"
log " Nginx:            $(nginx -v 2>&1)"
log ""
log " DB credentials:   /root/saludpr-db-credentials.txt"
log " App directory:    ${SALUDPR_HOME}"
log " App user:         ${SALUDPR_USER}"
log ""
log " Next steps:"
log "   1. Clone the saludpr repo to ${SALUDPR_HOME}/repo"
log "   2. Run: sudo bash ${SALUDPR_HOME}/repo/infra/scripts/deploy-backend.sh"
log "   3. Configure Nginx: sudo bash ${SALUDPR_HOME}/repo/infra/scripts/setup-nginx.sh"
log "   4. Run Alembic migrations: cd backend && uv run alembic upgrade head"
log ""
log "============================================================"
