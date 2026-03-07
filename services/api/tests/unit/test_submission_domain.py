"""
Unit tests for domain/submission.py.

Uses SQLite in-memory (aiosqlite) — no Docker dependency.
Celery enqueue is mocked to avoid Redis dependency.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.gig import CreateGigInput, MilestoneInput, create_gig
from src.domain.submission import (
    SubmissionValidationError,
    create_submission,
    get_submission,
    list_submissions,
)
from src.infra.database import Base
from src.infra.models import GigModel

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_CLIENT_ID = "cccccccc-0000-0000-0000-000000000001"
_FREELANCER_ID = "ffffffff-0000-0000-0000-000000000001"
_OTHER_FREELANCER_ID = "ffffffff-0000-0000-0000-000000000002"

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


async def _setup_in_progress_gig(db: AsyncSession) -> tuple[str, str]:
    """Create a gig and assign a freelancer. Returns (gig_id, milestone_id)."""
    gig = await create_gig(db, _CLIENT_ID, _make_gig_input())
    await db.execute(
        sa_update(GigModel)
        .where(GigModel.id == gig.id)
        .values(status="IN_PROGRESS", freelancer_id=_FREELANCER_ID)
    )
    await db.flush()
    milestone_id = gig.milestones[0].id
    return gig.id, milestone_id


# ---------------------------------------------------------------------------
# create_submission
# ---------------------------------------------------------------------------


class TestCreateSubmission:
    @pytest.mark.asyncio
    async def test_happy_path_first_submission(self, db: AsyncSession):
        with patch("src.domain.submission.enqueue_review"):
            _, milestone_id = await _setup_in_progress_gig(db)
            submission = await create_submission(
                db,
                freelancer_id=_FREELANCER_ID,
                milestone_id=milestone_id,
                repo_url="https://github.com/user/repo",
                file_keys=[],
                notes="Done!",
                previous_submission_id=None,
            )
        assert submission.id is not None
        assert submission.revision_number == 1
        assert submission.previous_submission_id is None
        assert submission.status == "UNDER_REVIEW"
        assert submission.milestone_id == milestone_id

    @pytest.mark.asyncio
    async def test_milestone_and_revision_count_updated(self, db: AsyncSession):
        from src.infra.models import MilestoneModel
        from sqlalchemy import select

        with patch("src.domain.submission.enqueue_review"):
            _, milestone_id = await _setup_in_progress_gig(db)
            await create_submission(
                db,
                freelancer_id=_FREELANCER_ID,
                milestone_id=milestone_id,
                repo_url="https://github.com/user/repo",
                file_keys=[],
                notes="",
                previous_submission_id=None,
            )

        result = await db.execute(
            select(MilestoneModel).where(MilestoneModel.id == milestone_id)
        )
        milestone = result.scalar_one()
        assert milestone.status == "UNDER_REVIEW"
        assert milestone.revision_count == 1

    @pytest.mark.asyncio
    async def test_notification_created_for_client(self, db: AsyncSession):
        from src.infra.models import NotificationModel
        from sqlalchemy import select

        with patch("src.domain.submission.enqueue_review"):
            _, milestone_id = await _setup_in_progress_gig(db)
            await create_submission(
                db,
                freelancer_id=_FREELANCER_ID,
                milestone_id=milestone_id,
                repo_url="https://github.com/user/repo",
                file_keys=[],
                notes="",
                previous_submission_id=None,
            )

        result = await db.execute(
            select(NotificationModel).where(NotificationModel.user_id == _CLIENT_ID)
        )
        notif = result.scalar_one()
        assert notif.type == "NOTIFICATION_TYPE_SUBMISSION_RECEIVED"

    @pytest.mark.asyncio
    async def test_resubmission_increments_revision_number(self, db: AsyncSession):
        from src.infra.models import MilestoneModel
        from sqlalchemy import update as sa_update

        with patch("src.domain.submission.enqueue_review"):
            _, milestone_id = await _setup_in_progress_gig(db)
            first = await create_submission(
                db,
                freelancer_id=_FREELANCER_ID,
                milestone_id=milestone_id,
                repo_url="https://github.com/user/repo",
                file_keys=[],
                notes="",
                previous_submission_id=None,
            )

            # Simulate revision request
            await db.execute(
                sa_update(MilestoneModel)
                .where(MilestoneModel.id == milestone_id)
                .values(status="REVISION_REQUESTED")
            )
            await db.flush()

            second = await create_submission(
                db,
                freelancer_id=_FREELANCER_ID,
                milestone_id=milestone_id,
                repo_url="https://github.com/user/repo-v2",
                file_keys=[],
                notes="Fixed",
                previous_submission_id=first.id,
            )

        assert second.revision_number == 2
        assert second.previous_submission_id == first.id

    @pytest.mark.asyncio
    async def test_wrong_freelancer_raises_forbidden(self, db: AsyncSession):
        with patch("src.domain.submission.enqueue_review"):
            _, milestone_id = await _setup_in_progress_gig(db)
            with pytest.raises(SubmissionValidationError) as exc_info:
                await create_submission(
                    db,
                    freelancer_id=_OTHER_FREELANCER_ID,
                    milestone_id=milestone_id,
                    repo_url="https://github.com/user/repo",
                    file_keys=[],
                    notes="",
                    previous_submission_id=None,
                )
        assert exc_info.value.code == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_unknown_milestone_raises_not_found(self, db: AsyncSession):
        with pytest.raises(SubmissionValidationError) as exc_info:
            await create_submission(
                db,
                freelancer_id=_FREELANCER_ID,
                milestone_id="00000000-0000-0000-0000-000000000000",
                repo_url="https://github.com/user/repo",
                file_keys=[],
                notes="",
                previous_submission_id=None,
            )
        assert exc_info.value.code == "MILESTONE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_approved_milestone_raises_not_submittable(self, db: AsyncSession):
        from src.infra.models import MilestoneModel
        from sqlalchemy import update as sa_update

        with patch("src.domain.submission.enqueue_review"):
            _, milestone_id = await _setup_in_progress_gig(db)
            # Force milestone to APPROVED status
            await db.execute(
                sa_update(MilestoneModel)
                .where(MilestoneModel.id == milestone_id)
                .values(status="APPROVED")
            )
            await db.flush()

            with pytest.raises(SubmissionValidationError) as exc_info:
                await create_submission(
                    db,
                    freelancer_id=_FREELANCER_ID,
                    milestone_id=milestone_id,
                    repo_url="https://github.com/user/repo",
                    file_keys=[],
                    notes="",
                    previous_submission_id=None,
                )
        assert exc_info.value.code == "MILESTONE_NOT_SUBMITTABLE"

    @pytest.mark.asyncio
    async def test_no_deliverable_raises_error(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        with pytest.raises(SubmissionValidationError) as exc_info:
            await create_submission(
                db,
                freelancer_id=_FREELANCER_ID,
                milestone_id=milestone_id,
                repo_url=None,
                file_keys=[],
                notes="",
                previous_submission_id=None,
            )
        assert exc_info.value.code == "NO_DELIVERABLE"

    @pytest.mark.asyncio
    async def test_no_assigned_freelancer_raises_error(self, db: AsyncSession):
        gig = await create_gig(db, _CLIENT_ID, _make_gig_input())
        milestone_id = gig.milestones[0].id
        # Gig has no freelancer_id (DRAFT)
        with pytest.raises(SubmissionValidationError) as exc_info:
            await create_submission(
                db,
                freelancer_id=_FREELANCER_ID,
                milestone_id=milestone_id,
                repo_url="https://github.com/user/repo",
                file_keys=[],
                notes="",
                previous_submission_id=None,
            )
        assert exc_info.value.code == "GIG_NOT_IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_resubmission_without_previous_id_raises_error(
        self, db: AsyncSession
    ):
        from src.infra.models import MilestoneModel
        from sqlalchemy import update as sa_update

        with patch("src.domain.submission.enqueue_review"):
            _, milestone_id = await _setup_in_progress_gig(db)
            await create_submission(
                db,
                freelancer_id=_FREELANCER_ID,
                milestone_id=milestone_id,
                repo_url="https://github.com/user/repo",
                file_keys=[],
                notes="",
                previous_submission_id=None,
            )
            await db.execute(
                sa_update(MilestoneModel)
                .where(MilestoneModel.id == milestone_id)
                .values(status="REVISION_REQUESTED")
            )
            await db.flush()

            with pytest.raises(SubmissionValidationError) as exc_info:
                await create_submission(
                    db,
                    freelancer_id=_FREELANCER_ID,
                    milestone_id=milestone_id,
                    repo_url="https://github.com/user/repo",
                    file_keys=[],
                    notes="",
                    previous_submission_id=None,
                )
        assert exc_info.value.code == "PREVIOUS_SUBMISSION_REQUIRED"


# ---------------------------------------------------------------------------
# get_submission / list_submissions
# ---------------------------------------------------------------------------


class TestGetAndListSubmissions:
    @pytest.mark.asyncio
    async def test_get_existing_submission(self, db: AsyncSession):
        with patch("src.domain.submission.enqueue_review"):
            _, milestone_id = await _setup_in_progress_gig(db)
            created = await create_submission(
                db,
                freelancer_id=_FREELANCER_ID,
                milestone_id=milestone_id,
                repo_url="https://github.com/user/repo",
                file_keys=[],
                notes="",
                previous_submission_id=None,
            )
        fetched = await get_submission(db, created.id)
        assert fetched is not None
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_get_unknown_returns_none(self, db: AsyncSession):
        result = await get_submission(db, "00000000-0000-0000-0000-000000000000")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_submissions_returns_in_order(self, db: AsyncSession):
        from src.infra.models import MilestoneModel
        from sqlalchemy import update as sa_update

        with patch("src.domain.submission.enqueue_review"):
            _, milestone_id = await _setup_in_progress_gig(db)
            first = await create_submission(
                db,
                freelancer_id=_FREELANCER_ID,
                milestone_id=milestone_id,
                repo_url="https://github.com/user/repo",
                file_keys=[],
                notes="",
                previous_submission_id=None,
            )
            await db.execute(
                sa_update(MilestoneModel)
                .where(MilestoneModel.id == milestone_id)
                .values(status="REVISION_REQUESTED")
            )
            await db.flush()
            await create_submission(
                db,
                freelancer_id=_FREELANCER_ID,
                milestone_id=milestone_id,
                repo_url="https://github.com/user/repo",
                file_keys=[],
                notes="v2",
                previous_submission_id=first.id,
            )

        submissions = await list_submissions(db, milestone_id)
        assert len(submissions) == 2
        assert submissions[0].revision_number == 1
        assert submissions[1].revision_number == 2
