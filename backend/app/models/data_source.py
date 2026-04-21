"""DataSource model — every external dataset we pull from."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.etl_run import EtlRun
    from app.models.health_metric import HealthMetric
    from app.models.hospital import Hospital
    from app.models.vulnerability import Vulnerability


class DataSource(Base):
    """A public data source that SaludPR pulls from.

    Every metric row in the database references one of these so users can trace
    any number back to the originating public dataset.
    """

    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    organization: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    license: Mapped[str] = mapped_column(Text, nullable=False)
    update_frequency: Mapped[str | None] = mapped_column(Text)

    description_en: Mapped[str | None] = mapped_column(Text)
    description_es: Mapped[str | None] = mapped_column(Text)
    known_limitations: Mapped[str | None] = mapped_column(Text)

    last_pulled_at: Mapped[datetime | None] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    etl_runs: Mapped[list["EtlRun"]] = relationship(back_populates="source")
    health_metrics: Mapped[list["HealthMetric"]] = relationship(back_populates="source")
    hospitals: Mapped[list["Hospital"]] = relationship(back_populates="source")
    vulnerability_records: Mapped[list["Vulnerability"]] = relationship(
        back_populates="source"
    )

    def __repr__(self) -> str:
        return f"<DataSource {self.slug}>"
