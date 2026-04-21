# Database Schema

PostgreSQL 16 + PostGIS 3.4.

All tables use `snake_case`. Timestamps are `TIMESTAMPTZ` (always UTC, display in AST via app layer). Primary keys are bigints except `municipalities.id` which uses the official FIPS-like PR municipality code.

---

## ER diagram (logical)

```
┌────────────────────┐         ┌──────────────────────┐
│  municipalities    │◄────────│  health_metrics      │
│  (78 rows)         │   n:1   │                      │
│                    │         │  (muni × indicator × │
│  id (PR code) PK   │         │   year)              │
│  name              │         │                      │
│  region            │         │  source_id FK        │
│  geometry (PostGIS)│         └──────────────────────┘
│  population_latest │
│  ...               │◄────────┐
└────────────────────┘         │
         ▲                     │
         │ n:1                 │ n:1
         │                     │
┌────────┴───────────┐  ┌──────┴──────────────┐
│  hospitals         │  │  vulnerability       │
│                    │  │                      │
│  id PK             │  │  muni_id FK         │
│  name              │  │  year               │
│  muni_id FK        │  │  index_score        │
│  location (Point)  │  │  source_id FK       │
│  beds              │  └─────────────────────┘
│  is_active         │
│  source_id FK      │
└────────────────────┘

┌────────────────────┐         ┌──────────────────────┐
│  data_sources      │◄────────│  etl_runs            │
│                    │    1:n  │                      │
│  id PK             │         │  source_id FK        │
│  slug (UNIQUE)     │         │  started_at          │
│  name              │         │  finished_at         │
│  url               │         │  rows_upserted       │
│  license           │         │  status              │
│  last_pulled_at    │         │  error_message       │
└────────────────────┘         └──────────────────────┘
```

---

## Tables

### `municipalities`
The 78 official Puerto Rico municipalities. Loaded once from Census TIGER/Line shapefiles. This is a reference table — rarely changes.

| Column | Type | Notes |
|---|---|---|
| `id` | `VARCHAR(5)` PK | PR municipality code (e.g. `72127` for San Juan) |
| `name` | `TEXT NOT NULL` | Official name (e.g. "San Juan") |
| `name_normalized` | `TEXT NOT NULL` | Lowercase, no accents — for search |
| `region` | `TEXT` | PR DoH health region (7 total) |
| `geometry` | `GEOMETRY(MultiPolygon, 4326)` | WGS84 boundary |
| `centroid` | `GEOGRAPHY(Point, 4326)` | Computed; used for labels |
| `area_sq_km` | `NUMERIC(10,2)` | Computed |
| `population_latest` | `INTEGER` | Most recent Census ACS estimate |
| `population_year` | `SMALLINT` | Year of the population figure |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |
| `updated_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |

**Indexes:**
- `GIST(geometry)` — spatial queries
- `GIST(centroid)` — point-in-polygon, nearest
- `btree(name_normalized)` — autocomplete

---

### `data_sources`
Every external dataset we pull from. Referenced by every metric row — nothing goes into the DB without a source.

| Column | Type | Notes |
|---|---|---|
| `id` | `BIGSERIAL` PK | |
| `slug` | `TEXT UNIQUE NOT NULL` | e.g. `cdc_brfss`, `hrsa_mua` |
| `name` | `TEXT NOT NULL` | Human-readable |
| `organization` | `TEXT NOT NULL` | e.g. "Centers for Disease Control" |
| `url` | `TEXT NOT NULL` | Public landing page |
| `license` | `TEXT NOT NULL` | e.g. "Public Domain (US Federal)" |
| `update_frequency` | `TEXT` | e.g. "Annual", "Quarterly" |
| `description_en` | `TEXT` | |
| `description_es` | `TEXT` | |
| `known_limitations` | `TEXT` | Self-reported, small samples, etc. |
| `last_pulled_at` | `TIMESTAMPTZ` | Updated by ETL runs |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |

**Indexes:**
- `UNIQUE(slug)` (implicit)

---

### `etl_runs`
Provenance and ops log. Every ETL execution leaves a trace here.

| Column | Type | Notes |
|---|---|---|
| `id` | `BIGSERIAL` PK | |
| `source_id` | `BIGINT NOT NULL REFERENCES data_sources(id)` | |
| `started_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |
| `finished_at` | `TIMESTAMPTZ` | NULL if in progress |
| `status` | `TEXT NOT NULL` | `running`, `success`, `failed`, `partial` |
| `rows_read` | `INTEGER` | From source |
| `rows_upserted` | `INTEGER` | Into target table |
| `rows_skipped` | `INTEGER` | Validation failures |
| `error_message` | `TEXT` | If failed |
| `git_sha` | `VARCHAR(40)` | Code version that ran the ETL |

**Indexes:**
- `btree(source_id, started_at DESC)` — "show me the latest run for X"

---

### `health_metrics`
The core fact table. One row per (municipality, indicator, year).

