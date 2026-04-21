"""Load US Census American Community Survey / Puerto Rico Community Survey data
for all 78 Puerto Rico municipios.

Loads social determinants of health (SDOH) indicators from the ACS 5-year
estimates — demographics, poverty, insurance, education, housing, economics.
These aren't direct health outcomes, but they're the underlying drivers
documented repeatedly as predictors of chronic disease in Puerto Rico.

For PR specifically, the ACS is customized as the Puerto Rico Community Survey
(PRCS). The API endpoint is the same.

API:    https://api.census.gov/data/{year}/acs/acs5
Docs:   https://www.census.gov/data/developers/data-sets/acs-5year.html
PR:     https://www2.census.gov/training-workshops/2023/2023-11-03-pr-api-presentation.pdf

Run:
    cd etl && uv run python -m sources.census_acs
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import requests
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential

from lib.db import session_scope
from lib.logging import get_logger
from lib.tracker import EtlRunTracker

log = get_logger(__name__)

SOURCE_SLUG = "census_acs"
PR_STATE_FIPS = "72"
API_BASE = "https://api.census.gov/data"

# --- Years to load ---
# ACS 5-year estimates: most recent is 2023 (covering 2019-2023 sample).
# Going back 5 years gives us longitudinal data for pre/post-Maria trends.
YEARS = [2019, 2020, 2021, 2022, 2023]


@dataclass(frozen=True)
class AcsVariable:
    """A single ACS variable or computed ratio we care about."""

    code: str                     # our indicator_code in health_metrics
    numerator: str                # ACS variable code for numerator
    denominator: str | None       # ACS variable code for denominator (None = raw count)
    value_type: str               # 'count', 'percent', or 'dollars'
    multiplier: float = 1.0       # e.g. 100 for percent conversion
    description: str = ""


# --- Variables to load ---
# Each tuple is (indicator_code, numerator_var, denominator_var_or_None, value_type)
# For percentages, we compute numerator / denominator * 100 at the app layer.
VARIABLES: list[AcsVariable] = [
    # --- Population / demographics ---
    AcsVariable(
        code="total_population",
        numerator="B01003_001E",
        denominator=None,
        value_type="count",
        description="Total population",
    ),
    AcsVariable(
        code="median_age",
        numerator="B01002_001E",
        denominator=None,
        value_type="count",  # really years but we use count bucket
        description="Median age",
    ),
    AcsVariable(
        code="pct_age_65_plus",
        # B01001_020..025 (male 65+) + B01001_044..049 (female 65+)
        # We can't sum in a single variable, so we query each and compute below.
        numerator="SYNTHETIC_AGE_65_PLUS",
        denominator="B01003_001E",
        value_type="percent",
        multiplier=100.0,
        description="% population age 65+",
    ),
    AcsVariable(
        code="pct_under_18",
        numerator="B09001_001E",
        denominator="B01003_001E",
        value_type="percent",
        multiplier=100.0,
        description="% population under 18",
    ),
    # --- Economic ---
    AcsVariable(
        code="median_household_income",
        numerator="B19013_001E",
        denominator=None,
        value_type="dollars",
        description="Median household income",
    ),
    AcsVariable(
        code="pct_below_poverty",
        numerator="B17001_002E",
        denominator="B17001_001E",
        value_type="percent",
        multiplier=100.0,
        description="% below federal poverty line",
    ),
    # --- Health access ---
    AcsVariable(
        code="pct_uninsured",
        # B27001_001 = total civilian pop. Uninsured is the sum across age buckets (B27001_005, _008, etc)
        # For simplicity use B27010_017+033+050+066 (not insured by age group) over B27010_001 total.
        numerator="SYNTHETIC_UNINSURED",
        denominator="B27010_001E",
        value_type="percent",
        multiplier=100.0,
        description="% without health insurance",
    ),
    # --- Education ---
    AcsVariable(
        code="pct_bachelors_or_higher",
        # B15003_022+023+024+025 (bachelor / master / prof / doctorate) over B15003_001 (25+)
        numerator="SYNTHETIC_BACHELORS_PLUS",
        denominator="B15003_001E",
        value_type="percent",
        multiplier=100.0,
        description="% age 25+ with bachelor's degree or higher",
    ),
    AcsVariable(
        code="pct_no_high_school",
        # B15003_002..016 (less than HS diploma) over B15003_001
        # B15003_002 is no schooling, B15003_003..016 are < HS completion
        numerator="SYNTHETIC_NO_HS",
        denominator="B15003_001E",
        value_type="percent",
        multiplier=100.0,
        description="% age 25+ without high school diploma",
    ),
    # --- Housing ---
    AcsVariable(
        code="pct_overcrowded_housing",
        # B25014_005+006+007 (owner 1.01+ per room) + B25014_011+012+013 (renter)
        numerator="SYNTHETIC_OVERCROWDED",
        denominator="B25014_001E",
        value_type="percent",
        multiplier=100.0,
        description="% housing units with >1 occupant per room",
    ),
]

# For synthetic sums, the list of underlying ACS variables to fetch and sum
SYNTHETIC_SUMS: dict[str, list[str]] = {
    "SYNTHETIC_AGE_65_PLUS": [
        # Male 65+
        "B01001_020E", "B01001_021E", "B01001_022E", "B01001_023E", "B01001_024E", "B01001_025E",
        # Female 65+
        "B01001_044E", "B01001_045E", "B01001_046E", "B01001_047E", "B01001_048E", "B01001_049E",
    ],
    "SYNTHETIC_UNINSURED": [
        # "No health insurance coverage" across age buckets in table B27010
        "B27010_017E", "B27010_033E", "B27010_050E", "B27010_066E",
    ],
    "SYNTHETIC_BACHELORS_PLUS": [
        "B15003_022E",  # bachelor's
        "B15003_023E",  # master's
        "B15003_024E",  # professional
        "B15003_025E",  # doctorate
    ],
    "SYNTHETIC_NO_HS": [
        # No schooling through 12th grade no diploma (B15003_002 .. _016)
        *[f"B15003_{str(i).zfill(3)}E" for i in range(2, 17)],
    ],
    "SYNTHETIC_OVERCROWDED": [
        "B25014_005E", "B25014_006E", "B25014_007E",   # owner occ, >1.0 per room
        "B25014_011E", "B25014_012E", "B25014_013E",   # renter occ, >1.0 per room
    ],
}


def _all_acs_variables() -> list[str]:
    """Flatten every raw ACS variable we need to fetch."""
    collected: set[str] = set()
    for v in VARIABLES:
        if v.numerator in SYNTHETIC_SUMS:
            collected.update(SYNTHETIC_SUMS[v.numerator])
        else:
            collected.add(v.numerator)
        if v.denominator and v.denominator not in SYNTHETIC_SUMS:
            collected.add(v.denominator)
    return sorted(collected)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _fetch_year(year: int, variables: list[str]) -> list[list[str]]:
    """Fetch one year of ACS data for all PR counties. Returns list of rows (header first)."""
    # API allows up to 50 variables per request; chunk if needed
    CHUNK_SIZE = 45
    chunks = [variables[i : i + CHUNK_SIZE] for i in range(0, len(variables), CHUNK_SIZE)]

    all_rows: list[dict[str, str]] = []
    header: list[str] | None = None

    for chunk in chunks:
        params: dict[str, str] = {
            "get": ",".join(["NAME", *chunk]),
            "for": "county:*",
            "in": f"state:{PR_STATE_FIPS}",
        }
        key = os.getenv("CENSUS_API_KEY")
        if key:
            params["key"] = key

        url = f"{API_BASE}/{year}/acs/acs5"
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        data: list[list[str]] = r.json()

        chunk_header = data[0]
        chunk_rows = data[1:]

        # Convert to dict keyed by muni_id for merging across chunks
        for row in chunk_rows:
            row_dict = dict(zip(chunk_header, row, strict=True))
            muni_id = row_dict["state"] + row_dict["county"]
            existing = next(
                (r for r in all_rows if r.get("_muni_id") == muni_id),
                None,
            )
            if existing is None:
                row_dict["_muni_id"] = muni_id
                all_rows.append(row_dict)
            else:
                existing.update(row_dict)
                existing["_muni_id"] = muni_id

        if header is None:
            header = chunk_header

    # Convert back to list-of-lists with combined headers
    if not all_rows:
        return []
    combined_headers = sorted({k for r in all_rows for k in r.keys() if k != "_muni_id"})
    result: list[list[str]] = [combined_headers]
    for row in all_rows:
        result.append([row.get(h, "") for h in combined_headers])
    return result


def _to_decimal(raw: str | None) -> Decimal | None:
    """Parse an ACS cell. Negative sentinel values mean missing/suppressed."""
    if raw is None or raw == "" or raw == "null":
        return None
    try:
        d = Decimal(raw)
    except (ValueError, ArithmeticError):
        return None
    # ACS uses -666666666, -999999999 etc as missing sentinels
    if d < Decimal("-100"):
        return None
    return d


def _compute_value(
    var: AcsVariable,
    row: dict[str, str],
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """Resolve a variable's value (possibly summing + dividing) from a flat row dict.

    Returns (value, numerator_int, denominator_int).
    """
    # Resolve numerator
    if var.numerator in SYNTHETIC_SUMS:
        nums = [_to_decimal(row.get(v)) for v in SYNTHETIC_SUMS[var.numerator]]
        if all(n is None for n in nums):
            numerator: Decimal | None = None
        else:
            numerator = sum((n for n in nums if n is not None), Decimal(0))
    else:
        numerator = _to_decimal(row.get(var.numerator))

    # Resolve denominator
    denominator: Decimal | None = None
    if var.denominator is not None:
        if var.denominator in SYNTHETIC_SUMS:
            dens = [_to_decimal(row.get(v)) for v in SYNTHETIC_SUMS[var.denominator]]
            if not all(d is None for d in dens):
                denominator = sum((d for d in dens if d is not None), Decimal(0))
        else:
            denominator = _to_decimal(row.get(var.denominator))

    # Compute final value
    if numerator is None:
        return None, None, denominator
    if var.denominator is None:
        # raw count / dollars
        return numerator, None, None
    if denominator is None or denominator == 0:
        return None, None, denominator

    pct = (numerator / denominator) * Decimal(str(var.multiplier if var.multiplier else 100))
    return pct.quantize(Decimal("0.0001")), numerator, denominator


UPSERT_SQL = text(
    """
    INSERT INTO health_metrics (
        muni_id, indicator_code, year,
        value, value_type, numerator, denominator,
        is_suppressed, is_estimated,
        source_id, etl_run_id, updated_at
    )
    VALUES (
        :muni_id, :indicator_code, :year,
        :value, :value_type, :numerator, :denominator,
        :is_suppressed, false,
        :source_id, :etl_run_id, now()
    )
    ON CONFLICT (muni_id, indicator_code, year, source_id) DO UPDATE SET
        value = EXCLUDED.value,
        numerator = EXCLUDED.numerator,
        denominator = EXCLUDED.denominator,
        is_suppressed = EXCLUDED.is_suppressed,
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

    acs_vars = _all_acs_variables()
    log.info("Will fetch %d ACS variables × %d years", len(acs_vars), len(YEARS))

    with EtlRunTracker(source_slug=SOURCE_SLUG) as run:
        total_read = 0
        total_upserted = 0
        total_skipped = 0

        with session_scope() as s:
            for year in YEARS:
                log.info("--- Year %d ---", year)
                try:
                    raw = _fetch_year(year, acs_vars)
                except requests.HTTPError as e:
                    log.error("Census API error for %d: %s", year, e)
                    total_skipped += 1
                    continue

                if not raw:
                    log.warning("No data for year %d", year)
                    continue

                header = raw[0]
                rows = raw[1:]
                total_read += len(rows)
                log.info("  fetched %d muni rows", len(rows))

                for raw_row in rows:
                    row = dict(zip(header, raw_row, strict=False))
                    muni_id = str(row.get("state", "")) + str(row.get("county", ""))

                    if muni_id not in known_munis:
                        total_skipped += 1
                        continue

                    for var in VARIABLES:
                        value, numerator, denominator = _compute_value(var, row)
                        is_suppressed = value is None

                        s.execute(
                            UPSERT_SQL,
                            {
                                "muni_id": muni_id,
                                "indicator_code": var.code,
                                "year": year,
                                "value": value,
                                "value_type": var.value_type,
                                "numerator": int(numerator) if numerator is not None else None,
                                "denominator": int(denominator) if denominator is not None else None,
                                "is_suppressed": is_suppressed,
                                "source_id": run.source_id,
                                "etl_run_id": run.run_id,
                            },
                        )
                        total_upserted += 1

        run.rows_read = total_read
        run.rows_upserted = total_upserted
        run.rows_skipped = total_skipped
        log.info(
            "Finished. Years=%d Indicators=%d Upserted=%d Skipped=%d",
            len(YEARS), len(VARIABLES), total_upserted, total_skipped,
        )


if __name__ == "__main__":
    main()
