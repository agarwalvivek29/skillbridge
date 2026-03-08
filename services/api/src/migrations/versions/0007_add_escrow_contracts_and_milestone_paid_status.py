"""add escrow_contracts table and milestone PAID status

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-08

Changes:
- Creates the `escrow_contracts` table with a `release_tx_hash` column
  to store the on-chain tx hash after fund release is confirmed.
- The `milestones.status` column now accepts PAID and REVISION_REQUESTED
  as valid values (String column, no schema enforcement needed — comment
  updated on MilestoneModel for documentation purposes).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "escrow_contracts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "gig_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("gigs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("contract_address", sa.Text, nullable=False),
        # Stores the completeMilestone() tx_hash after the client confirms release
        sa.Column("release_tx_hash", sa.Text, nullable=True),
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
    op.create_index("ix_escrow_contracts_gig_id", "escrow_contracts", ["gig_id"])


def downgrade() -> None:
    op.drop_index("ix_escrow_contracts_gig_id", table_name="escrow_contracts")
    op.drop_table("escrow_contracts")
