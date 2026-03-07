"""Create gigs and portfolio_items tables

Revision ID: 001
Revises:
Create Date: 2026-03-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Minimal gigs table for portfolio badge verification.
    # The full gig feature (separate issue) will add columns via ALTER TABLE migration.
    op.create_table(
        "gigs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "status",
            sa.Enum(
                "GIG_STATUS_UNSPECIFIED",
                "GIG_STATUS_DRAFT",
                "GIG_STATUS_OPEN",
                "GIG_STATUS_IN_PROGRESS",
                "GIG_STATUS_COMPLETED",
                "GIG_STATUS_CANCELLED",
                "GIG_STATUS_DISPUTED",
                name="gig_status",
            ),
            nullable=False,
            server_default="GIG_STATUS_DRAFT",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "portfolio_items",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("file_keys", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("external_url", sa.String(2048), nullable=False, server_default=""),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        # Soft reference — no FK constraint; badge computed at read time
        sa.Column("verified_gig_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("idx_portfolio_items_user_id", "portfolio_items", ["user_id"])
    op.create_index(
        "idx_portfolio_items_created_at",
        "portfolio_items",
        ["created_at"],
        postgresql_using="btree",
    )


def downgrade() -> None:
    op.drop_index("idx_portfolio_items_created_at", table_name="portfolio_items")
    op.drop_index("idx_portfolio_items_user_id", table_name="portfolio_items")
    op.drop_table("portfolio_items")
    op.drop_table("gigs")
    op.execute("DROP TYPE IF EXISTS gig_status")
