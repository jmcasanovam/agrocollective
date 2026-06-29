"""add_plot_causal_results_table

Revision ID: h5c6d7e8f9a0
Revises: g4b5c6d7e8f9
Create Date: 2026-06-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h5c6d7e8f9a0"
down_revision: Union[str, None] = "g4b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plot_causal_results",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plot_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("plots.id"), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        sa.Column("anomalous_feature", sa.String(60), nullable=False),
        sa.Column("causal_feature", sa.String(60), nullable=True),
        sa.Column("correlation", sa.Float(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_plot_causal_results_plot_id", "plot_causal_results", ["plot_id"])
    op.create_index("ix_plot_causal_results_run_date", "plot_causal_results", ["run_date"])


def downgrade() -> None:
    op.drop_index("ix_plot_causal_results_run_date", "plot_causal_results")
    op.drop_index("ix_plot_causal_results_plot_id", "plot_causal_results")
    op.drop_table("plot_causal_results")
