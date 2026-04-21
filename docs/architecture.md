# Architecture

## High-level diagram

```
┌──────────────────────────────────────────────────────────┐
│  USER (browser, desktop or mobile)                       │
└──────────────────────┬───────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼───────────────────────────────────┐
│  FRONTEND — Vercel (Edge CDN, global)                    │
│  Next.js 15 · App Router · React 19 · TypeScript strict  │
│  Tailwind 4 · shadcn/ui · Mapbox GL · Visx · Motion      │
│  next-intl (EN/ES) · TanStack Query · Zod validation     │
│  MDX for /methodology                                    │
└──────────────────────┬───────────────────────────────────┘
                       │ REST (JSON, runtime-validated)
                       │ api.saludpr.org or /api proxy
┌──────────────────────▼───────────────────────────────────┐
│  REVERSE PROXY — Nginx (Azure VM, Linux)                 │
│  TLS termination (Let's Encrypt auto-renew)              │
│  Rate limiting (100 req/min/IP), gzip, static caching    │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│  BACKEND API — FastAPI (Uvicorn, systemd)                │
│  Python 3.12 · SQLAlchemy 2 · Pydantic 2                 │
│  Endpoints:                                              │
│    GET /api/health                                       │
│    GET /api/municipalities          → GeoJSON + stats    │
│    GET /api/municipalities/:id                           │
│    GET /api/metrics/:indicator                           │
│    GET /api/metrics/:indicator/:muniId                   │
│    GET /api/hospitals                                    │
│    GET /api/vulnerability                                │
│    GET /api/sources                 → provenance manifest│
└──────────────────────┬───────────────────────────────────┘
                       │ SQLAlchemy
┌──────────────────────▼───────────────────────────────────┐
│  DATABASE — PostgreSQL 16 + PostGIS (Azure VM, localhost)│
│  Tables:                                                 │
│    municipalities (+ geometry)                           │
│    health_metrics                                        │
│    hospitals (+ geography point)                         │
│    vulnerability                                         │
│    data_sources  ← provenance, always cited              │
│    etl_runs      ← every pipeline execution logged       │
└──────────────────────▲───────────────────────────────────┘
                       │ Scheduled upserts
                       │
┌──────────────────────┴───────────────────────────────────┐
│  ETL PIPELINE — Python 3.12 + cron                       │
│  pandas · geopandas · requests · Pydantic validation     │
│  One module per source under etl/sources/                │
│  Orchestrator: etl/scripts/refresh_all.py (quarterly)    │
└──────────────────────▲───────────────────────────────────┘
                       │ HTTPS
┌──────────────────────┴───────────────────────────────────┐
│  PUBLIC DATA SOURCES                                     │
│  CDC BRFSS · HRSA MUA/P · HRSA AHRF · US Census (ACS)    │
│  Census CRE · PR Dept of Health · CMS Provider Data      │
└──────────────────────────────────────────────────────────┘
```

## Why this stack

**Next.js 15** — Server-rendered pages mean SaludPR is indexable (critical for a credibility/discovery play), loads fast on slow connections (common in rural PR), and the App Router pairs naturally with `next-intl` for bilingual routing (`/en/...` and `/es/...`).

**shadcn/ui + Tailwind 4** — Accessible Radix primitives where we own the source. No black-box component library. Codex can audit it cleanly.

**Mapbox GL via react-map-gl** — Vector tile choropleth performs smoothly on mobile; Leaflet's raster approach struggles with 78-municipality fills at high zoom.

**TanStack Query + Zod** — Server-first caching with runtime response validation. If the FastAPI schema drifts, Zod throws in dev before users see broken charts.

**Visx + Recharts** — Visx for bespoke, editorial-quality visuals (histograms, beeswarms, custom annotations); Recharts as escape hatch for quick standard charts.

**FastAPI + PostgreSQL + PostGIS** — Python's geospatial ecosystem is unmatched for ETL, and PostGIS does heavy geographic work at DB level.

## Deployment targets

| Component | Host | Monthly cost |
|---|---|---|
| Frontend | Vercel | $0 (free tier) |
| Backend | Azure VM (existing) | $0 incremental |
| Database | Same VM (localhost Postgres) | $0 |
| ETL | Same VM (cron) | $0 |
| Domain | Cloudflare Registrar | ~$10/year |
| Mapbox | Free tier | $0 up to 50k loads/month |

**Net additional cost: ~$1/month for the domain.** The Azure VM you wanted to monetize becomes the backbone of a public-good project — way better than a resume reviewer site for your credibility.

## Security

- All secrets in `.env` files, never committed.
- Postgres listens on localhost only; backend uses non-superuser app role.
- API rate-limited at Nginx layer.
- No PII stored — aggregated public data only.
- HTTPS-only with HSTS.
- Security headers: X-Frame-Options, X-Content-Type-Options, Referrer-Policy.
- `fail2ban` for SSH brute-force protection.
- Dependabot + GitHub security alerts on both repos.

## Observability

- Structured JSON logs from FastAPI to `/var/log/saludpr/`.
- `etl_runs` table records every pipeline execution.
- UptimeRobot free tier pinging `/api/health` every 5 min.
- Vercel Analytics (free) for frontend vitals.
- Optional Sentry free tier post-launch.

## Quality gates (Codex-audit ready)

### Frontend
- `tsconfig.json` with `strict: true`, `noUncheckedIndexedAccess`, `noImplicitOverride`
- ESLint + `eslint-config-next` + Prettier
- `vitest` + `@testing-library/react` for components
- No `any`, no `@ts-ignore` without written justification

### Backend
- `ruff` with security (S), complexity (PL), and style rules enabled
- `mypy --strict` passing
- `pytest` with coverage threshold
- Every public function has a docstring

### CI (planned)
- GitHub Actions on every PR: lint + typecheck + test
- Vercel preview deploys on every PR
- Production deploys only on merge to `main`

## Scaling considerations (post-MVP)

- Frontend is SSG/ISR → scales infinitely via Vercel edge.
- Backend is read-heavy → add Redis cache if sustained >100 req/s.
- DB projected <1GB for years — no partitioning concerns.
- If Mapbox free tier exceeded, swap to self-hosted MapLibre + TileServer.
