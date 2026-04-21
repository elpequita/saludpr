"""Health check endpoint — verifies app + database are reachable."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.database import DbSession

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    database: str
    municipalities_loaded: int


@router.get("/health", response_model=HealthResponse)
def health(db: DbSession) -> HealthResponse:
    """Return app status + basic DB connectivity check."""
    try:
        count = db.execute(text("SELECT COUNT(*) FROM municipalities")).scalar_one()
        db_status = "ok"
    except Exception:  # noqa: BLE001 — we genuinely want a bare catch for the health check
        count = 0
        db_status = "error"

    return HealthResponse(
        status="ok",
        database=db_status,
        municipalities_loaded=int(count),
    )
