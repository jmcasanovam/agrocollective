"""add_plot_ml_predictions_table

Revision ID: j7e8f9a0b1c2
Revises: i6d7e8f9a0b1
Create Date: 2026-06-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j7e8f9a0b1c2"
down_revision: Union[str, None] = "i6d7e8f9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plot_ml_predictions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plot_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("plots.id"), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        sa.Column("target", sa.String(40), nullable=False),
        sa.Column("predicted_value", sa.Float(), nullable=True),
        sa.Column("model_r2", sa.Float(), nullable=True),
        sa.Column("n_training_samples", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_plot_ml_predictions_plot_id", "plot_ml_predictions", ["plot_id"])
    op.create_index("ix_plot_ml_predictions_run_date", "plot_ml_predictions", ["run_date"])


def downgrade() -> None:
    op.drop_index("ix_plot_ml_predictions_run_date", "plot_ml_predictions")
    op.drop_index("ix_plot_ml_predictions_plot_id", "plot_ml_predictions")
    op.drop_table("plot_ml_predictions")
