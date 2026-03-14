"""rename gigs.contract_address to escrow_pda

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-14

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("gigs", "contract_address", new_column_name="escrow_pda")


def downgrade() -> None:
    op.alter_column("gigs", "escrow_pda", new_column_name="contract_address")
