"""add barrios and barrio_health_metrics

Revision ID: 0002_barrios
Revises: 0001_initial
Create Date: 2026-04-22 09:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography, Geometry

# revision identifiers, used by Alembic.
revision: str = "0002_barrios"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- barrios (sub-municipio geographic units) ---
    # IDs are 10-digit Census GEOIDs: state(2) + county(3) + cousub(5), e.g. "7212735560"
    op.create_table(
        "barrios",
        sa.Column("id", sa.String(length=10), nullable=False),
        sa.Column("muni_id", sa.String(length=5), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_normalized", sa.Text(), nullable=False),
        sa.Column(
            "geometry",
            Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column(
            "centroid",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column("area_sq_km", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("population_latest", sa.Integer(), nullable=True),
        sa.Column("population_year", sa.SmallInteger(), nullable=True),
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
        sa.ForeignKeyConstraint(["muni_id"], ["municipalities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_barrios_geometry", "barrios", ["geometry"], postgresql_using="gist"
    )
    op.create_index(
        "ix_barrios_centroid", "barrios", ["centroid"], postgresql_using="gist"
    )
    op.create_index("ix_barrios_name_normalized", "barrios", ["name_normalized"])
    op.create_index("ix_barrios_muni", "barrios", ["muni_id"])

    # --- barrio_health_metrics (same shape as health_metrics but FK to barrios) ---
    op.create_table(
        "barrio_health_metrics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("barrio_id", sa.String(length=10), nullable=False),
        sa.Column("indicator_code", sa.Text(), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("value", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("value_type", sa.Text(), nullable=False),
        sa.Column("numerator", sa.Integer(), nullable=True),
        sa.Column("denominator", sa.Integer(), nullable=True),
        sa.Column("ci_lower", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("ci_upper", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column(
            "is_suppressed", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column(
            "is_estimated", sa.Boolean(), server_default="false", nullable=False
        ),
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
        sa.ForeignKeyConstraint(["barrio_id"], ["barrios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_id"], ["data_sources.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["etl_run_id"], ["etl_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "barrio_id",
            "indicator_code",
            "year",
            "source_id",
            name="uq_bhm_barrio_indicator_year_source",
        ),
        sa.CheckConstraint(
            "value IS NULL OR value >= 0", name="ck_bhm_value_nonneg"
        ),
        sa.CheckConstraint(
            "ci_lower IS NULL OR ci_upper IS NULL OR ci_lower <= ci_upper",
            name="ck_bhm_ci_valid",
        ),
    )
    op.create_index(
        "ix_bhm_indicator_year", "barrio_health_metrics", ["indicator_code", "year"]
    )
    op.create_index(
        "ix_bhm_barrio_indicator",
        "barrio_health_metrics",
        ["barrio_id", "indicator_code"],
    )

    # --- View: latest metric value per barrio/indicator ---
    op.execute(
        """
        CREATE OR REPLACE VIEW v_latest_barrio_metrics AS
        SELECT DISTINCT ON (barrio_id, indicator_code, source_id)
            barrio_id,
            indicator_code,
            year,
            value,
            value_type,
            ci_lower,
            ci_upper,
            is_suppressed,
            source_id
        FROM barrio_health_metrics
        ORDER BY barrio_id, indicator_code, source_id, year DESC;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_latest_barrio_metrics;")
    op.drop_index("ix_bhm_barrio_indicator", table_name="barrio_health_metrics")
    op.drop_index("ix_bhm_indicator_year", table_name="barrio_health_metrics")
    op.drop_table("barrio_health_metrics")
    op.drop_index("ix_barrios_muni", table_name="barrios")
    op.drop_index("ix_barrios_name_normalized", table_name="barrios")
    op.drop_index("ix_barrios_centroid", table_name="barrios")
    op.drop_index("ix_barrios_geometry", table_name="barrios")
    op.drop_table("barrios")
