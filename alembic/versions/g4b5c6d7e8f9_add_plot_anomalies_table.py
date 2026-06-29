"""add_plot_anomalies_table

Revision ID: g4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-06-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g4b5c6d7e8f9"
down_revision: Union[str, None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plot_anomalies",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plot_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("plots.id"), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        sa.Column("lof_score", sa.Float(), nullable=False),
        sa.Column("is_anomaly", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("anomalous_features", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_plot_anomalies_plot_id", "plot_anomalies", ["plot_id"])
    op.create_index("ix_plot_anomalies_run_date", "plot_anomalies", ["run_date"])
    op.create_index("ix_plot_anomalies_is_anomaly", "plot_anomalies", ["is_anomaly"])


def downgrade() -> None:
    op.drop_index("ix_plot_anomalies_is_anomaly", "plot_anomalies")
    op.drop_index("ix_plot_anomalies_run_date", "plot_anomalies")
    op.drop_index("ix_plot_anomalies_plot_id", "plot_anomalies")
    op.drop_table("plot_anomalies")
