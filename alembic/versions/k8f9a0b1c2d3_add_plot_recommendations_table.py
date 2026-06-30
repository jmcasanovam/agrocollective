"""add_plot_recommendations_table

Revision ID: k8f9a0b1c2d3
Revises: j7e8f9a0b1c2
Create Date: 2026-06-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k8f9a0b1c2d3"
down_revision: Union[str, None] = "j7e8f9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plot_recommendations",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plot_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("plots.id"), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_plot_recommendations_plot_id", "plot_recommendations", ["plot_id"])
    op.create_index("ix_plot_recommendations_run_date", "plot_recommendations", ["run_date"])
    op.create_index("ix_plot_recommendations_priority", "plot_recommendations", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_plot_recommendations_priority", "plot_recommendations")
    op.drop_index("ix_plot_recommendations_run_date", "plot_recommendations")
    op.drop_index("ix_plot_recommendations_plot_id", "plot_recommendations")
    op.drop_table("plot_recommendations")
