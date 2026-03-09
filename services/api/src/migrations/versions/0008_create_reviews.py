"""create reviews table

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "gig_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("gigs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reviewer_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "reviewee_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "is_visible",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("gig_id", "reviewer_id", name="uq_review_gig_reviewer"),
    )

    op.create_index("ix_reviews_gig_id", "reviews", ["gig_id"])
    op.create_index("ix_reviews_reviewee_id", "reviews", ["reviewee_id"])


def downgrade() -> None:
    op.drop_index("ix_reviews_reviewee_id", table_name="reviews")
    op.drop_index("ix_reviews_gig_id", table_name="reviews")
    op.drop_table("reviews")
