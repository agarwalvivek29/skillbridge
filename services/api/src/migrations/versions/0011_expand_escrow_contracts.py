"""expand escrow_contracts with proto-canonical field names

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "escrow_contracts", "contract_address", new_column_name="chain_address"
    )
    op.alter_column(
        "escrow_contracts", "tx_signature", new_column_name="funding_tx_hash"
    )
    op.add_column("escrow_contracts", sa.Column("network", sa.Text(), nullable=True))
    op.add_column(
        "escrow_contracts", sa.Column("total_amount", sa.Text(), nullable=True)
    )
    op.add_column(
        "escrow_contracts",
        sa.Column("released_amount", sa.Text(), nullable=True, server_default="0"),
    )
    op.add_column(
        "escrow_contracts",
        sa.Column("status", sa.String(32), nullable=True),
    )
    op.add_column(
        "escrow_contracts", sa.Column("token_address", sa.Text(), nullable=True)
    )
    op.add_column(
        "escrow_contracts",
        sa.Column(
            "platform_fee_basis_points",
            sa.Integer(),
            nullable=True,
            server_default="500",
        ),
    )
    op.add_column(
        "escrow_contracts",
        sa.Column("platform_fee_amount", sa.Text(), nullable=True, server_default="0"),
    )
    op.add_column(
        "escrow_contracts",
        sa.Column("platform_fee_recipient", sa.Text(), nullable=True),
    )
    op.add_column(
        "escrow_contracts",
        sa.Column("funded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "escrow_contracts",
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("escrow_contracts", "settled_at")
    op.drop_column("escrow_contracts", "funded_at")
    op.drop_column("escrow_contracts", "platform_fee_recipient")
    op.drop_column("escrow_contracts", "platform_fee_amount")
    op.drop_column("escrow_contracts", "platform_fee_basis_points")
    op.drop_column("escrow_contracts", "token_address")
    op.drop_column("escrow_contracts", "status")
    op.drop_column("escrow_contracts", "released_amount")
    op.drop_column("escrow_contracts", "total_amount")
    op.drop_column("escrow_contracts", "network")
    op.alter_column(
        "escrow_contracts", "funding_tx_hash", new_column_name="tx_signature"
    )
    op.alter_column(
        "escrow_contracts", "chain_address", new_column_name="contract_address"
    )
