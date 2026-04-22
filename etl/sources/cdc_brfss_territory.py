"""Load CDC BRFSS Prevalence Data at the Puerto Rico territory level.

CDC PLACES excludes Puerto Rico — but BRFSS itself does include PR as a
participating territory, with 14 years of data (2011-2024). The data is only
available at the territory level (not disaggregated to municipio), but it
gives us the best available chronic-disease snapshot for PR.

Source: https://data.cdc.gov/resource/dttw-5yxu (Socrata)

Each BRFSS indicator we care about maps to a (topic, question_substring, response)
triple. We filter to break_out='Overall' to avoid demographic slices and pull
only crude prevalence values with their confidence intervals and sample sizes.

Run:
    cd etl && uv run python -m sources.cdc_brfss_territory
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import requests
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential

from lib.db import session_scope
from lib.logging import get_logger
from lib.tracker import EtlRunTracker

log = get_logger(__name__)

SOURCE_SLUG = "cdc_brfss"
TERRITORY_ID = "PR"
API_URL = "https://data.cdc.gov/resource/dttw-5yxu.json"

# Only pull from recent years to keep the context strip readable
YEARS = list(range(2015, 2025))  # 2015-2024 inclusive


@dataclass(frozen=True)
class BrfssIndicator:
    """One indicator we want to extract, mapped to BRFSS's (topic, question, response)."""

    code: str
    topic: str
    question_contains: str  # substring match in the question text (case-insensitive)
    response: str | tuple[str, ...]  # single response OR tuple of responses to sum
    description: str


