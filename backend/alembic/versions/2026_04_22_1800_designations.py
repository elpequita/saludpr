"""add muni_designations table for HRSA MUA/P + future HPSA data

Revision ID: 0004_designations
Revises: 0003_territory
Create Date: 2026-04-22 18:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_designations"
down_revision: Union[str, None] = "0003_territory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # muni_designations — federal designations (MUA/P, HPSA) at municipio level.
    # Distinct from health_metrics because these are categorical ref data with
    # effective-dates, not time-series observations.
    op.create_table(
        "muni_designations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        # External natural key (HRSA's MUA/P ID, e.g. "03920")
        sa.Column("external_id", sa.Text(), nullable=False),
        # Parent geography
        sa.Column("muni_id", sa.String(length=5), nullable=False),
        # Designation metadata
        sa.Column(
            "designation_code",
            sa.String(length=16),
            nullable=False,
        ),  # e.g. 'MUA', 'MUP', 'HPSA'
        sa.Column("designation_name", sa.Text(), nullable=False),
        sa.Column("population_type_code", sa.String(length=16), nullable=True),
        sa.Column("population_type", sa.Text(), nullable=True),
        # Severity / status
        sa.Column("imu_score", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("status_code", sa.String(length=2), nullable=True),
        sa.Column("status_description", sa.Text(), nullable=True),
        # Timeline
        sa.Column("designation_date", sa.Date(), nullable=True),
        sa.Column("update_date", sa.Date(), nullable=True),
        sa.Column("withdrawal_date", sa.Date(), nullable=True),
        sa.Column("break_in_designation", sa.Boolean(), nullable=True),
        # Context
        sa.Column("rural_status_code", sa.String(length=2), nullable=True),
        sa.Column("rural_status", sa.Text(), nullable=True),
        sa.Column(
            "designated_population", sa.Integer(), nullable=True
        ),  # population covered by this designation
        sa.Column("service_area_name", sa.Text(), nullable=True),
        # Provenance
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("etl_run_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["muni_id"], ["municipalities.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["data_sources.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["etl_run_id"], ["etl_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "external_id",
            "source_id",
            name="uq_muni_designations_external",
        ),
        sa.CheckConstraint(
            "imu_score IS NULL OR (imu_score >= 0 AND imu_score <= 100)",
            name="ck_muni_designations_imu_range",
        ),
    )
    op.create_index(
        "ix_muni_designations_muni", "muni_designations", ["muni_id"]
    )
    op.create_index(
        "ix_muni_designations_code",
        "muni_designations",
        ["designation_code", "status_code"],
    )

    # View: latest active designation per muni (for fast joins)
    op.execute(
        """
        CREATE OR REPLACE VIEW v_muni_active_designations AS
        SELECT
            md.muni_id,
            md.designation_code,
            md.designation_name,
            md.imu_score,
            md.designation_date,
            md.rural_status,
            md.designated_population,
            md.source_id
        FROM muni_designations md
        WHERE md.status_code = 'D'
          AND md.withdrawal_date IS NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_muni_active_designations;")
    op.drop_index("ix_muni_designations_code", table_name="muni_designations")
    op.drop_index("ix_muni_designations_muni", table_name="muni_designations")
    op.drop_table("muni_designations")
