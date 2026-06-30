"""add_plot_clusters_table

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-06-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plot_clusters",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plot_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("plots.id"), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        sa.Column("distance_to_centroid", sa.Float(), nullable=True),
        sa.Column("cluster_size", sa.Integer(), nullable=True),
        sa.Column("cluster_avg_soil_humidity", sa.Float(), nullable=True),
        sa.Column("cluster_avg_air_temp", sa.Float(), nullable=True),
        sa.Column("cluster_avg_irrigation_mm", sa.Float(), nullable=True),
        sa.Column("cluster_avg_efficiency", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_plot_clusters_plot_id", "plot_clusters", ["plot_id"])
    op.create_index("ix_plot_clusters_run_date", "plot_clusters", ["run_date"])


def downgrade() -> None:
    op.drop_index("ix_plot_clusters_run_date", "plot_clusters")
    op.drop_index("ix_plot_clusters_plot_id", "plot_clusters")
    op.drop_table("plot_clusters")
