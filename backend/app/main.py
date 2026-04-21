"""SaludPR FastAPI application — entrypoint.

Public health data API for Puerto Rico. Serves aggregated, publicly-sourced data
from CDC, HRSA, US Census, PR Dept of Health, and CMS.

Run locally:
    cd backend && uv run uvicorn app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health, municipalities


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hooks — placeholder for now."""
    yield


app = FastAPI(
    title="SaludPR API",
    description=(
        "Public health data for Puerto Rico — chronic disease rates, hospital "
        "capacity, and medically underserved zones by municipality. "
        "Every value is traceable to a public source."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(municipalities.router, prefix="/api", tags=["municipalities"])
