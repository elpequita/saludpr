"""Load CDC PLACES county-level chronic-disease estimates for Puerto Rico.

PLACES publishes model-based prevalence estimates derived from BRFSS survey data
projected to the county (municipio) level. For Puerto Rico, LocationID is the
5-digit FIPS code which matches our municipalities.id column exactly.

Dataset: PLACES — Local Data for Better Health, County Data (long / tall format).
Each row is one county × one measure × one value-type (crude or age-adjusted).

We filter to:
  - StateAbbr = 'PR'
  - DataValueTypeID = 'AgeAdjPrv'   (age-adjusted; better for cross-muni comparison)
  - MeasureId in our curated list

All values are flagged is_estimated=true (PLACES values are model outputs, not direct
observations).

API:    https://data.cdc.gov/resource/swc5-untb.json
Portal: https://www.cdc.gov/places/
SODA:   https://dev.socrata.com/foundry/chronicdata.cdc.gov/swc5-untb

Run:
    cd etl && uv run python -m sources.cdc_places_county
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import requests
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential

from lib.db import session_scope
from lib.logging import get_logger
from lib.tracker import EtlRunTracker

log = get_logger(__name__)

# We track PLACES data under the `cdc_brfss` source record — PLACES is a
# derivative product of BRFSS, and this keeps provenance simple.
SOURCE_SLUG = "cdc_brfss"

PLACES_API_URL = "https://data.cdc.gov/resource/swc5-untb.json"

# Age-adjusted prevalence (percent) — best for comparing munis of different age profiles.
# Alternative: "CrdPrv" (crude prevalence) — matches the raw population exactly.
DATA_VALUE_TYPE_ID = "AgeAdjPrv"

# Map: PLACES MeasureId -> our indicator_code in health_metrics.
# See https://www.cdc.gov/places/measure-definitions/ for definitions.
MEASURE_MAP: dict[str, str] = {
    # Chronic conditions
    "DIABETES": "diabetes_adult_prevalence",
    "BPHIGH": "hypertension_adult_prevalence",
    "CASTHMA": "asthma_adult_prevalence",
    "CHD": "coronary_heart_disease_adult_prevalence",
    "STROKE": "stroke_adult_prevalence",
    "CANCER": "cancer_adult_prevalence",
    "COPD": "copd_adult_prevalence",
    "OBESITY": "obesity_adult_prevalence",
    "HIGHCHOL": "high_cholesterol_adult_prevalence",
    "KIDNEY": "chronic_kidney_disease_adult_prevalence",
    "ARTHRITIS": "arthritis_adult_prevalence",
    # Behaviors / risk factors
    "CSMOKING": "smoking_adult_prevalence",
    "BINGE": "binge_drinking_adult_prevalence",
    "LPA": "no_leisure_physical_activity_adult_prevalence",
    # Prevention / access
    "ACCESS2": "no_health_insurance_adult_prevalence",
    "CHECKUP": "routine_checkup_adult_prevalence",
    # Mental health
    "DEPRESSION": "depression_adult_prevalence",
}

# Page size for Socrata requests
PAGE_LIMIT = 10_000


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _fetch_page(offset: int) -> list[dict[str, Any]]:
    params = {
        "StateAbbr": "PR",
        "DataValueTypeID": DATA_VALUE_TYPE_ID,
        "$limit": str(PAGE_LIMIT),
        "$offset": str(offset),
    }
    r = requests.get(PLACES_API_URL, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def fetch_places_pr() -> list[dict[str, Any]]:
    """Fetch all PLACES county-level rows for Puerto Rico (age-adjusted)."""
    log.info(
        "Fetching PLACES county data (StateAbbr=PR, DataValueTypeID=%s)...",
        DATA_VALUE_TYPE_ID,
    )
    all_rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = _fetch_page(offset)
        if not page:
            break
        all_rows.extend(page)
        log.info("  fetched %d rows (total=%d)", len(page), len(all_rows))
        if len(page) < PAGE_LIMIT:
            break
        offset += PAGE_LIMIT
    log.info("Total PR rows received: %d", len(all_rows))
    return all_rows


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (ValueError, ArithmeticError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


UPSERT_SQL = text(
    """
    INSERT INTO health_metrics (
        muni_id, indicator_code, year,
        value, value_type, ci_lower, ci_upper,
        is_suppressed, is_estimated,
        source_id, etl_run_id, updated_at
    )
    VALUES (
        :muni_id, :indicator_code, :year,
        :value, 'percent', :ci_lower, :ci_upper,
        :is_suppressed, true,
        :source_id, :etl_run_id, now()
    )
    ON CONFLICT (muni_id, indicator_code, year, source_id) DO UPDATE SET
        value = EXCLUDED.value,
        ci_lower = EXCLUDED.ci_lower,
        ci_upper = EXCLUDED.ci_upper,
        is_suppressed = EXCLUDED.is_suppressed,
        is_estimated = EXCLUDED.is_estimated,
        etl_run_id = EXCLUDED.etl_run_id,
        updated_at = now()
    """
)


def _get_known_munis() -> set[str]:
    with session_scope() as s:
        rows = s.execute(text("SELECT id FROM municipalities")).all()
    return {r[0] for r in rows}


def main() -> None:
    known_munis = _get_known_munis()
    if not known_munis:
        raise RuntimeError(
            "No municipalities in DB. Run the TIGER loader first: "
            "uv run python -m sources.census_tiger_municipalities"
        )
    log.info("Known municipalities in DB: %d", len(known_munis))

    with EtlRunTracker(source_slug=SOURCE_SLUG) as run:
        raw_rows = fetch_places_pr()
        run.rows_read = len(raw_rows)

        upserted = 0
        skipped = 0
        unmapped_measures: set[str] = set()
        unknown_munis: set[str] = set()

        with session_scope() as s:
            for row in raw_rows:
                measure_id = str(row.get("measureid", "")).strip()
                indicator_code = MEASURE_MAP.get(measure_id)
                if indicator_code is None:
                    unmapped_measures.add(measure_id)
                    skipped += 1
                    continue

                muni_id = str(row.get("locationid", "")).strip()
                if muni_id not in known_munis:
                    unknown_munis.add(muni_id)
                    skipped += 1
                    continue

                year = _to_int(row.get("year")) or 2023
                value = _to_decimal(row.get("data_value"))
                ci_low = _to_decimal(row.get("low_confidence_limit"))
                ci_high = _to_decimal(row.get("high_confidence_limit"))
                is_suppressed = value is None

                s.execute(
                    UPSERT_SQL,
                    {
                        "muni_id": muni_id,
                        "indicator_code": indicator_code,
                        "year": year,
                        "value": value,
                        "ci_lower": ci_low,
                        "ci_upper": ci_high,
                        "is_suppressed": is_suppressed,
                        "source_id": run.source_id,
                        "etl_run_id": run.run_id,
                    },
                )
                upserted += 1

        run.rows_upserted = upserted
        run.rows_skipped = skipped

        if unmapped_measures:
            log.info(
                "Skipped %d measures we don't track (first 10): %s",
                len(unmapped_measures),
                sorted(unmapped_measures)[:10],
            )
        if unknown_munis:
            log.warning(
                "Skipped %d rows with unknown muni IDs: %s",
                len(unknown_munis),
                sorted(unknown_munis)[:10],
            )
        log.info(
            "Upserted %d health_metric rows across %d indicators × ~78 munis",
            upserted,
            len(MEASURE_MAP),
        )


if __name__ == "__main__":
    main()
