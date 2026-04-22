"""Load US Census ACS / PRCS data at the BARRIO level for Puerto Rico.

Uses the `county subdivision` geography which, in PR, corresponds to barrios.
Each ACS variable chunk returns a row per barrio with a 10-digit composite key:
state(2) + county(3) + county subdivision(5).

Expect significant suppression — barrios with small populations will have
many cells returned as sentinel-missing values. That's reality, not a bug.

Run:
    cd etl && uv run python -m sources.census_acs_barrios
"""

from __future__ import annotations

import requests
from sqlalchemy import text

from lib.acs_common import (
    PR_STATE_FIPS,
    VARIABLES,
    YEARS,
    all_acs_variables,
    compute_value,
    fetch_acs_year,
)
from lib.db import session_scope
from lib.logging import get_logger
from lib.tracker import EtlRunTracker

log = get_logger(__name__)

SOURCE_SLUG = "census_acs"
# `for=county subdivision:*&in=state:72 county:*` returns all barrios in all PR munis.
GEOGRAPHY = (
    "for=county subdivision:*&"
    f"in=state:{PR_STATE_FIPS}&"
    "in=county:*"
)


UPSERT_SQL = text(
    """
    INSERT INTO barrio_health_metrics (
        barrio_id, indicator_code, year,
        value, value_type, numerator, denominator,
        is_suppressed, is_estimated,
        source_id, etl_run_id, updated_at
    )
    VALUES (
        :barrio_id, :indicator_code, :year,
        :value, :value_type, :numerator, :denominator,
        :is_suppressed, false,
        :source_id, :etl_run_id, now()
    )
    ON CONFLICT (barrio_id, indicator_code, year, source_id) DO UPDATE SET
        value = EXCLUDED.value,
        numerator = EXCLUDED.numerator,
        denominator = EXCLUDED.denominator,
        is_suppressed = EXCLUDED.is_suppressed,
        etl_run_id = EXCLUDED.etl_run_id,
        updated_at = now()
    """
)


def _get_known_barrios() -> set[str]:
    with session_scope() as s:
        rows = s.execute(text("SELECT id FROM barrios")).all()
    return {r[0] for r in rows}


def main() -> None:
    known_barrios = _get_known_barrios()
    if not known_barrios:
        raise RuntimeError(
            "No barrios in DB. Run the TIGER barrio loader first: "
            "uv run python -m sources.census_tiger_barrios"
        )
    log.info("Known barrios in DB: %d", len(known_barrios))

    acs_vars = all_acs_variables()
    log.info("Will fetch %d ACS variables × %d years", len(acs_vars), len(YEARS))

    with EtlRunTracker(source_slug=SOURCE_SLUG) as run:
        total_read = 0
        total_upserted = 0
        total_skipped = 0
        suppressed_count = 0

        with session_scope() as s:
            for year in YEARS:
                log.info("--- Year %d ---", year)
                try:
                    rows = fetch_acs_year(year, acs_vars, GEOGRAPHY)
                except requests.HTTPError as e:
                    log.error("Census API error for %d: %s", year, e)
                    total_skipped += 1
                    continue

                log.info("  fetched %d barrio rows", len(rows))
                total_read += len(rows)

                for row in rows:
                    barrio_id = (
                        str(row.get("state", ""))
                        + str(row.get("county", ""))
                        + str(row.get("county subdivision", ""))
                    )
                    if barrio_id not in known_barrios:
                        total_skipped += 1
                        continue

                    for var in VARIABLES:
                        value, numerator, denominator = compute_value(var, row)
                        is_suppressed = value is None
                        if is_suppressed:
                            suppressed_count += 1
                        s.execute(
                            UPSERT_SQL,
                            {
                                "barrio_id": barrio_id,
                                "indicator_code": var.code,
                                "year": year,
                                "value": value,
                                "value_type": var.value_type,
                                "numerator": int(numerator) if numerator else None,
                                "denominator": int(denominator) if denominator else None,
                                "is_suppressed": is_suppressed,
                                "source_id": run.source_id,
                                "etl_run_id": run.run_id,
                            },
                        )
                        total_upserted += 1

        run.rows_read = total_read
        run.rows_upserted = total_upserted
        run.rows_skipped = total_skipped

        pct_suppressed = (
            100.0 * suppressed_count / max(total_upserted, 1)
        )
        log.info(
            "Finished. Years=%d Indicators=%d Upserted=%d Skipped=%d Suppressed=%d (%.1f%%)",
            len(YEARS), len(VARIABLES), total_upserted, total_skipped,
            suppressed_count, pct_suppressed,
        )


if __name__ == "__main__":
    main()
