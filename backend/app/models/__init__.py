"""SQLAlchemy ORM models for SaludPR."""

from app.models.barrio import Barrio
from app.models.barrio_health_metric import BarrioHealthMetric
from app.models.data_source import DataSource
from app.models.etl_run import EtlRun
from app.models.health_metric import HealthMetric
from app.models.hospital import Hospital
from app.models.muni_designation import MuniDesignation
from app.models.municipality import Municipality
from app.models.territory_health_metric import TerritoryHealthMetric
from app.models.vulnerability import Vulnerability

__all__ = [
    "Barrio",
    "BarrioHealthMetric",
    "DataSource",
    "EtlRun",
    "HealthMetric",
    "Hospital",
    "MuniDesignation",
    "Municipality",
    "TerritoryHealthMetric",
    "Vulnerability",
]
