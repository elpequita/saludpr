#!/usr/bin/env bash
# =============================================================================
# SaludPR — Local Development Environment Setup
# Target: Ubuntu 24.04 (local VirtualBox or WSL)
#
# Installs:
#   - PostgreSQL 16 + PostGIS 3
#   - Python 3.12 (already in 24.04) + uv
#   - Node.js 20 LTS + pnpm
#
# Creates:
#   - saludpr_dev database (local only)
#   - A role using your Linux username (for passwordless local connection)
#   - backend/.env configured for local development
#
# Run from the repo root:
#   bash infra/scripts/setup-local-dev.sh
#
# This script is SAFE to rerun — every step is idempotent.
# =============================================================================

set -euo pipefail

readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'

log()   { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $*"; }
warn()  { echo -e "${YELLOW}[$(date +%H:%M:%S)] WARN:${NC} $*"; }
error() { echo -e "${RED}[$(date +%H:%M:%S)] ERROR:${NC} $*" >&2; }

readonly LOCAL_USER="${USER:-$(whoami)}"
readonly DB_NAME="saludpr_dev"

# --- Must NOT run as root (we want passwordless access for current user) ---
if [[ $EUID -eq 0 ]]; then
    error "Do NOT run this as root. Run as your normal user; it will prompt for sudo when needed."
    exit 1
fi

# --- Must run from repo root ---
if [[ ! -f "backend/pyproject.toml" ]] || [[ ! -d "infra/scripts" ]]; then
    error "Run this script from the saludpr repo root, e.g.:"
    error "  cd ~/Coding/saludpr && bash infra/scripts/setup-local-dev.sh"
    exit 1
fi

log "Setting up SaludPR local dev environment for user: ${LOCAL_USER}"
log "This will require your sudo password for package installs."
echo

# =============================================================================
# 1. Base packages
# =============================================================================
log "Updating apt and installing base packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    build-essential curl wget git unzip \
    ca-certificates gnupg lsb-release \
    software-properties-common

# =============================================================================
# 2. PostgreSQL 16 + PostGIS 3
# =============================================================================
log "Installing PostgreSQL 16 + PostGIS..."

# Add official PostgreSQL apt repo (idempotent)
if [[ ! -f /etc/apt/sources.list.d/pgdg.list ]]; then
    sudo install -d /usr/share/postgresql-common/pgdg
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc |
        sudo tee /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc >/dev/null
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] \
https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" |
        sudo tee /etc/apt/sources.list.d/pgdg.list >/dev/null
    sudo apt-get update -qq
fi

sudo apt-get install -y -qq \
    postgresql-16 \
    postgresql-16-postgis-3 \
    postgresql-16-postgis-3-scripts \
    postgresql-contrib-16 \
    libpq-dev

sudo systemctl enable --now postgresql

# --- Create a DB role matching the current Linux user (peer auth -> no password locally) ---
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${LOCAL_USER}'" | grep -q 1; then
    log "Creating PostgreSQL role: ${LOCAL_USER}"
    sudo -u postgres createuser --superuser "${LOCAL_USER}"
else
    log "PostgreSQL role '${LOCAL_USER}' already exists"
fi

# --- Create the dev database ---
if ! psql -lqt | cut -d \| -f 1 | tr -d ' ' | grep -qx "${DB_NAME}"; then
    log "Creating database: ${DB_NAME}"
    createdb "${DB_NAME}"
else
    log "Database '${DB_NAME}' already exists"
fi

# --- Enable extensions ---
log "Enabling PostGIS + helper extensions in ${DB_NAME}..."
psql -d "${DB_NAME}" -v ON_ERROR_STOP=1 <<'SQL' >/dev/null
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
SQL

# =============================================================================
# 3. Python 3.12 + uv
# =============================================================================
log "Installing Python 3.12 + uv..."
sudo apt-get install -y -qq \
    python3.12 python3.12-venv python3.12-dev \
    python3-pip pipx

if ! command -v uv >/dev/null 2>&1; then
    log "Installing uv (fast Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # shellcheck source=/dev/null
    source "${HOME}/.local/bin/env" 2>/dev/null || export PATH="${HOME}/.local/bin:${PATH}"
else
    log "uv already installed: $(uv --version)"
fi

# =============================================================================
# 4. Node.js 20 LTS + pnpm
# =============================================================================
log "Installing Node.js 20 LTS..."
if ! command -v node >/dev/null 2>&1 || [[ "$(node -v)" != v20* ]]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y -qq nodejs
fi

# Enable corepack (ships with Node 20) for pnpm
sudo corepack enable
corepack prepare pnpm@latest --activate

# =============================================================================
# 5. Create backend/.env for local dev
# =============================================================================
if [[ ! -f "backend/.env" ]]; then
    log "Creating backend/.env for local development..."
    cat > backend/.env <<EOF
# SaludPR Backend — LOCAL DEV (generated $(date -u +%Y-%m-%dT%H:%M:%SZ))
# Uses peer auth via your Linux user. No password needed locally.
DATABASE_URL=postgresql+psycopg://${LOCAL_USER}@localhost:5432/${DB_NAME}

APP_ENV=development
APP_DEBUG=true
APP_CORS_ORIGINS=http://localhost:3000

LOG_LEVEL=DEBUG
LOG_FORMAT=text

RATE_LIMIT_PER_MINUTE=1000
EOF
    chmod 600 backend/.env
    log "Created backend/.env (ignored by git)"
else
    warn "backend/.env already exists — leaving as-is. Delete it to regenerate."
fi

# =============================================================================
# 6. Create frontend/.env.local for local dev
# =============================================================================
if [[ ! -f "frontend/.env.local" ]]; then
    log "Creating frontend/.env.local for local development..."
    cat > frontend/.env.local <<'EOF'
# SaludPR Frontend — LOCAL DEV
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
NEXT_PUBLIC_MAPBOX_TOKEN=
NEXT_PUBLIC_DEFAULT_LOCALE=es
EOF
    log "Created frontend/.env.local"
    warn "You'll need to add a Mapbox token to frontend/.env.local"
    warn "  Get a free one at: https://account.mapbox.com/access-tokens/"
else
    warn "frontend/.env.local already exists — leaving as-is."
fi

# =============================================================================
# 7. Summary
# =============================================================================
echo
log "============================================================"
log " Local dev environment ready!"
log "============================================================"
echo
log " PostgreSQL 16:    $(sudo -u postgres psql -tAc 'SELECT version();' | head -c 60)..."
log " PostGIS version:  $(psql -d ${DB_NAME} -tAc 'SELECT PostGIS_Version();' | xargs)"
log " Python:           $(python3.12 --version)"
log " uv:               $(uv --version 2>/dev/null || echo 'NOT FOUND — reopen your shell')"
log " Node.js:          $(node --version)"
log " pnpm:             $(pnpm --version)"
echo
log " Database:         ${DB_NAME} (on localhost, peer-auth as ${LOCAL_USER})"
log " Backend env:      backend/.env"
log " Frontend env:     frontend/.env.local"
echo
log " Next steps:"
log "   1. If 'uv' wasn't found above, close and reopen your terminal"
log "   2. cd backend && uv sync"
log "   3. cd backend && uv run alembic upgrade head   # create tables"
log "   4. cd backend && uv run uvicorn app.main:app --reload"
log "   5. (In another terminal) cd frontend && pnpm install && pnpm dev"
echo
log "============================================================"
