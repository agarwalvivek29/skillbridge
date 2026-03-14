"""add escrow_contracts table, milestone release_tx_hash, and PAID/REVISION_REQUESTED statuses

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-08

Changes:
- Creates the `escrow_contracts` table (contract_address per gig; no tx_hash here).
- Adds `milestones.release_tx_hash` to store the completeMilestone() tx_hash per
  milestone after the client confirms fund release.  Keeping it on the milestone
  (rather than on escrow_contracts) is correct because a gig has N milestones and
  each one gets its own on-chain tx.
- Adds an ON UPDATE trigger for escrow_contracts.updated_at so it is kept accurate
  even when rows are updated via raw SQL (e.g. tests, migrations).
- The `milestones.status` column now accepts PAID and REVISION_REQUESTED as valid
  values (String column, no schema enforcement needed — comment updated on
  MilestoneModel for documentation purposes).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "escrow_contracts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "gig_id",
            sa.String(36),
            sa.ForeignKey("gigs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("contract_address", sa.Text, nullable=False),
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

    # Keep updated_at accurate on raw-SQL updates (ORM onupdate= only fires for ORM ops)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_escrow_contracts_updated_at
        BEFORE UPDATE ON escrow_contracts
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )

    # release_tx_hash belongs on the milestone — each milestone has its own on-chain tx
    op.add_column(
        "milestones",
        sa.Column("release_tx_hash", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("milestones", "release_tx_hash")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_escrow_contracts_updated_at ON escrow_contracts"
    )
    op.execute("DROP FUNCTION IF EXISTS set_updated_at")
    op.drop_index("ix_escrow_contracts_gig_id", table_name="escrow_contracts")
    op.drop_table("escrow_contracts")
