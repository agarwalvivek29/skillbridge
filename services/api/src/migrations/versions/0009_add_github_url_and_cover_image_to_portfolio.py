"""add github_url and cover_image_url to portfolio_items

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("portfolio_items", sa.Column("github_url", sa.Text(), nullable=True))
    op.add_column(
        "portfolio_items", sa.Column("cover_image_url", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("portfolio_items", "cover_image_url")
    op.drop_column("portfolio_items", "github_url")
