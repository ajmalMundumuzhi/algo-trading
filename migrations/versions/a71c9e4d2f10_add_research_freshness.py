
"""add research freshness timestamp

Revision ID: a71c9e4d2f10
Revises: c4b36b282bca
"""

from alembic import op
import sqlalchemy as sa


revision = "a71c9e4d2f10"
down_revision = "c4b36b282bca"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "research_watchlist",
        sa.Column(
            "last_researched_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "research_watchlist",
        "last_researched_at",
    )
