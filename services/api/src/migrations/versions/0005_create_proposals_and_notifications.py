"""create proposals and notifications tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "proposals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "gig_id",
            sa.String(36),
            sa.ForeignKey("gigs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "freelancer_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("cover_letter", sa.Text, nullable=False),
        sa.Column("estimated_days", sa.Integer, nullable=False),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="PENDING",
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
        sa.UniqueConstraint(
            "gig_id", "freelancer_id", name="uq_proposal_gig_freelancer"
        ),
    )


def downgrade() -> None:
    op.drop_table("proposals")
