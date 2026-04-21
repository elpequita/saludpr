# SaludPR Infrastructure

Scripts and config for deploying SaludPR on an Ubuntu 24.04 Azure VM.

## Quick start (first-time setup)

```bash
# 1. SSH to the VM
ssh carlitosabdiel@<vm-ip>

# 2. Clone the repo (as root to /opt/saludpr/repo after user creation, or anywhere for now)
sudo mkdir -p /opt/saludpr
sudo git clone git@github.com:elpequita/saludpr.git /opt/saludpr/repo

# 3. Run VM provisioning — installs PostgreSQL, Python, Node, Nginx, creates users
sudo bash /opt/saludpr/repo/infra/scripts/setup-vm.sh

# 4. Transfer repo ownership to saludpr user
sudo chown -R saludpr:saludpr /opt/saludpr/repo

# 5. Deploy backend (installs deps, runs migrations, starts systemd service)
sudo bash /opt/saludpr/repo/infra/scripts/deploy-backend.sh

# 6. (After pointing DNS for api.saludpr.org) Configure Nginx + TLS
sudo SALUDPR_API_DOMAIN=api.saludpr.org \
     SALUDPR_CERT_EMAIL=carlos.perez@dataurea.com \
     bash /opt/saludpr/repo/infra/scripts/setup-nginx.sh
```

## Contents

| Path | Purpose |
|---|---|
| `scripts/setup-vm.sh` | One-time VM provisioning (idempotent) |
| `scripts/deploy-backend.sh` | Pull → install → migrate → restart |
| `scripts/setup-nginx.sh` | Nginx config + Let's Encrypt cert |
| `systemd/saludpr-api.service` | FastAPI as a systemd service |
| `nginx/saludpr-api.conf` | Reverse proxy config with rate limiting |

## Subsequent deploys

Once everything is set up, every deploy is just:

```bash
sudo bash /opt/saludpr/repo/infra/scripts/deploy-backend.sh
```

That pulls latest `main`, installs any new deps, runs any pending migrations, and restarts the service.

## Useful ops commands

```bash
# Check API status
sudo systemctl status saludpr-api

# Tail logs
sudo journalctl -u saludpr-api -f
# or
sudo tail -f /var/log/saludpr/api.log

# Restart API
sudo systemctl restart saludpr-api

# Connect to DB as admin
sudo -u postgres psql saludpr

# Test API locally on the VM
curl http://127.0.0.1:8000/api/health

# Test API via public domain
curl https://api.saludpr.org/api/health

# Nginx reload after config change
sudo nginx -t && sudo systemctl reload nginx

# Certbot renewal test
sudo certbot renew --dry-run
```

## Where secrets live

| File | Who reads it |
|---|---|
| `/root/saludpr-db-credentials.txt` | Root only (mode 600). Source of truth for the DB URL. |
| `/opt/saludpr/repo/backend/.env` | `saludpr` user only. Created by `deploy-backend.sh` from the root file. |

Never commit either to git.

## Why this setup

- **systemd, not Docker** — one VM, no orchestration overhead, easier to debug. We can containerize later if the project scales.
- **uv instead of pip** — much faster dep installs, lock file (`uv.lock`) guarantees reproducibility.
- **Nginx in front of Uvicorn** — TLS termination, rate limiting, gzip, security headers. Uvicorn stays on localhost.
- **fail2ban + UFW** — basic defense against SSH brute-force and random port scans.
- **Stricter systemd sandboxing** — `ProtectSystem=strict`, `NoNewPrivileges`, etc. Limits blast radius of any backend compromise.
