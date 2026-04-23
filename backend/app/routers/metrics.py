"""Metrics router — serves health_metrics data by indicator + year."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.database import DbSession

router = APIRouter()


class Indicator(BaseModel):
    """One indicator available for querying."""

    code: str
    value_type: str
    source_slug: str
    source_name: str
    years: list[int]
    total_rows: int


class MetricValue(BaseModel):
    muni_id: str
    name: str
    value: float | None
    value_type: str
    year: int
    is_suppressed: bool
    is_estimated: bool


class MetricSummary(BaseModel):
    indicator_code: str
    value_type: str
    year: int
    count: int
    min_value: float | None
    max_value: float | None
    median_value: float | None
    values: list[MetricValue]


@router.get("/metrics/indicators", response_model=list[Indicator])
def list_indicators(db: DbSession) -> list[Indicator]:
    """List every indicator that has data loaded, with the year range available."""
    rows = db.execute(
        text(
            """
            SELECT
                hm.indicator_code AS code,
                MAX(hm.value_type) AS value_type,
                ds.slug AS source_slug,
                ds.name AS source_name,
                array_agg(DISTINCT hm.year ORDER BY hm.year) AS years,
                COUNT(*) AS total_rows
            FROM health_metrics hm
            JOIN data_sources ds ON ds.id = hm.source_id
            GROUP BY hm.indicator_code, ds.slug, ds.name

            UNION ALL

            SELECT
                'imu_score' AS code,
                'imu_score' AS value_type,
                ds.slug AS source_slug,
                ds.name AS source_name,
                array_agg(DISTINCT EXTRACT(YEAR FROM d.designation_date)::int
                    ORDER BY EXTRACT(YEAR FROM d.designation_date)::int) AS years,
                COUNT(*) AS total_rows
            FROM v_muni_active_designations d
            JOIN data_sources ds ON ds.id = d.source_id
            GROUP BY ds.slug, ds.name

            ORDER BY code
            """
        )
    ).all()
    return [
        Indicator(
            code=row.code,
            value_type=row.value_type,
            source_slug=row.source_slug,
            source_name=row.source_name,
            years=list(row.years),
            total_rows=int(row.total_rows),
        )
        for row in rows
    ]


@router.get("/metrics/{indicator_code}", response_model=MetricSummary)
def get_metric(
    indicator_code: str,
    db: DbSession,
    year: int | None = Query(
        None, description="Year to fetch. Defaults to latest available for this indicator."
    ),
) -> MetricSummary:
    """Return one indicator's values across all municipalities for a given year.

    Also includes summary stats (min/max/median) computed at the DB level — used
    by the frontend to generate a legend scale.
    """
    # Resolve year if not provided
    if year is None:
        row = db.execute(
            text(
                "SELECT MAX(year) FROM health_metrics WHERE indicator_code = :code"
            ),
            {"code": indicator_code},
        ).first()
        if row is None or row[0] is None:
            raise HTTPException(
                status_code=404, detail=f"No data for indicator '{indicator_code}'"
            )
        year = int(row[0])

    # Fetch values + metadata
    rows = db.execute(
        text(
            """
            SELECT
                hm.muni_id,
                m.name,
                hm.value,
                hm.value_type,
                hm.year,
                hm.is_suppressed,
                hm.is_estimated
            FROM health_metrics hm
            JOIN municipalities m ON m.id = hm.muni_id
            WHERE hm.indicator_code = :code AND hm.year = :year
            ORDER BY m.name
            """
        ),
        {"code": indicator_code, "year": year},
    ).all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No data for indicator '{indicator_code}' in year {year}",
        )

    values = [
        MetricValue(
            muni_id=r.muni_id,
            name=r.name,
            value=float(r.value) if r.value is not None else None,
            value_type=r.value_type,
            year=r.year,
            is_suppressed=r.is_suppressed,
            is_estimated=r.is_estimated,
        )
        for r in rows
    ]

    # Summary stats from non-null values
    nums: list[Decimal] = [r.value for r in rows if r.value is not None]
    if nums:
        sorted_nums = sorted(nums)
        median = sorted_nums[len(sorted_nums) // 2]
        min_val: float | None = float(min(nums))
        max_val: float | None = float(max(nums))
        median_val: float | None = float(median)
    else:
        min_val = max_val = median_val = None

    return MetricSummary(
        indicator_code=indicator_code,
        value_type=rows[0].value_type,
        year=year,
        count=len(rows),
        min_value=min_val,
        max_value=max_val,
        median_value=median_val,
        values=values,
    )
