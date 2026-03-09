"""create reputation table

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-09

Changes:
- Creates the `reputation` table: per-user cache of on-chain reputation data.
  One row per user (unique on wallet_address). Synced from the Reputation
  contract on Base L2 via background job.
- Fields match api/v1/reputation.proto: gigs_completed, gigs_as_client,
  total_earned (string to avoid precision loss), average_ai_score,
  dispute_rate_pct, average_rating_x100, rating_count, last_synced_at.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reputation",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("wallet_address", sa.Text, nullable=False, unique=True),
        sa.Column("gigs_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("gigs_as_client", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_earned", sa.Text, nullable=False, server_default="0"),
        sa.Column("average_ai_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("dispute_rate_pct", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "average_rating_x100", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column("rating_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_reputation_user_id", "reputation", ["user_id"])
    op.create_index("ix_reputation_wallet_address", "reputation", ["wallet_address"])

    # Keep updated_at accurate on raw-SQL updates
    op.execute(
        """
        CREATE TRIGGER trg_reputation_updated_at
        BEFORE UPDATE ON reputation
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_reputation_updated_at ON reputation")
    op.drop_index("ix_reputation_wallet_address", table_name="reputation")
    op.drop_index("ix_reputation_user_id", table_name="reputation")
    op.drop_table("reputation")
