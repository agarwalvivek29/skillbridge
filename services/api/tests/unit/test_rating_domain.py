"""
Unit tests for domain/rating.py — blind mutual ratings and reviews.

Uses SQLite in-memory (aiosqlite) — no Docker dependency.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.gig import CreateGigInput, MilestoneInput, create_gig
from src.domain.rating import (
    ReviewValidationError,
    compute_average_rating_x100,
    create_review,
    get_gig_reviews,
    get_user_reviews,
)
from src.infra.database import Base
from src.infra.models import GigModel, ReviewModel

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_CLIENT_ID = "cccccccc-0000-0000-0000-000000000001"
_FREELANCER_ID = "ffffffff-0000-0000-0000-000000000001"
_OTHER_USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _make_gig_input() -> CreateGigInput:
    return CreateGigInput(
        title="Build API",
        description="REST API project",
        total_amount="1000",
        currency="ETH",
        required_skills=["Python"],
        milestones=[
            MilestoneInput(
                title="Milestone 1",
                description="First milestone",
                acceptance_criteria="## Tests pass",
                amount="1000",
                order=1,
            )
        ],
    )


async def _setup_completed_gig(db: AsyncSession) -> str:
    """Create a COMPLETED gig with client + freelancer. Returns gig_id."""
    gig = await create_gig(db, _CLIENT_ID, _make_gig_input())
    await db.execute(
        sa_update(GigModel)
        .where(GigModel.id == gig.id)
        .values(status="COMPLETED", freelancer_id=_FREELANCER_ID)
    )
    await db.flush()
    return gig.id


# ---------------------------------------------------------------------------
# create_review
# ---------------------------------------------------------------------------


class TestCreateReview:
    @pytest.mark.asyncio
    async def test_client_can_review_freelancer(self, db: AsyncSession):
        gig_id = await _setup_completed_gig(db)
        review = await create_review(
            db,
            gig_id=gig_id,
            reviewer_id=_CLIENT_ID,
            reviewer_role="USER_ROLE_CLIENT",
            rating=4,
            comment="Great work!",
        )
        assert review.id is not None
        assert review.reviewer_id == _CLIENT_ID
        assert review.reviewee_id == _FREELANCER_ID
        assert review.rating == 4
        assert review.is_visible is False

    @pytest.mark.asyncio
    async def test_freelancer_can_review_client(self, db: AsyncSession):
        gig_id = await _setup_completed_gig(db)
        review = await create_review(
            db,
            gig_id=gig_id,
            reviewer_id=_FREELANCER_ID,
            reviewer_role="USER_ROLE_FREELANCER",
            rating=5,
            comment="Good client",
        )
        assert review.reviewer_id == _FREELANCER_ID
        assert review.reviewee_id == _CLIENT_ID
        assert review.is_visible is False

    @pytest.mark.asyncio
    async def test_both_submit_triggers_reveal(self, db: AsyncSession):
        gig_id = await _setup_completed_gig(db)
        r1 = await create_review(
            db,
            gig_id=gig_id,
            reviewer_id=_CLIENT_ID,
            reviewer_role="USER_ROLE_CLIENT",
            rating=4,
            comment="",
        )
        assert r1.is_visible is False

        r2 = await create_review(
            db,
            gig_id=gig_id,
            reviewer_id=_FREELANCER_ID,
            reviewer_role="USER_ROLE_FREELANCER",
            rating=5,
            comment="",
        )
        # Both should now be visible
        assert r2.is_visible is True
        await db.refresh(r1)
        assert r1.is_visible is True

    @pytest.mark.asyncio
    async def test_non_completed_gig_raises(self, db: AsyncSession):
        gig = await create_gig(db, _CLIENT_ID, _make_gig_input())
        # gig is in DRAFT status
        with pytest.raises(ReviewValidationError) as exc_info:
            await create_review(
                db,
                gig_id=gig.id,
                reviewer_id=_CLIENT_ID,
                reviewer_role="USER_ROLE_CLIENT",
                rating=4,
                comment="",
            )
        assert exc_info.value.code == "GIG_NOT_COMPLETED"

    @pytest.mark.asyncio
    async def test_non_participant_raises(self, db: AsyncSession):
        gig_id = await _setup_completed_gig(db)
        with pytest.raises(ReviewValidationError) as exc_info:
            await create_review(
                db,
                gig_id=gig_id,
                reviewer_id=_OTHER_USER_ID,
                reviewer_role="USER_ROLE_CLIENT",
                rating=4,
                comment="",
            )
        assert exc_info.value.code == "NOT_GIG_PARTICIPANT"

    @pytest.mark.asyncio
    async def test_duplicate_review_raises(self, db: AsyncSession):
        gig_id = await _setup_completed_gig(db)
        await create_review(
            db,
            gig_id=gig_id,
            reviewer_id=_CLIENT_ID,
            reviewer_role="USER_ROLE_CLIENT",
            rating=4,
            comment="",
        )
        with pytest.raises(ReviewValidationError) as exc_info:
            await create_review(
                db,
                gig_id=gig_id,
                reviewer_id=_CLIENT_ID,
                reviewer_role="USER_ROLE_CLIENT",
                rating=5,
                comment="Changed my mind",
            )
        assert exc_info.value.code == "ALREADY_REVIEWED"

    @pytest.mark.asyncio
    async def test_invalid_rating_raises(self, db: AsyncSession):
        gig_id = await _setup_completed_gig(db)
        with pytest.raises(ReviewValidationError) as exc_info:
            await create_review(
                db,
                gig_id=gig_id,
                reviewer_id=_CLIENT_ID,
                reviewer_role="USER_ROLE_CLIENT",
                rating=0,
                comment="",
            )
        assert exc_info.value.code == "INVALID_RATING"

    @pytest.mark.asyncio
    async def test_rating_above_5_raises(self, db: AsyncSession):
        gig_id = await _setup_completed_gig(db)
        with pytest.raises(ReviewValidationError) as exc_info:
            await create_review(
                db,
                gig_id=gig_id,
                reviewer_id=_CLIENT_ID,
                reviewer_role="USER_ROLE_CLIENT",
                rating=6,
                comment="",
            )
        assert exc_info.value.code == "INVALID_RATING"

    @pytest.mark.asyncio
    async def test_comment_too_long_raises(self, db: AsyncSession):
        gig_id = await _setup_completed_gig(db)
        with pytest.raises(ReviewValidationError) as exc_info:
            await create_review(
                db,
                gig_id=gig_id,
                reviewer_id=_CLIENT_ID,
                reviewer_role="USER_ROLE_CLIENT",
                rating=4,
                comment="x" * 501,
            )
        assert exc_info.value.code == "COMMENT_TOO_LONG"

    @pytest.mark.asyncio
    async def test_gig_not_found_raises(self, db: AsyncSession):
        with pytest.raises(ReviewValidationError) as exc_info:
            await create_review(
                db,
                gig_id="00000000-0000-0000-0000-000000000000",
                reviewer_id=_CLIENT_ID,
                reviewer_role="USER_ROLE_CLIENT",
                rating=4,
                comment="",
            )
        assert exc_info.value.code == "GIG_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_notification_created_on_reveal(self, db: AsyncSession):
        from sqlalchemy import select
        from src.infra.models import NotificationModel

        gig_id = await _setup_completed_gig(db)
        await create_review(
            db,
            gig_id=gig_id,
            reviewer_id=_CLIENT_ID,
            reviewer_role="USER_ROLE_CLIENT",
            rating=4,
            comment="",
        )
        # First review: not visible yet, no notification
        result = await db.execute(
            select(NotificationModel).where(
                NotificationModel.type == "NOTIFICATION_TYPE_REVIEW_RECEIVED"
            )
        )
        assert result.scalars().all() == []

        await create_review(
            db,
            gig_id=gig_id,
            reviewer_id=_FREELANCER_ID,
            reviewer_role="USER_ROLE_FREELANCER",
            rating=5,
            comment="",
        )
        # Both revealed: notifications for both reviewees
        result = await db.execute(
            select(NotificationModel).where(
                NotificationModel.type == "NOTIFICATION_TYPE_REVIEW_RECEIVED"
            )
        )
        notifications = result.scalars().all()
        notified_users = {n.user_id for n in notifications}
        assert _FREELANCER_ID in notified_users
        assert _CLIENT_ID in notified_users


# ---------------------------------------------------------------------------
# get_gig_reviews / get_user_reviews
# ---------------------------------------------------------------------------


class TestGetReviews:
    @pytest.mark.asyncio
    async def test_get_gig_reviews_only_visible(self, db: AsyncSession):
        gig_id = await _setup_completed_gig(db)
        await create_review(
            db,
            gig_id=gig_id,
            reviewer_id=_CLIENT_ID,
            reviewer_role="USER_ROLE_CLIENT",
            rating=4,
            comment="",
        )
        # Only one review submitted -> not visible
        reviews = await get_gig_reviews(db, gig_id)
        assert len(reviews) == 0

    @pytest.mark.asyncio
    async def test_get_gig_reviews_both_visible(self, db: AsyncSession):
        gig_id = await _setup_completed_gig(db)
        await create_review(
            db,
            gig_id=gig_id,
            reviewer_id=_CLIENT_ID,
            reviewer_role="USER_ROLE_CLIENT",
            rating=4,
            comment="",
        )
        await create_review(
            db,
            gig_id=gig_id,
            reviewer_id=_FREELANCER_ID,
            reviewer_role="USER_ROLE_FREELANCER",
            rating=5,
            comment="",
        )
        reviews = await get_gig_reviews(db, gig_id)
        assert len(reviews) == 2

    @pytest.mark.asyncio
    async def test_get_gig_reviews_7day_window(self, db: AsyncSession):
        from sqlalchemy import update as sa_upd

        gig_id = await _setup_completed_gig(db)
        review = await create_review(
            db,
            gig_id=gig_id,
            reviewer_id=_CLIENT_ID,
            reviewer_role="USER_ROLE_CLIENT",
            rating=4,
            comment="",
        )
        # Manually backdate the review to 8 days ago
        old_time = datetime.now(timezone.utc) - timedelta(days=8)
        await db.execute(
            sa_upd(ReviewModel)
            .where(ReviewModel.id == review.id)
            .values(created_at=old_time)
        )
        await db.flush()

        reviews = await get_gig_reviews(db, gig_id)
        # Should be visible due to window expiry even though only one review
        assert len(reviews) == 1
        assert reviews[0].id == review.id

    @pytest.mark.asyncio
    async def test_get_user_reviews_returns_visible_only(self, db: AsyncSession):
        gig_id = await _setup_completed_gig(db)
        await create_review(
            db,
            gig_id=gig_id,
            reviewer_id=_CLIENT_ID,
            reviewer_role="USER_ROLE_CLIENT",
            rating=4,
            comment="",
        )
        # Freelancer has one review as reviewee, but not visible
        reviews = await get_user_reviews(db, _FREELANCER_ID)
        assert len(reviews) == 0

        # Both submit
        await create_review(
            db,
            gig_id=gig_id,
            reviewer_id=_FREELANCER_ID,
            reviewer_role="USER_ROLE_FREELANCER",
            rating=5,
            comment="",
        )
        reviews = await get_user_reviews(db, _FREELANCER_ID)
        assert len(reviews) == 1
        assert reviews[0].reviewee_id == _FREELANCER_ID


# ---------------------------------------------------------------------------
# compute_average_rating_x100
# ---------------------------------------------------------------------------


class TestComputeAverage:
    def test_empty_list(self):
        assert compute_average_rating_x100([]) == 0

    def test_single_review(self):
        r = ReviewModel(rating=4)
        assert compute_average_rating_x100([r]) == 400

    def test_multiple_reviews(self):
        reviews = [ReviewModel(rating=4), ReviewModel(rating=5)]
        assert compute_average_rating_x100(reviews) == 450

    def test_rounding(self):
        reviews = [ReviewModel(rating=3), ReviewModel(rating=4), ReviewModel(rating=5)]
        # (3+4+5)/3 = 4.0 -> 400
        assert compute_average_rating_x100(reviews) == 400
