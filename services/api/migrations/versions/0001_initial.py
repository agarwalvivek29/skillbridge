"""initial: users and siwe_nonces tables

Revision ID: 0001
Revises:
Create Date: 2026-03-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=True, unique=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("wallet_address", sa.String(42), nullable=True, unique=True),
        sa.Column(
            "status",
            sa.Enum(
                "USER_STATUS_PENDING_VERIFICATION",
                "USER_STATUS_ACTIVE",
                "USER_STATUS_INACTIVE",
                "USER_STATUS_BANNED",
                name="user_status",
            ),
            nullable=False,
            server_default="USER_STATUS_ACTIVE",
        ),
        sa.Column(
            "role",
            sa.Enum(
                "USER_ROLE_MEMBER",
                "USER_ROLE_ADMIN",
                "USER_ROLE_SUPER_ADMIN",
                name="user_role",
            ),
            nullable=False,
            server_default="USER_ROLE_MEMBER",
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
        sa.CheckConstraint(
            "email IS NOT NULL OR wallet_address IS NOT NULL",
            name="users_identity_check",
        ),
    )

    op.create_table(
        "siwe_nonces",
        sa.Column("nonce", sa.String(64), primary_key=True),
        sa.Column("address", sa.String(42), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_siwe_nonces_address", "siwe_nonces", ["address"])
    op.create_index("idx_siwe_nonces_expires_at", "siwe_nonces", ["expires_at"])


def downgrade() -> None:
    op.drop_index("idx_siwe_nonces_expires_at", table_name="siwe_nonces")
    op.drop_index("idx_siwe_nonces_address", table_name="siwe_nonces")
    op.drop_table("siwe_nonces")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS user_status")
    op.execute("DROP TYPE IF EXISTS user_role")
