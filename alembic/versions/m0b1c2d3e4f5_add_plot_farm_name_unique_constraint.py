"""add_plot_farm_name_unique_constraint

Revision ID: m0b1c2d3e4f5
Revises: l9a0b1c2d3e4
Create Date: 2026-07-03
"""
from typing import Sequence, Union

from alembic import op

revision: str = "m0b1c2d3e4f5"
down_revision: Union[str, None] = "l9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_plot_farm_name", "plots", ["farm_id", "name"])


def downgrade() -> None:
    op.drop_constraint("uq_plot_farm_name", "plots")
