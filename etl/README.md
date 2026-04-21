# SaludPR ETL

Python scripts that pull public data → transform → load into PostgreSQL.

## Principles

1. **Idempotent** — running the same script twice produces the same result.
2. **Traceable** — every row has a `source_id` and `pulled_at` timestamp.
3. **Validated** — schemas enforced via Pydantic before insert.
4. **Logged** — every run writes a record to `public.etl_runs`.

## Layout

```
etl/
├── sources/
│   ├── cdc_brfss.py
│   ├── hrsa_mua.py
│   ├── census_acs.py
│   ├── census_resilience.py
│   ├── prdoh_hospitals.py
│   └── cms_providers.py
├── lib/
│   ├── db.py                 # shared DB connection
│   ├── schemas.py            # Pydantic validation
│   └── logging.py
├── scripts/
│   ├── bootstrap_geo.py      # loads PR municipality shapefiles
│   └── refresh_all.py        # orchestrator (cron entrypoint)
├── requirements.txt
└── README.md
```

## Running

```bash
cd etl
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# One-time: load municipality boundaries
python scripts/bootstrap_geo.py

# Run a single source
python -m sources.cdc_brfss

# Run everything
python scripts/refresh_all.py
```

## Scheduling (production, via cron on Azure VM)

```cron
# Refresh all sources quarterly, 2am AST on 1st of Jan/Apr/Jul/Oct
0 2 1 1,4,7,10 * cd /opt/saludpr/etl && /opt/saludpr/etl/.venv/bin/python scripts/refresh_all.py >> /var/log/saludpr/etl.log 2>&1
```
