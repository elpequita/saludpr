"""Shared ACS / PRCS logic used by both muni-level and barrio-level loaders.

Keeps the variable definitions, synthetic sums, value parsing, and API paging
in one place so the muni and barrio loaders stay thin.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from lib.logging import get_logger

log = get_logger(__name__)

PR_STATE_FIPS = "72"
API_BASE = "https://api.census.gov/data"

# 5-year ACS vintages we load. Keep this in sync with the frontend year selector.
YEARS = [2019, 2020, 2021, 2022, 2023]


@dataclass(frozen=True)
class AcsVariable:
    """A single ACS variable or computed ratio we care about."""

    code: str                     # our indicator_code
    numerator: str                # ACS variable, or SYNTHETIC_* key
    denominator: str | None       # None = raw count
    value_type: str               # 'count' | 'percent' | 'dollars'
    multiplier: float = 1.0       # 100 for percent
    description: str = ""


VARIABLES: list[AcsVariable] = [
    # Population / demographics
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
        value_type="count",
        description="Median age",
    ),
    AcsVariable(
        code="pct_age_65_plus",
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
    # Economic
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
    # Health access
    AcsVariable(
        code="pct_uninsured",
        numerator="SYNTHETIC_UNINSURED",
        denominator="B27010_001E",
        value_type="percent",
        multiplier=100.0,
        description="% without health insurance",
    ),
    # Education
    AcsVariable(
        code="pct_bachelors_or_higher",
        numerator="SYNTHETIC_BACHELORS_PLUS",
        denominator="B15003_001E",
        value_type="percent",
        multiplier=100.0,
        description="% age 25+ with bachelor's or higher",
    ),
    AcsVariable(
        code="pct_no_high_school",
        numerator="SYNTHETIC_NO_HS",
        denominator="B15003_001E",
        value_type="percent",
        multiplier=100.0,
        description="% age 25+ without high school diploma",
    ),
    # Housing
    AcsVariable(
        code="pct_overcrowded_housing",
        numerator="SYNTHETIC_OVERCROWDED",
        denominator="B25014_001E",
        value_type="percent",
        multiplier=100.0,
        description="% housing units with >1 occupant per room",
    ),
]

SYNTHETIC_SUMS: dict[str, list[str]] = {
    "SYNTHETIC_AGE_65_PLUS": [
        "B01001_020E", "B01001_021E", "B01001_022E",
        "B01001_023E", "B01001_024E", "B01001_025E",
        "B01001_044E", "B01001_045E", "B01001_046E",
        "B01001_047E", "B01001_048E", "B01001_049E",
    ],
    "SYNTHETIC_UNINSURED": [
        "B27010_017E", "B27010_033E", "B27010_050E", "B27010_066E",
    ],
    "SYNTHETIC_BACHELORS_PLUS": [
        "B15003_022E", "B15003_023E", "B15003_024E", "B15003_025E",
    ],
    "SYNTHETIC_NO_HS": [
        *[f"B15003_{str(i).zfill(3)}E" for i in range(2, 17)],
    ],
    "SYNTHETIC_OVERCROWDED": [
        "B25014_005E", "B25014_006E", "B25014_007E",
        "B25014_011E", "B25014_012E", "B25014_013E",
    ],
}


def all_acs_variables() -> list[str]:
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
def _api_get(url: str, params: list[tuple[str, str]]) -> list[list[str]]:
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def fetch_acs_year(
    year: int,
    variables: list[str],
    geography: str,
) -> list[dict[str, str]]:
    """Fetch one year of ACS data for the given geography.

    `geography` is an ampersand-separated list of `key=value` pairs, e.g.:
        'for=county:*&in=state:72'              (all PR counties/munis)
        'for=county subdivision:*&in=state:72&in=county:*'  (all PR barrios)

    The `in=` key may appear multiple times — Census uses that to specify a
    hierarchy (e.g. state AND county). We preserve duplicates by using a list
    of tuples, which `requests` serializes correctly.

    Returns a list of row dicts, already merged across paginated variable chunks.
    """
    chunk_size = 45  # ACS allows up to 50 vars; leave headroom for NAME
    chunks = [
        variables[i : i + chunk_size] for i in range(0, len(variables), chunk_size)
    ]

    # Parse geography string into list of (key, value) tuples — preserves duplicate keys
    geo_params: list[tuple[str, str]] = []
    for pair in geography.split("&"):
        pair = pair.strip()
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        geo_params.append((key.strip(), value.strip()))

    key_env = os.getenv("CENSUS_API_KEY")
    all_rows: dict[str, dict[str, str]] = {}

    for chunk in chunks:
        params: list[tuple[str, str]] = [
            ("get", ",".join(["NAME", *chunk])),
            *geo_params,
        ]
        if key_env:
            params.append(("key", key_env))

        url = f"{API_BASE}/{year}/acs/acs5"
        data = _api_get(url, params)

        if not data:
            continue
        header = data[0]
        # Geography columns are everything in the header that wasn't a requested variable
        geo_cols = [h for h in header if h not in ("NAME", *chunk)]
        for row in data[1:]:
            row_dict = dict(zip(header, row, strict=True))
            geo_key = "|".join(row_dict.get(c, "") for c in sorted(geo_cols))
            if geo_key in all_rows:
                all_rows[geo_key].update(row_dict)
            else:
                all_rows[geo_key] = row_dict

    return list(all_rows.values())


def to_decimal(raw: str | None) -> Decimal | None:
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


def compute_value(
    var: AcsVariable,
    row: dict[str, Any],
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """Resolve a variable's value (possibly summing + dividing) from a row dict.

    Returns (value, numerator_int, denominator_int).
    """
    # Numerator
    if var.numerator in SYNTHETIC_SUMS:
        nums = [to_decimal(row.get(v)) for v in SYNTHETIC_SUMS[var.numerator]]
        numerator = (
            sum((n for n in nums if n is not None), Decimal(0))
            if any(n is not None for n in nums)
            else None
        )
    else:
        numerator = to_decimal(row.get(var.numerator))

    # Denominator
    denominator: Decimal | None = None
    if var.denominator is not None:
        if var.denominator in SYNTHETIC_SUMS:
            dens = [to_decimal(row.get(v)) for v in SYNTHETIC_SUMS[var.denominator]]
            if any(d is not None for d in dens):
                denominator = sum((d for d in dens if d is not None), Decimal(0))
        else:
            denominator = to_decimal(row.get(var.denominator))

    # Compute final
    if numerator is None:
        return None, None, denominator
    if var.denominator is None:
        return numerator, None, None
    if denominator is None or denominator == 0:
        return None, None, denominator

    pct = (numerator / denominator) * Decimal(str(var.multiplier or 100))
    return pct.quantize(Decimal("0.0001")), numerator, denominator
