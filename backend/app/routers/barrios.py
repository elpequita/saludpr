"""Barrios router — serves PR's ~900 barrios as GeoJSON, optionally enriched."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.database import DbSession

router = APIRouter()


class BarrioSummary(BaseModel):
    """Compact barrio summary (no geometry)."""

    id: str
    muni_id: str
    muni_name: str
    name: str
    area_sq_km: float | None
    population_latest: int | None


@router.get("/barrios")
def list_barrios_geojson(
    db: DbSession,
    muni_id: str | None = Query(
        None, description="If provided, filter to barrios in this municipio only"
    ),
    indicator: str | None = Query(
        None, description="Optional indicator_code to inject into each feature"
    ),
    year: int | None = Query(
        None, description="Year (defaults to latest available for the indicator)"
    ),
) -> dict[str, Any]:
    """Return barrios as a GeoJSON FeatureCollection.

    - Without `muni_id`: returns all ~900 PR barrios (large response).
    - With `muni_id`: returns only barrios within that muni.
    - With `indicator`: each feature gets a `value` property from
      barrio_health_metrics for the most recent (or specified) year.
    """
    resolved_year: int | None = year
    if indicator is not None and resolved_year is None:
        row = db.execute(
            text(
                "SELECT MAX(year) FROM barrio_health_metrics "
                "WHERE indicator_code = :code"
            ),
            {"code": indicator},
        ).first()
        if row is None or row[0] is None:
            raise HTTPException(
                status_code=404, detail=f"No data for indicator '{indicator}'"
            )
        resolved_year = int(row[0])

    params: dict[str, Any] = {}
    muni_filter = ""
    if muni_id is not None:
        muni_filter = "WHERE b.muni_id = :muni_id"
        params["muni_id"] = muni_id

    if indicator is None:
        query = f"""
            SELECT
                b.id,
                b.muni_id,
                b.name,
                b.area_sq_km,
                b.population_latest,
                ST_AsGeoJSON(ST_Simplify(b.geometry, 0.0003), 6) AS geom_json,
                NULL::numeric AS value,
                NULL::text AS value_type,
                NULL::int AS data_year,
                NULL::boolean AS is_suppressed,
                NULL::boolean AS is_estimated
            FROM barrios b
            {muni_filter}
            ORDER BY b.muni_id, b.name
        """
    else:
        query = f"""
            SELECT
                b.id,
                b.muni_id,
                b.name,
                b.area_sq_km,
                b.population_latest,
                ST_AsGeoJSON(ST_Simplify(b.geometry, 0.0003), 6) AS geom_json,
                hm.value,
                hm.value_type,
                hm.year AS data_year,
                hm.is_suppressed,
                hm.is_estimated
            FROM barrios b
            LEFT JOIN barrio_health_metrics hm
                ON hm.barrio_id = b.id
                AND hm.indicator_code = :indicator
                AND hm.year = :year
            {muni_filter}
            ORDER BY b.muni_id, b.name
        """
        params["indicator"] = indicator
        params["year"] = resolved_year

    rows = db.execute(text(query), params).all()

    features = [
        {
            "type": "Feature",
            "id": row.id,
            "geometry": json.loads(row.geom_json),
            "properties": {
                "id": row.id,
                "muni_id": row.muni_id,
                "name": row.name,
                "area_sq_km": float(row.area_sq_km) if row.area_sq_km else None,
                "population_latest": row.population_latest,
                "value": float(row.value) if row.value is not None else None,
                "value_type": row.value_type,
                "year": row.data_year,
                "is_suppressed": row.is_suppressed,
                "is_estimated": row.is_estimated,
            },
        }
        for row in rows
    ]

    return {
        "type": "FeatureCollection",
        "metadata": {
            "muni_id": muni_id,
            "indicator": indicator,
            "year": resolved_year,
            "count": len(features),
        },
        "features": features,
    }


@router.get("/barrios/summary", response_model=list[BarrioSummary])
def list_barrios_summary(
    db: DbSession,
    muni_id: str | None = Query(
        None, description="Filter by parent municipio"
    ),
) -> list[BarrioSummary]:
    """Compact list of barrios (no geometry) — fast, good for dropdowns/search."""
    params: dict[str, Any] = {}
    muni_filter = ""
    if muni_id is not None:
        muni_filter = "WHERE b.muni_id = :muni_id"
        params["muni_id"] = muni_id

    rows = db.execute(
        text(
            f"""
            SELECT b.id, b.muni_id, m.name AS muni_name, b.name,
                   b.area_sq_km, b.population_latest
            FROM barrios b
            JOIN municipalities m ON m.id = b.muni_id
            {muni_filter}
            ORDER BY m.name, b.name
            """
        ),
        params,
    ).all()
    return [
        BarrioSummary(
            id=row.id,
            muni_id=row.muni_id,
            muni_name=row.muni_name,
            name=row.name,
            area_sq_km=float(row.area_sq_km) if row.area_sq_km else None,
            population_latest=row.population_latest,
        )
        for row in rows
    ]


@router.get("/barrios/{barrio_id}", response_model=BarrioSummary)
def get_barrio(barrio_id: str, db: DbSession) -> BarrioSummary:
    """Look up a single barrio by its 10-digit FIPS code."""
    row = db.execute(
        text(
            """
            SELECT b.id, b.muni_id, m.name AS muni_name, b.name,
                   b.area_sq_km, b.population_latest
            FROM barrios b
            JOIN municipalities m ON m.id = b.muni_id
            WHERE b.id = :barrio_id
            """
        ),
        {"barrio_id": barrio_id},
    ).first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Barrio '{barrio_id}' not found")

    return BarrioSummary(
        id=row.id,
        muni_id=row.muni_id,
        muni_name=row.muni_name,
        name=row.name,
        area_sq_km=float(row.area_sq_km) if row.area_sq_km else None,
        population_latest=row.population_latest,
    )
