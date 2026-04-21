"""EtlRun model — logs every ETL pipeline execution."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.data_source import DataSource


class EtlRun(Base):
    """A single ETL pipeline execution.

    Every run — whether successful, partial, or failed — leaves a trace here so
    we can debug production issues and show data freshness in the UI.
    """

    __tablename__ = "etl_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("data_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column()
    status: Mapped[str] = mapped_column(Text, nullable=False)  # running/success/failed/partial

    rows_read: Mapped[int | None] = mapped_column(Integer)
    rows_upserted: Mapped[int | None] = mapped_column(Integer)
    rows_skipped: Mapped[int | None] = mapped_column(Integer)

    error_message: Mapped[str | None] = mapped_column(Text)
    git_sha: Mapped[str | None] = mapped_column(String(40))

    # Relationships
    source: Mapped["DataSource"] = relationship(back_populates="etl_runs")

    __table_args__ = (
        Index("ix_etl_runs_source_started", "source_id", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<EtlRun {self.id} source={self.source_id} status={self.status}>"
