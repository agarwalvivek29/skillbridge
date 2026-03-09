"""
Unit tests for domain/dispute.py.

Uses SQLite in-memory (aiosqlite) — no Docker dependency.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.dispute import (
    DisputeError,
    escalate_open_disputes,
    generate_ai_evidence,
    get_dispute,
    get_dispute_by_milestone,
    post_dispute_message,
    raise_dispute,
    resolve_dispute,
)
from src.domain.gig import CreateGigInput, MilestoneInput, create_gig
from src.infra.database import Base
from src.infra.models import (
    DisputeModel,
    GigModel,
    MilestoneModel,
    NotificationModel,
    ReviewReportModel,
    SubmissionModel,
)

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_CLIENT_ID = "cccccccc-0000-0000-0000-000000000001"
_FREELANCER_ID = "ffffffff-0000-0000-0000-000000000001"
_ADMIN_ID = "aaaaaaaa-0000-0000-0000-000000000001"
_OTHER_USER_ID = "00000000-0000-0000-0000-999999999999"

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
                acceptance_criteria="## Tests pass\nAll unit tests green.",
                amount="1000",
                order=1,
            )
        ],
    )


async def _setup_in_progress_gig(db: AsyncSession) -> tuple[str, str]:
    """Create a gig with freelancer assigned. Returns (gig_id, milestone_id)."""
    gig = await create_gig(db, _CLIENT_ID, _make_gig_input())
    await db.execute(
        sa_update(GigModel)
        .where(GigModel.id == gig.id)
        .values(status="IN_PROGRESS", freelancer_id=_FREELANCER_ID)
    )
    await db.flush()
    milestone_id = gig.milestones[0].id
    return gig.id, milestone_id


async def _set_milestone_status(
    db: AsyncSession, milestone_id: str, status: str
) -> None:
    await db.execute(
        sa_update(MilestoneModel)
        .where(MilestoneModel.id == milestone_id)
        .values(status=status)
    )
    await db.flush()


async def _create_dispute(
    db: AsyncSession, milestone_id: str, user_id: str = _CLIENT_ID
) -> DisputeModel:
    """Helper: set milestone to SUBMITTED and raise dispute."""
    await _set_milestone_status(db, milestone_id, "SUBMITTED")
    return await raise_dispute(db, user_id, milestone_id, "Work is incomplete")


# ---------------------------------------------------------------------------
# raise_dispute
# ---------------------------------------------------------------------------


class TestRaiseDispute:
    @pytest.mark.asyncio
    async def test_raise_dispute_by_client(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "SUBMITTED")

        dispute = await raise_dispute(
            db, _CLIENT_ID, milestone_id, "Work is incomplete"
        )

        assert dispute.status == "OPEN"
        assert dispute.raised_by_user_id == _CLIENT_ID
        assert dispute.milestone_id == milestone_id
        assert dispute.reason == "Work is incomplete"
        assert dispute.discussion_deadline is not None

    @pytest.mark.asyncio
    async def test_raise_dispute_by_freelancer(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "UNDER_REVIEW")

        dispute = await raise_dispute(
            db, _FREELANCER_ID, milestone_id, "Client not responding"
        )

        assert dispute.status == "OPEN"
        assert dispute.raised_by_user_id == _FREELANCER_ID

    @pytest.mark.asyncio
    async def test_raise_dispute_sets_milestone_disputed(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "SUBMITTED")

        await raise_dispute(db, _CLIENT_ID, milestone_id, "Incomplete")

        result = await db.execute(
            select(MilestoneModel).where(MilestoneModel.id == milestone_id)
        )
        milestone = result.scalar_one()
        assert milestone.status == "DISPUTED"

    @pytest.mark.asyncio
    async def test_raise_dispute_creates_notifications(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "SUBMITTED")

        await raise_dispute(db, _CLIENT_ID, milestone_id, "Incomplete")

        result = await db.execute(
            select(NotificationModel).where(
                NotificationModel.type == "NOTIFICATION_TYPE_DISPUTE_RAISED"
            )
        )
        notifications = list(result.scalars().all())
        # Both client and freelancer should be notified
        assert len(notifications) == 2
        notified_users = {n.user_id for n in notifications}
        assert _CLIENT_ID in notified_users
        assert _FREELANCER_ID in notified_users

    @pytest.mark.asyncio
    async def test_raise_dispute_pending_milestone_fails(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        # milestone starts as PENDING

        with pytest.raises(DisputeError) as exc_info:
            await raise_dispute(db, _CLIENT_ID, milestone_id, "Incomplete")

        assert exc_info.value.code == "MILESTONE_NOT_DISPUTABLE"

    @pytest.mark.asyncio
    async def test_raise_dispute_duplicate_fails(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "SUBMITTED")

        await raise_dispute(db, _CLIENT_ID, milestone_id, "First dispute")

        # Second dispute on same milestone should fail — milestone is now DISPUTED,
        # so it fails the status check before reaching the duplicate check
        with pytest.raises(DisputeError) as exc_info:
            await raise_dispute(db, _FREELANCER_ID, milestone_id, "Second dispute")

        assert exc_info.value.code == "MILESTONE_NOT_DISPUTABLE"

    @pytest.mark.asyncio
    async def test_raise_dispute_unauthorized_user_fails(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "SUBMITTED")

        with pytest.raises(DisputeError) as exc_info:
            await raise_dispute(db, _OTHER_USER_ID, milestone_id, "Dispute")

        assert exc_info.value.code == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_raise_dispute_unknown_milestone_fails(self, db: AsyncSession):
        with pytest.raises(DisputeError) as exc_info:
            await raise_dispute(
                db, _CLIENT_ID, "00000000-0000-0000-0000-000000000000", "Dispute"
            )

        assert exc_info.value.code == "MILESTONE_NOT_FOUND"


# ---------------------------------------------------------------------------
# get_dispute / get_dispute_by_milestone
# ---------------------------------------------------------------------------


class TestGetDispute:
    @pytest.mark.asyncio
    async def test_get_dispute(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        created = await _create_dispute(db, milestone_id)

        dispute = await get_dispute(db, created.id)

        assert dispute is not None
        assert dispute.id == created.id
        assert isinstance(dispute.messages, list)

    @pytest.mark.asyncio
    async def test_get_dispute_not_found(self, db: AsyncSession):
        dispute = await get_dispute(db, "00000000-0000-0000-0000-000000000000")
        assert dispute is None

    @pytest.mark.asyncio
    async def test_get_dispute_by_milestone(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        created = await _create_dispute(db, milestone_id)

        dispute = await get_dispute_by_milestone(db, milestone_id)

        assert dispute is not None
        assert dispute.id == created.id

    @pytest.mark.asyncio
    async def test_get_dispute_by_milestone_no_dispute(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)

        dispute = await get_dispute_by_milestone(db, milestone_id)

        assert dispute is None


# ---------------------------------------------------------------------------
# post_dispute_message
# ---------------------------------------------------------------------------


class TestPostDisputeMessage:
    @pytest.mark.asyncio
    async def test_post_message(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        msg = await post_dispute_message(
            db, _CLIENT_ID, dispute.id, "I disagree with the delivery"
        )

        assert msg.dispute_id == dispute.id
        assert msg.user_id == _CLIENT_ID
        assert msg.content == "I disagree with the delivery"

    @pytest.mark.asyncio
    async def test_post_message_by_freelancer(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        msg = await post_dispute_message(
            db, _FREELANCER_ID, dispute.id, "I completed the work"
        )

        assert msg.user_id == _FREELANCER_ID

    @pytest.mark.asyncio
    async def test_post_message_not_open_fails(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        # Manually set to ARBITRATION
        await db.execute(
            sa_update(DisputeModel)
            .where(DisputeModel.id == dispute.id)
            .values(status="ARBITRATION")
        )
        await db.flush()

        with pytest.raises(DisputeError) as exc_info:
            await post_dispute_message(db, _CLIENT_ID, dispute.id, "Message")

        assert exc_info.value.code == "DISPUTE_NOT_OPEN"

    @pytest.mark.asyncio
    async def test_post_message_past_deadline_fails(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        # Set deadline to past
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.execute(
            sa_update(DisputeModel)
            .where(DisputeModel.id == dispute.id)
            .values(discussion_deadline=past)
        )
        await db.flush()

        with pytest.raises(DisputeError) as exc_info:
            await post_dispute_message(db, _CLIENT_ID, dispute.id, "Late message")

        assert exc_info.value.code == "DISCUSSION_DEADLINE_PASSED"

    @pytest.mark.asyncio
    async def test_post_message_unauthorized_user_fails(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        with pytest.raises(DisputeError) as exc_info:
            await post_dispute_message(db, _OTHER_USER_ID, dispute.id, "Message")

        assert exc_info.value.code == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_post_message_dispute_not_found_fails(self, db: AsyncSession):
        with pytest.raises(DisputeError) as exc_info:
            await post_dispute_message(
                db, _CLIENT_ID, "00000000-0000-0000-0000-000000000000", "Message"
            )

        assert exc_info.value.code == "DISPUTE_NOT_FOUND"


# ---------------------------------------------------------------------------
# resolve_dispute
# ---------------------------------------------------------------------------


class TestResolveDispute:
    @pytest.mark.asyncio
    async def test_resolve_pay_freelancer(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        resolved = await resolve_dispute(
            db,
            dispute.id,
            "DISPUTE_RESOLUTION_PAY_FREELANCER",
            None,
            "0xabc123",
        )

        assert resolved.status == "RESOLVED"
        assert resolved.resolution == "DISPUTE_RESOLUTION_PAY_FREELANCER"
        assert resolved.resolution_tx_hash == "0xabc123"
        assert resolved.resolved_at is not None

    @pytest.mark.asyncio
    async def test_resolve_refund_client(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        resolved = await resolve_dispute(
            db,
            dispute.id,
            "DISPUTE_RESOLUTION_REFUND_CLIENT",
            None,
            "0xdef456",
        )

        assert resolved.status == "RESOLVED"
        assert resolved.resolution == "DISPUTE_RESOLUTION_REFUND_CLIENT"

    @pytest.mark.asyncio
    async def test_resolve_split(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        resolved = await resolve_dispute(
            db,
            dispute.id,
            "DISPUTE_RESOLUTION_SPLIT",
            "500",
            "0x789",
        )

        assert resolved.status == "RESOLVED"
        assert resolved.resolution == "DISPUTE_RESOLUTION_SPLIT"
        assert resolved.freelancer_split_amount == "500"

    @pytest.mark.asyncio
    async def test_resolve_sets_milestone_resolved(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        await resolve_dispute(
            db,
            dispute.id,
            "DISPUTE_RESOLUTION_PAY_FREELANCER",
            None,
            "0xabc",
        )

        result = await db.execute(
            select(MilestoneModel).where(MilestoneModel.id == milestone_id)
        )
        milestone = result.scalar_one()
        assert milestone.status == "RESOLVED"

    @pytest.mark.asyncio
    async def test_resolve_creates_notifications(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        await resolve_dispute(
            db,
            dispute.id,
            "DISPUTE_RESOLUTION_PAY_FREELANCER",
            None,
            "0xabc",
        )

        result = await db.execute(
            select(NotificationModel).where(
                NotificationModel.type == "NOTIFICATION_TYPE_DISPUTE_RESOLVED"
            )
        )
        notifications = list(result.scalars().all())
        assert len(notifications) == 2

    @pytest.mark.asyncio
    async def test_resolve_already_resolved_fails(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        await resolve_dispute(
            db,
            dispute.id,
            "DISPUTE_RESOLUTION_PAY_FREELANCER",
            None,
            "0xabc",
        )

        with pytest.raises(DisputeError) as exc_info:
            await resolve_dispute(
                db,
                dispute.id,
                "DISPUTE_RESOLUTION_PAY_FREELANCER",
                None,
                "0xabc2",
            )

        assert exc_info.value.code == "DISPUTE_NOT_RESOLVABLE"

    @pytest.mark.asyncio
    async def test_resolve_invalid_resolution_fails(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        with pytest.raises(DisputeError) as exc_info:
            await resolve_dispute(
                db,
                dispute.id,
                "INVALID_VALUE",
                None,
                "0xabc",
            )

        assert exc_info.value.code == "INVALID_RESOLUTION"

    @pytest.mark.asyncio
    async def test_resolve_split_without_amount_fails(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        with pytest.raises(DisputeError) as exc_info:
            await resolve_dispute(
                db,
                dispute.id,
                "DISPUTE_RESOLUTION_SPLIT",
                None,
                "0xabc",
            )

        assert exc_info.value.code == "SPLIT_AMOUNT_REQUIRED"

    @pytest.mark.asyncio
    async def test_resolve_from_arbitration_status(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        # Set to ARBITRATION
        await db.execute(
            sa_update(DisputeModel)
            .where(DisputeModel.id == dispute.id)
            .values(status="ARBITRATION")
        )
        await db.flush()

        resolved = await resolve_dispute(
            db,
            dispute.id,
            "DISPUTE_RESOLUTION_PAY_FREELANCER",
            None,
            "0xabc",
        )

        assert resolved.status == "RESOLVED"


# ---------------------------------------------------------------------------
# escalate_open_disputes
# ---------------------------------------------------------------------------


class TestEscalateOpenDisputes:
    @pytest.mark.asyncio
    async def test_escalate_past_deadline(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        # Set deadline to past
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.execute(
            sa_update(DisputeModel)
            .where(DisputeModel.id == dispute.id)
            .values(discussion_deadline=past)
        )
        await db.flush()

        count = await escalate_open_disputes(db)

        assert count == 1

        result = await db.execute(
            select(DisputeModel).where(DisputeModel.id == dispute.id)
        )
        updated = result.scalar_one()
        assert updated.status == "ARBITRATION"

    @pytest.mark.asyncio
    async def test_no_escalation_before_deadline(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _create_dispute(db, milestone_id)
        # Default deadline is 3 days in the future

        count = await escalate_open_disputes(db)

        assert count == 0

    @pytest.mark.asyncio
    async def test_no_escalation_for_non_open(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.execute(
            sa_update(DisputeModel)
            .where(DisputeModel.id == dispute.id)
            .values(status="RESOLVED", discussion_deadline=past)
        )
        await db.flush()

        count = await escalate_open_disputes(db)

        assert count == 0


# ---------------------------------------------------------------------------
# generate_ai_evidence
# ---------------------------------------------------------------------------


class TestGenerateAiEvidence:
    @pytest.mark.asyncio
    async def test_copies_review_report_body(self, db: AsyncSession):
        gig_id, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        # Create a submission with repo_url
        submission = SubmissionModel(
            milestone_id=milestone_id,
            freelancer_id=_FREELANCER_ID,
            repo_url="https://github.com/owner/repo/pull/1",
            notes="PR ready",
            status="UNDER_REVIEW",
            revision_number=1,
        )
        db.add(submission)
        await db.flush()

        # Create a ReviewReport
        report = ReviewReportModel(
            submission_id=submission.id,
            verdict="FAIL",
            score=0,
            body="The code does not meet acceptance criteria. Missing tests.",
            model_version="openreview",
        )
        db.add(report)
        await db.flush()

        await generate_ai_evidence(db, dispute.id)

        result = await db.execute(
            select(DisputeModel).where(DisputeModel.id == dispute.id)
        )
        updated = result.scalar_one()
        assert updated.ai_evidence_summary == report.body

    @pytest.mark.asyncio
    async def test_no_submissions_sets_fallback(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        await generate_ai_evidence(db, dispute.id)

        result = await db.execute(
            select(DisputeModel).where(DisputeModel.id == dispute.id)
        )
        updated = result.scalar_one()
        assert "No submissions found" in updated.ai_evidence_summary

    @pytest.mark.asyncio
    async def test_file_only_no_api_key_sets_fallback(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        dispute = await _create_dispute(db, milestone_id)

        # Create a file-only submission (no repo_url)
        submission = SubmissionModel(
            milestone_id=milestone_id,
            freelancer_id=_FREELANCER_ID,
            file_keys=["submissions/file1.zip"],
            notes="Files uploaded",
            status="UNDER_REVIEW",
            revision_number=1,
        )
        db.add(submission)
        await db.flush()

        await generate_ai_evidence(db, dispute.id)

        result = await db.execute(
            select(DisputeModel).where(DisputeModel.id == dispute.id)
        )
        updated = result.scalar_one()
        assert updated.ai_evidence_summary is not None
        # Without ANTHROPIC_API_KEY, should get the "unavailable" fallback
        assert (
            "unavailable" in updated.ai_evidence_summary.lower()
            or "failed" in updated.ai_evidence_summary.lower()
        )
