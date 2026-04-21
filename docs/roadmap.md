# Roadmap

**Target MVP launch:** Summer 2026 (10 weeks from start)
**Commitment:** 10–20 hrs/week

---

## Phase 1 — Foundation (Weeks 1–2)

- [ ] Register domain (`saludpr.org` preferred)
- [ ] Create GitHub repo + initial structure ✅ *(this commit)*
- [ ] Set up Azure VM environment (PostgreSQL 16 + PostGIS, Python 3.12, Node 20, Nginx)
- [ ] Initialize FastAPI skeleton with `/api/health` endpoint
- [ ] Initialize React + Vite + TypeScript project
- [ ] Download PR TIGER/Line shapefiles → convert to GeoJSON
- [ ] Deploy "Hello PR" interactive map (all 78 municipalities clickable)

## Phase 2 — Data Pipeline (Weeks 3–4)

- [ ] Design PostgreSQL schema (`docs/schema.md`)
- [ ] Build ETL module for CDC BRFSS (diabetes, hypertension, asthma)
- [ ] Build ETL module for HRSA MUA/P designations
- [ ] Build ETL module for PR DoH hospital registry
- [ ] Build ETL module for Census ACS + Community Resilience Estimates
- [ ] Populate `data_sources` provenance table
- [ ] Set up cron jobs for quarterly refresh

## Phase 3 — Core Dashboard (Weeks 5–6)

- [ ] Interactive choropleth map (color-coded by disease)
- [ ] Municipality detail side panel (stats, trends, PR-average comparison)
- [ ] Hospital pin layer with bed capacity popup
- [ ] Filter controls (year, disease, region)
- [ ] Responsive mobile layout
- [ ] Chart library for trends (Recharts)

## Phase 4 — Bilingual & Polish (Weeks 7–8)

- [ ] i18next setup with EN/ES dictionaries
- [ ] Translate all UI strings (natural Spanish, not machine)
- [ ] Accessibility audit (WCAG AA, screen readers, keyboard nav)
- [ ] `/about` page with Dataurea attribution
- [ ] `/methodology` page (auto-generated from `data_sources.md`)
- [ ] `/api/sources` endpoint exposing provenance
- [ ] Open Graph + Twitter Card meta tags
- [ ] Favicon + logo

## Phase 5 — Launch (Weeks 9–10)

- [ ] Domain DNS cutover
- [ ] TLS certificate (Let's Encrypt)
- [ ] Performance pass (Lighthouse >90)
- [ ] Press kit (EN + ES) with screenshots
- [ ] Outreach list:
  - El Nuevo Día
  - Centro de Periodismo Investigativo
  - Telemundo PR
  - Metro Puerto Rico
  - PR Public Health Association
  - Asociación de Salud Primaria de PR
  - Relevant legislators
  - HRSA + CDC regional contacts
- [ ] Soft launch to community (LinkedIn, Twitter/X, Reddit r/PuertoRico)
- [ ] Monitor uptime for first 72h

---

## Post-MVP ideas (parking lot — do NOT build in v1)

- Mental health / behavioral health layer
- Environmental health overlay (air quality, water)
- Food desert mapping
- Pharmacy access
- Insurance coverage trends
- API for researchers
- Email newsletter digest
- Mobile app
- Historical time-lapse animation

---

## Grant application parallel track

- [ ] HRSA Rural Health Innovation grant — research deadlines
- [ ] CDC Data Modernization Initiative — flagship fit
- [ ] Robert Wood Johnson Foundation — health equity focus
- [ ] CDBG-DR healthcare IT set-aside — PR-specific
