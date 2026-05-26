"""Add operator access fields.

Revision ID: 20260526_1130
Revises: 20260526_1050
Create Date: 2026-05-26 11:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260526_1130"
down_revision: str | None = "20260526_1050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "internal_users",
        sa.Column("is_operator", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "invite_codes",
        sa.Column("grants_operator", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("invite_codes", "grants_operator")
    op.drop_column("internal_users", "is_operator")