| Column | Type | Notes |
|---|---|---|
| `id` | `BIGSERIAL` PK | |
| `muni_id` | `VARCHAR(5) NOT NULL REFERENCES municipalities(id)` | |
| `indicator_code` | `TEXT NOT NULL` | e.g. `diabetes_adult_prevalence`, `hypertension_adult_prevalence`, `asthma_adult_prevalence` |
| `year` | `SMALLINT NOT NULL` | |
| `value` | `NUMERIC(10,4)` | The rate/count; NULL = suppressed |
| `value_type` | `TEXT NOT NULL` | `percent`, `rate_per_100k`, `count`, `index` |
| `numerator` | `INTEGER` | If available |
| `denominator` | `INTEGER` | If available |
| `ci_lower` | `NUMERIC(10,4)` | 95% confidence interval lower bound |
| `ci_upper` | `NUMERIC(10,4)` | Upper bound |
| `is_suppressed` | `BOOLEAN NOT NULL DEFAULT false` | Small cell size |
| `is_estimated` | `BOOLEAN NOT NULL DEFAULT false` | Modeled vs. direct |
| `source_id` | `BIGINT NOT NULL REFERENCES data_sources(id)` | |
| `etl_run_id` | `BIGINT REFERENCES etl_runs(id)` | Which run inserted this |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |
| `updated_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |

**Constraints:**
- `UNIQUE(muni_id, indicator_code, year, source_id)` — no dupes per source
- `CHECK(value IS NULL OR value >= 0)` — no negative rates
- `CHECK(ci_lower IS NULL OR ci_upper IS NULL OR ci_lower <= ci_upper)` — valid CI

**Indexes:**
- `btree(indicator_code, year)` — for "all diabetes in 2023"
- `btree(muni_id, indicator_code)` — for "all diabetes history in Ponce"

---

### `hospitals`
Licensed healthcare facilities with geolocation and capacity.

| Column | Type | Notes |
|---|---|---|
| `id` | `BIGSERIAL` PK | |
| `external_id` | `TEXT` | CMS provider ID or PRDOH license # |
| `name` | `TEXT NOT NULL` | |
| `muni_id` | `VARCHAR(5) NOT NULL REFERENCES municipalities(id)` | |
| `facility_type` | `TEXT NOT NULL` | `general`, `specialty`, `critical_access`, `chc` |
| `location` | `GEOGRAPHY(Point, 4326) NOT NULL` | Geocoded |
| `address` | `TEXT` | |
| `total_beds` | `INTEGER` | |
| `staffed_beds` | `INTEGER` | |
| `has_emergency_dept` | `BOOLEAN` | |
| `is_active` | `BOOLEAN NOT NULL DEFAULT true` | |
| `source_id` | `BIGINT NOT NULL REFERENCES data_sources(id)` | |
| `etl_run_id` | `BIGINT REFERENCES etl_runs(id)` | |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |
| `updated_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |

**Constraints:**
- `UNIQUE(external_id, source_id)` — idempotent upserts
- `CHECK(total_beds IS NULL OR total_beds >= 0)`

**Indexes:**
- `GIST(location)` — "hospitals within X km"
- `btree(muni_id)` — hospitals by municipality

---

### `vulnerability`
Social vulnerability + disaster risk index from Census CRE.

| Column | Type | Notes |
|---|---|---|
| `id` | `BIGSERIAL` PK | |
| `muni_id` | `VARCHAR(5) NOT NULL REFERENCES municipalities(id)` | |
| `year` | `SMALLINT NOT NULL` | |
| `index_score` | `NUMERIC(6,3)` | 0–100 normalized |
| `low_pct` | `NUMERIC(5,2)` | % population low vulnerability |
| `medium_pct` | `NUMERIC(5,2)` | % population medium |
| `high_pct` | `NUMERIC(5,2)` | % population high |
| `disaster_risk_score` | `NUMERIC(6,3)` | FEMA NRI overlay |
| `source_id` | `BIGINT NOT NULL REFERENCES data_sources(id)` | |
| `etl_run_id` | `BIGINT REFERENCES etl_runs(id)` | |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |

**Constraints:**
- `UNIQUE(muni_id, year, source_id)`
- `CHECK(low_pct + medium_pct + high_pct BETWEEN 99.0 AND 101.0)` — rounding tolerance

---

## Views (convenience)

### `v_latest_metrics`
Most recent year available per (muni, indicator). Used heavily by the API's map endpoint.

### `v_source_freshness`
Per-source age of the most recent data. Powers the `/api/sources` freshness badge.

---

## Extensions required

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS unaccent;  -- for name_normalized
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- fuzzy search on muni names
```

---

## Migration strategy

- **Alembic** manages all schema changes
- Every migration file follows convention `YYYY_MM_DD_HHMM_<slug>.py`
- Never edit an applied migration; add a new one
- Production migrations run via `alembic upgrade head` in the deploy pipeline
- Data backfills go in `etl/` scripts, NOT in migrations
