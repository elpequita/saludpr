# SaludPR Backend

FastAPI service that serves aggregated public health data for Puerto Rico.

## Stack

- Python 3.12
- FastAPI + Uvicorn
- SQLAlchemy 2.x
- Pydantic v2
- PostgreSQL 16 + PostGIS

## Local development

```bash
# From repo root
cd backend

# Create virtualenv
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your local Postgres credentials

# Run migrations (TBD — Alembic)
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 8000
```

API will be at http://localhost:8000
Interactive docs at http://localhost:8000/docs

## Project layout

```
backend/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py            # Settings (Pydantic BaseSettings)
│   ├── database.py          # SQLAlchemy session
│   ├── models/              # ORM models
│   ├── schemas/             # Pydantic response schemas
│   ├── routers/             # API route modules
│   │   ├── health.py
│   │   ├── municipalities.py
│   │   ├── metrics.py
│   │   ├── hospitals.py
│   │   └── sources.py
│   └── services/            # Business logic
├── alembic/                 # Database migrations
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

## Endpoints (planned)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Uptime check |
| GET | `/api/municipalities` | List 78 municipalities + GeoJSON |
| GET | `/api/municipalities/{id}` | Detail for one municipality |
| GET | `/api/metrics/{indicator}` | Disease rates across all munis |
| GET | `/api/metrics/{indicator}/{muni_id}` | Single muni + trend |
| GET | `/api/hospitals` | All hospitals with geo + capacity |
| GET | `/api/vulnerability` | Resilience + disaster risk index |
| GET | `/api/sources` | Data provenance manifest |
