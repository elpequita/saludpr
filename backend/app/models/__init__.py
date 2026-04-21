"""SQLAlchemy ORM models for SaludPR."""

from app.models.data_source import DataSource
from app.models.etl_run import EtlRun
from app.models.health_metric import HealthMetric
from app.models.hospital import Hospital
from app.models.municipality import Municipality
from app.models.vulnerability import Vulnerability

__all__ = [
    "DataSource",
    "EtlRun",
    "HealthMetric",
    "Hospital",
    "Municipality",
    "Vulnerability",
]
