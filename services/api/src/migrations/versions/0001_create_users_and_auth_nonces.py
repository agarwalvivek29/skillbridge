"""create users and auth_nonces tables

Revision ID: 0001
Revises:
Create Date: 2026-03-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("email", sa.Text, unique=True, nullable=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=True),
        sa.Column("wallet_address", sa.Text, unique=True, nullable=True),
        sa.Column(
            "role", sa.String(32), nullable=False, server_default="USER_ROLE_FREELANCER"
        ),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="USER_STATUS_ACTIVE"
        ),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("bio", sa.Text, nullable=True),
        sa.Column(
            "skills",
            postgresql.ARRAY(sa.Text),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("hourly_rate_wei", sa.Text, nullable=False, server_default="0"),
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
        "auth_nonces",
        sa.Column("wallet_address", sa.Text, primary_key=True),
        sa.Column("nonce", sa.Text, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("auth_nonces")
    op.drop_table("users")
