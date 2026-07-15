"""add_device_plot_unique_constraint

Revision ID: n1c2d3e4f5g6
Revises: m0b1c2d3e4f5
Create Date: 2026-07-03
"""
from typing import Sequence, Union

from alembic import op

revision: str = "n1c2d3e4f5g6"
down_revision: Union[str, None] = "m0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_device_plot_id", "devices", ["plot_id"])


def downgrade() -> None:
    op.drop_constraint("uq_device_plot_id", "devices")
