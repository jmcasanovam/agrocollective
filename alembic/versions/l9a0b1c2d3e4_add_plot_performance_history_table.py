"""add_plot_performance_history_table

Revision ID: l9a0b1c2d3e4
Revises: k8f9a0b1c2d3
Create Date: 2026-06-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "l9a0b1c2d3e4"
down_revision: Union[str, None] = "k8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plot_performance_history",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plot_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("plots.id"), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        # Sensoriales
        sa.Column("avg_soil_humidity", sa.Float(), nullable=True),
        sa.Column("avg_air_temp", sa.Float(), nullable=True),
        sa.Column("avg_soil_temp", sa.Float(), nullable=True),
        sa.Column("avg_air_humidity", sa.Float(), nullable=True),
        # Riego y cosecha
        sa.Column("irrigation_frequency", sa.Integer(), nullable=True),
        sa.Column("avg_irrigation_mm", sa.Float(), nullable=True),
        sa.Column("total_water_mm", sa.Float(), nullable=True),
        sa.Column("yield_kg_ha", sa.Float(), nullable=True),
        sa.Column("water_efficiency", sa.Float(), nullable=True),
        # Anomalía
        sa.Column("is_anomaly", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("lof_score", sa.Float(), nullable=True),
        # Predicción ML
        sa.Column("predicted_yield", sa.Float(), nullable=True),
        sa.Column("predicted_efficiency", sa.Float(), nullable=True),
        # Recomendaciones
        sa.Column("n_recommendations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_high_priority", sa.Integer(), nullable=False, server_default="0"),
        # Auditoría
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_plot_performance_history_plot_id", "plot_performance_history", ["plot_id"])
    op.create_index("ix_plot_performance_history_run_date", "plot_performance_history", ["run_date"])
    op.create_unique_constraint(
        "uq_plot_performance_history_plot_date",
        "plot_performance_history",
        ["plot_id", "run_date"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_plot_performance_history_plot_date", "plot_performance_history")
    op.drop_index("ix_plot_performance_history_run_date", "plot_performance_history")
    op.drop_index("ix_plot_performance_history_plot_id", "plot_performance_history")
    op.drop_table("plot_performance_history")
