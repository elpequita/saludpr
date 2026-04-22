"""Territory router — PR-wide health indicators (BRFSS chronic disease data).

Separate from /metrics because the granularity is fundamentally different:
these are island-wide values, not per-muni. Keeping the routes distinct
makes it explicit in the URL that what you're getting is territory-level.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.database import DbSession

router = APIRouter()


class TerritoryIndicator(BaseModel):
    code: str
    latest_year: int
    latest_value: float | None
    source_slug: str
    source_name: str
    year_count: int


class TerritoryValue(BaseModel):
    year: int
    value: float | None
    ci_lower: float | None
    ci_upper: float | None
    sample_size: int | None
    is_suppressed: bool


class TerritoryTrend(BaseModel):
    indicator_code: str
    territory_id: str
    source_slug: str
    values: list[TerritoryValue]
    latest_updated_at: datetime | None


@router.get("/territory/indicators", response_model=list[TerritoryIndicator])
def list_territory_indicators(db: DbSession) -> list[TerritoryIndicator]:
    """List every territory-level indicator currently loaded."""
    rows = db.execute(
        text(
            """
            WITH latest AS (
                SELECT DISTINCT ON (thm.indicator_code)
                    thm.indicator_code,
                    thm.year AS latest_year,
                    thm.value AS latest_value,
                    thm.source_id
                FROM territory_health_metrics thm
                ORDER BY thm.indicator_code, thm.year DESC
            )
            SELECT
                latest.indicator_code AS code,
                latest.latest_year,
                latest.latest_value,
                ds.slug AS source_slug,
                ds.name AS source_name,
                (SELECT COUNT(DISTINCT year)
                   FROM territory_health_metrics thm2
                  WHERE thm2.indicator_code = latest.indicator_code) AS year_count
            FROM latest
            JOIN data_sources ds ON ds.id = latest.source_id
            ORDER BY latest.indicator_code
            """
        )
    ).all()

    return [
        TerritoryIndicator(
            code=r.code,
            latest_year=int(r.latest_year),
            latest_value=float(r.latest_value) if r.latest_value is not None else None,
            source_slug=r.source_slug,
            source_name=r.source_name,
            year_count=int(r.year_count),
        )
        for r in rows
    ]


@router.get("/territory/trend/{indicator_code}", response_model=TerritoryTrend)
def get_territory_trend(
    indicator_code: str,
    db: DbSession,
    territory_id: str = Query("PR", description="Territory code (default PR)"),
) -> TerritoryTrend:
    """Return full year-by-year history for one indicator.

    Used by the frontend sparkline in the context strip.
    """
    rows = db.execute(
        text(
            """
            SELECT
                thm.year,
                thm.value,
                thm.ci_lower,
                thm.ci_upper,
                thm.sample_size,
                thm.is_suppressed,
                thm.updated_at,
                ds.slug AS source_slug
            FROM territory_health_metrics thm
            JOIN data_sources ds ON ds.id = thm.source_id
            WHERE thm.indicator_code = :code
              AND thm.territory_id = :territory
            ORDER BY thm.year
            """
        ),
        {"code": indicator_code, "territory": territory_id},
    ).all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No data for indicator '{indicator_code}' in territory '{territory_id}'",
        )

    values = [
        TerritoryValue(
            year=int(r.year),
            value=float(r.value) if r.value is not None else None,
            ci_lower=float(r.ci_lower) if r.ci_lower is not None else None,
            ci_upper=float(r.ci_upper) if r.ci_upper is not None else None,
            sample_size=r.sample_size,
            is_suppressed=r.is_suppressed,
        )
        for r in rows
    ]

    latest_updated = max((r.updated_at for r in rows if r.updated_at), default=None)
    source_slug = rows[0].source_slug

    return TerritoryTrend(
        indicator_code=indicator_code,
        territory_id=territory_id,
        source_slug=source_slug,
        values=values,
        latest_updated_at=latest_updated,
    )