INDICATORS: list[BrfssIndicator] = [
    BrfssIndicator(
        code="pct_diabetes_diagnosed",
        topic="Diabetes",
        question_contains="ever been told by a doctor that you have diabetes",
        response="Yes",
        description="% adultos diagnosticados con diabetes",
    ),
    BrfssIndicator(
        code="pct_hypertension",
        topic="High Blood Pressure",
        question_contains="high blood pressure",
        response="Yes",
        description="% adultos con presión alta diagnosticada",
    ),
    BrfssIndicator(
        code="pct_current_asthma",
        topic="Asthma",
        question_contains="currently have asthma",
        response="Yes",
        description="% adultos con asma actual",
    ),
    BrfssIndicator(
        code="pct_copd",
        topic="COPD",
        question_contains="told you have COPD",
        response="Yes",
        description="% adultos con EPOC",
    ),
    BrfssIndicator(
        code="pct_heart_attack_ever",
        topic="Cardiovascular Disease",
        question_contains="heart attack",
        response="Yes",
        description="% adultos que han tenido un ataque al corazón",
    ),
    BrfssIndicator(
        code="pct_stroke_ever",
        topic="Cardiovascular Disease",
        question_contains="you had a stroke",
        response="Yes",
        description="% adultos que han tenido un derrame cerebral",
    ),
    BrfssIndicator(
        code="pct_chd_or_mi",
        topic="Cardiovascular Disease",
        question_contains="coronary heart disease",
        response="Reported having MI or CHD",
        description="% adultos con enfermedad coronaria o ataque al corazón",
    ),
    BrfssIndicator(
        code="pct_depression_ever",
        topic="Depression",
        question_contains="form of depression",
        response="Yes",
        description="% adultos diagnosticados con depresión",
    ),
    BrfssIndicator(
        code="pct_kidney_disease",
        topic="Kidney",
        question_contains="kidney disease",
        response="Yes",
        description="% adultos con enfermedad renal",
    ),
    BrfssIndicator(
        code="pct_obesity",
        topic="BMI Categories",
        question_contains="body mass index",
        response="Obese (BMI 30.0 - 99.8)",
        description="% adultos con obesidad (BMI ≥ 30)",
    ),
    BrfssIndicator(
        code="pct_current_smoker",
        topic="Smoker Status",
        question_contains="Four Level Smoking Status",
        response=("Smoke everyday", "Smoke some days"),
        description="% adultos fumadores actuales (diarios + ocasionales)",
    ),
    BrfssIndicator(
        code="pct_binge_drinking",
        topic="Binge Drinking",
        question_contains="Binge drinkers",
        response="Yes",
        description="% adultos con consumo excesivo de alcohol",
    ),
    BrfssIndicator(
        code="pct_no_health_coverage",
        topic="Health Care Coverage",
        question_contains="any kind of health care coverage",
        response="No",
        description="% adultos sin cobertura de salud (BRFSS)",
    ),
    BrfssIndicator(
        code="pct_fair_or_poor_health",
        topic="Overall Health",
        question_contains="general health",
        response=("Fair", "Poor"),
        description="% adultos con salud autoreportada como regular o mala",
    ),
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _fetch_indicator_year(
    topic: str,
    year: int,
) -> list[dict[str, str]]:
    """Fetch all rows for a topic + year for PR, Overall breakout only."""
    # Socrata uses $where with SoQL. We pull the whole topic (all responses)
    # for the year and filter client-side for the right question/response.
    params = {
        "$where": (
            f"locationabbr='{TERRITORY_ID}' "
            f"AND topic='{topic}' "
            f"AND year='{year}' "
            f"AND break_out='Overall'"
        ),
        "$select": (
            "year,topic,question,response,data_value,data_value_type,"
            "sample_size,confidence_limit_low,confidence_limit_high,break_out"
        ),
        "$limit": 500,
    }
    r = requests.get(API_URL, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def _to_decimal(raw: str | None) -> Decimal | None:
    if raw is None or raw == "" or raw == "null":
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return None


def _to_int(raw: str | None) -> int | None:
    if raw is None or raw == "" or raw == "null":
        return None
    try:
        return int(float(raw))
    except (ValueError, TypeError):
        return None


def _match_rows(
    rows: list[dict[str, str]],
    ind: BrfssIndicator,
) -> dict[str, str] | None:
    """Find the row(s) that match this indicator's (question, response) filters.

    If the indicator specifies a tuple of responses (e.g. ('Smoke everyday',
    'Smoke some days')), we sum the data_value across matching rows and combine
    their confidence intervals naively. This handles BRFSS's decomposed
    response categories (e.g. current smoker = daily + some-days).

    Prefers rows with data_value_type='Crude Prevalence' over 'Age-Adjusted'
    for consistency with how we describe the numbers to users.
    """
    responses = (
        (ind.response,) if isinstance(ind.response, str) else ind.response
    )

    collected: list[dict[str, str]] = []
    for target in responses:
        matches = [
            r
            for r in rows
            if ind.question_contains.lower() in (r.get("question") or "").lower()
            and (r.get("response") or "").strip() == target.strip()
        ]
        if not matches:
            continue
        # Prefer Crude Prevalence within each response group
        crude = [m for m in matches if m.get("data_value_type") == "Crude Prevalence"]
        collected.append(crude[0] if crude else matches[0])

    if not collected:
        return None
    if len(collected) == 1:
        return collected[0]

    # Sum across multiple responses
    def _sum_decimal(key: str) -> str | None:
        parts = [_to_decimal(c.get(key)) for c in collected]
        numeric = [p for p in parts if p is not None]
        if len(numeric) != len(parts):
            # At least one missing — safer to return None than a partial sum
            return None
        total = sum(numeric, Decimal(0))
        return str(total)

    def _sum_int(key: str) -> str | None:
        parts = [_to_int(c.get(key)) for c in collected]
        numeric = [p for p in parts if p is not None]
        if len(numeric) != len(parts):
            return None
        return str(sum(numeric))

    # Represent the aggregated result as a synthetic row
    return {
        "year": collected[0].get("year", ""),
        "topic": collected[0].get("topic", ""),
        "question": collected[0].get("question", ""),
        "response": " + ".join(responses),
        "data_value": _sum_decimal("data_value") or "",
        "data_value_type": collected[0].get("data_value_type", "Crude Prevalence"),
        # Summing CI bounds is only approximate (ignores correlation) but useful
        "confidence_limit_low": _sum_decimal("confidence_limit_low") or "",
        "confidence_limit_high": _sum_decimal("confidence_limit_high") or "",
        "sample_size": _sum_int("sample_size") or "",
    }


UPSERT_SQL = text(
    """
    INSERT INTO territory_health_metrics (
        territory_id, indicator_code, year,
        value, value_type, ci_lower, ci_upper, sample_size,
        is_suppressed, is_estimated,
        source_id, etl_run_id, updated_at
    )
    VALUES (
        :territory_id, :indicator_code, :year,
        :value, 'percent', :ci_lower, :ci_upper, :sample_size,
        :is_suppressed, false,
        :source_id, :etl_run_id, now()
    )
    ON CONFLICT (territory_id, indicator_code, year, source_id) DO UPDATE SET
        value = EXCLUDED.value,
        ci_lower = EXCLUDED.ci_lower,
        ci_upper = EXCLUDED.ci_upper,
        sample_size = EXCLUDED.sample_size,
        is_suppressed = EXCLUDED.is_suppressed,
        etl_run_id = EXCLUDED.etl_run_id,
        updated_at = now()
    """
)


def main() -> None:
    log.info(
        "Will fetch %d indicators × %d years from BRFSS for PR",
        len(INDICATORS),
        len(YEARS),
    )

    with EtlRunTracker(source_slug=SOURCE_SLUG) as run:
        total_read = 0
        total_upserted = 0
        total_missing = 0

        with session_scope() as s:
            # Group by topic to minimize API calls (one request per topic-year
            # covers multiple indicators sharing that topic)
            topics = sorted({ind.topic for ind in INDICATORS})

            for year in YEARS:
                log.info("--- Year %d ---", year)
                for topic in topics:
                    try:
                        rows = _fetch_indicator_year(topic, year)
                    except requests.HTTPError as e:
                        log.error("BRFSS API error for %s/%d: %s", topic, year, e)
                        continue

                    total_read += len(rows)

                    # For each indicator belonging to this topic, find the right row
                    for ind in INDICATORS:
                        if ind.topic != topic:
                            continue
                        row = _match_rows(rows, ind)
                        if row is None:
                            total_missing += 1
                            continue

                        value = _to_decimal(row.get("data_value"))
                        ci_low = _to_decimal(row.get("confidence_limit_low"))
                        ci_high = _to_decimal(row.get("confidence_limit_high"))
                        sample = _to_int(row.get("sample_size"))

                        s.execute(
                            UPSERT_SQL,
                            {
                                "territory_id": TERRITORY_ID,
                                "indicator_code": ind.code,
                                "year": year,
                                "value": value,
                                "ci_lower": ci_low,
                                "ci_upper": ci_high,
                                "sample_size": sample,
                                "is_suppressed": value is None,
                                "source_id": run.source_id,
                                "etl_run_id": run.run_id,
                            },
                        )
                        total_upserted += 1

        run.rows_read = total_read
        run.rows_upserted = total_upserted
        run.rows_skipped = total_missing
        log.info(
            "Finished. Read=%d Upserted=%d Missing=%d",
            total_read,
            total_upserted,
            total_missing,
        )


if __name__ == "__main__":
    main()
