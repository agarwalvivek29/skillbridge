"""add tx_signature column to escrow_contracts

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-14

Changes:
- Adds `escrow_contracts.tx_signature` (Text, nullable) to store the Solana
  transaction signature that confirms the escrow deposit on-chain.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "escrow_contracts",
        sa.Column("tx_signature", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("escrow_contracts", "tx_signature")
