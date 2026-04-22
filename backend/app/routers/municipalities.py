"""Municipalities router — serves the 78 PR municipios as GeoJSON.

Supports optional indicator overlay: when ?indicator=X is passed, each feature
gets a `value` property injected from the health_metrics table for the most
recent year (or the specified ?year=YYYY).
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.database import DbSession

router = APIRouter()


class MunicipalitySummary(BaseModel):
    """Compact summary of a municipality (no geometry)."""

    id: str
    name: str
    area_sq_km: float | None
    population_latest: int | None


@router.get("/municipalities")
def list_municipalities_geojson(
    db: DbSession,
    indicator: str | None = Query(
        None, description="Optional indicator_code to inject into each feature"
    ),
    year: int | None = Query(
        None, description="Year for the indicator (defaults to latest available)"
    ),
) -> dict[str, Any]:
    """Return all 78 municipalities as a GeoJSON FeatureCollection.

    When `indicator` is passed, each feature's properties include a `value`,
    `value_type`, `year`, `is_suppressed`, and `is_estimated` from
    health_metrics. Otherwise just geometry + name + area.
    """
    resolved_year: int | None = year
    if indicator is not None and resolved_year is None:
        row = db.execute(
            text("SELECT MAX(year) FROM health_metrics WHERE indicator_code = :code"),
            {"code": indicator},
        ).first()
        if row is None or row[0] is None:
            raise HTTPException(
                status_code=404, detail=f"No data for indicator '{indicator}'"
            )
        resolved_year = int(row[0])

    if indicator is None:
        query = """
            SELECT
                m.id,
                m.name,
                m.area_sq_km,
                m.population_latest,
                ST_AsGeoJSON(ST_Simplify(m.geometry, 0.0005), 6) AS geom_json,
                NULL::numeric AS value,
                NULL::text AS value_type,
                NULL::int AS year,
                NULL::boolean AS is_suppressed,
                NULL::boolean AS is_estimated
            FROM municipalities m
            ORDER BY m.name
        """
        params: dict[str, Any] = {}
    else:
        query = """
            SELECT
                m.id,
                m.name,
                m.area_sq_km,
                m.population_latest,
                ST_AsGeoJSON(ST_Simplify(m.geometry, 0.0005), 6) AS geom_json,
                hm.value,
                hm.value_type,
                hm.year,
                hm.is_suppressed,
                hm.is_estimated
            FROM municipalities m
            LEFT JOIN health_metrics hm
                ON hm.muni_id = m.id
                AND hm.indicator_code = :indicator
                AND hm.year = :year
            ORDER BY m.name
        """
        params = {"indicator": indicator, "year": resolved_year}

    rows = db.execute(text(query), params).all()

    features = [
        {
            "type": "Feature",
            "id": row.id,  # surfaced at feature level so Mapbox feature-state works cleanly
            "geometry": json.loads(row.geom_json),
            "properties": {
                "id": row.id,
                "name": row.name,
                "area_sq_km": float(row.area_sq_km) if row.area_sq_km else None,
                "population_latest": row.population_latest,
                "value": float(row.value) if row.value is not None else None,
                "value_type": row.value_type,
                "year": row.year,
                "is_suppressed": row.is_suppressed,
                "is_estimated": row.is_estimated,
            },
        }
        for row in rows
    ]

    return {
        "type": "FeatureCollection",
        "metadata": {
            "indicator": indicator,
            "year": resolved_year,
            "count": len(features),
        },
        "features": features,
    }


@router.get("/municipalities/summary", response_model=list[MunicipalitySummary])
def list_municipalities_summary(db: DbSession) -> list[MunicipalitySummary]:
    """Return all 78 municipalities as a compact list (no geometry)."""
    rows = db.execute(
        text(
            """
            SELECT id, name, area_sq_km, population_latest
            FROM municipalities
            ORDER BY name
            """
        )
    ).all()
    return [
        MunicipalitySummary(
            id=row.id,
            name=row.name,
            area_sq_km=float(row.area_sq_km) if row.area_sq_km else None,
            population_latest=row.population_latest,
        )
        for row in rows
    ]


@router.get("/municipalities/{muni_id}", response_model=MunicipalitySummary)
def get_municipality(muni_id: str, db: DbSession) -> MunicipalitySummary:
    """Return one municipality by its 5-digit FIPS code (e.g. '72127' for San Juan)."""
    row = db.execute(
        text(
            """
            SELECT id, name, area_sq_km, population_latest
            FROM municipalities
            WHERE id = :muni_id
            """
        ),
        {"muni_id": muni_id},
    ).first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Municipality '{muni_id}' not found")

    return MunicipalitySummary(
        id=row.id,
        name=row.name,
        area_sq_km=float(row.area_sq_km) if row.area_sq_km else None,
        population_latest=row.population_latest,
    )
