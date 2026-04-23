"""Data sources router — exposes provenance metadata for the /methodology page."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.database import DbSession

router = APIRouter()


class DataSourcePublic(BaseModel):
    """Public view of a data source, suitable for the methodology page."""

    slug: str
    name: str
    organization: str
    url: str
    license: str
    update_frequency: str | None
    description_es: str | None
    known_limitations: str | None
    last_pulled_at: datetime | None
    latest_data_year: int | None
    latest_successful_run: datetime | None
    # Stats — how much data does this source contribute?
    muni_metric_rows: int
    barrio_metric_rows: int


@router.get("/data-sources", response_model=list[DataSourcePublic])
def list_data_sources(db: DbSession) -> list[DataSourcePublic]:
    """Return every data source SaludPR pulls from, with freshness + usage stats.

    Powers the public /methodology page. Values refresh whenever a new ETL
    run completes.
    """
    rows = db.execute(
        text(
            """
            SELECT
                ds.slug,
                ds.name,
                ds.organization,
                ds.url,
                ds.license,
                ds.update_frequency,
                ds.description_es,
                ds.known_limitations,
                ds.last_pulled_at,
                (SELECT MAX(year) FROM health_metrics hm WHERE hm.source_id = ds.id)
                    AS latest_data_year,
                (SELECT MAX(started_at) FROM etl_runs er
                    WHERE er.source_id = ds.id AND er.status = 'success')
                    AS latest_successful_run,
                (SELECT COUNT(*) FROM health_metrics hm WHERE hm.source_id = ds.id)
                    AS muni_metric_rows,
                (SELECT COUNT(*) FROM barrio_health_metrics bhm
                    WHERE bhm.source_id = ds.id)
                    AS barrio_metric_rows
            FROM data_sources ds
            ORDER BY
                CASE WHEN ds.last_pulled_at IS NULL THEN 1 ELSE 0 END,
                ds.last_pulled_at DESC,
                ds.name
            """
        )
    ).all()

    return [
        DataSourcePublic(
            slug=r.slug,
            name=r.name,
            organization=r.organization,
            url=r.url,
            license=r.license,
            update_frequency=r.update_frequency,
            description_es=r.description_es,
            known_limitations=r.known_limitations,
            last_pulled_at=r.last_pulled_at,
            latest_data_year=r.latest_data_year,
            latest_successful_run=r.latest_successful_run,
            muni_metric_rows=int(r.muni_metric_rows or 0),
            barrio_metric_rows=int(r.barrio_metric_rows or 0),
        )
        for r in rows
    ]
