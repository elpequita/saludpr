# SaludPR 🏥

[English](#english) · [Español](#español)

---

## English

**SaludPR** is a free, bilingual, open public health dashboard for Puerto Rico.

It visualizes chronic disease rates, hospital capacity, and medically underserved zones across the island's 78 municipalities — using only publicly available data from trusted sources (CDC, HRSA, US Census, PR Department of Health, CMS).

### Why this exists

Puerto Rico has persistently higher rates of chronic conditions — diabetes, hypertension, cardiovascular disease — than any U.S. state. Yet health data about the island is fragmented, inconsistently collected, and rarely presented in a way that residents, journalists, policymakers, or community leaders can actually use.

SaludPR closes that gap.

### What it shows

- 📊 Chronic disease rates by municipality (diabetes, hypertension, asthma, cardiovascular)
- 🏥 Hospital bed capacity and geographic distribution
- 🗺️ Medically underserved areas (HRSA designation)
- ⚠️ Social vulnerability + disaster risk overlay
- 📈 Trends over time (pre/post Hurricane María, earthquakes, COVID-19)

### Tech stack

- **Frontend:** Next.js 15 · TypeScript (strict) · Tailwind CSS 4 · shadcn/ui · Mapbox GL · Visx · Motion · TanStack Query · next-intl
- **Backend:** FastAPI · SQLAlchemy 2 · Pydantic v2
- **Database:** PostgreSQL 16 with PostGIS
- **ETL:** Python (pandas, geopandas, requests) — scheduled via cron
- **Hosting:** Frontend on Vercel · Backend + DB on Azure VM (Linux)

### Data sources

Every number in SaludPR is traceable to a public source. See [`docs/data-sources.md`](docs/data-sources.md) for the complete list with direct links, pull dates, and methodology notes.

### Built by

[Dataurea](https://www.dataurea.com) — A Puerto Rico-based data analytics company founded by Carlos A. Perez Medina, Healthcare Data Analyst.

### License

- **Code:** [MIT](LICENSE)
- **Content & aggregated data:** [CC BY 4.0](LICENSE-CONTENT)

---

## Español

**SaludPR** es un panel público de salud gratuito y bilingüe para Puerto Rico.

Visualiza tasas de enfermedades crónicas, capacidad hospitalaria y zonas médicamente desatendidas en los 78 municipios de la isla — usando solamente datos públicos de fuentes confiables (CDC, HRSA, Censo de EE.UU., Departamento de Salud de PR, CMS).

### Por qué existe

Puerto Rico tiene tasas persistentemente más altas de condiciones crónicas — diabetes, hipertensión, enfermedades cardiovasculares — que cualquier estado de EE.UU. Sin embargo, los datos de salud de la isla están fragmentados, se recopilan de manera inconsistente y rara vez se presentan de forma que residentes, periodistas, formuladores de política o líderes comunitarios puedan usar.

SaludPR cierra esa brecha.

### Qué muestra

- 📊 Tasas de enfermedades crónicas por municipio (diabetes, hipertensión, asma, cardiovascular)
- 🏥 Capacidad de camas hospitalarias y distribución geográfica
- 🗺️ Áreas médicamente desatendidas (designación HRSA)
- ⚠️ Vulnerabilidad social + riesgo de desastres
- 📈 Tendencias en el tiempo (antes/después del huracán María, terremotos, COVID-19)

### Creado por

[Dataurea](https://www.dataurea.com) — Empresa de análisis de datos basada en Puerto Rico, fundada por Carlos A. Perez Medina, Analista de Datos de Salud.

---

## Project status

🚧 **Active development** — planning phase started April 2026. Target MVP launch: Summer 2026.

See [`docs/roadmap.md`](docs/roadmap.md) for milestones.

## Contributing

This is a public-good project. Contributions, data corrections, and translations are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Contact

- Email: carlos.perez@dataurea.com
- Website: [dataurea.com](https://www.dataurea.com)
