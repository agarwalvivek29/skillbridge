"""
Unit tests for domain/proposal.py.

Uses SQLite in-memory (aiosqlite) — no Docker dependency.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.gig import CreateGigInput, MilestoneInput, create_gig
from src.domain.proposal import (
    CreateProposalInput,
    ProposalError,
    accept_proposal,
    create_proposal,
    get_my_proposal,
    list_proposals,
    reject_proposal,
    withdraw_proposal,
)
from src.infra.database import Base
from src.infra.models import GigModel, NotificationModel

_TEST_CLIENT_ID = "aaaaaaaa-0000-0000-0000-000000000001"
_TEST_FREELANCER_ID = "bbbbbbbb-0000-0000-0000-000000000001"
_TEST_FREELANCER_ID_2 = "bbbbbbbb-0000-0000-0000-000000000002"
_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

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


def _make_milestones(total: int = 1000) -> list[MilestoneInput]:
    return [
        MilestoneInput(
            title="Milestone 1",
            description="Do the thing",
            acceptance_criteria="## Criteria\n- It works",
            amount=str(total),
            order=1,
        )
    ]


async def _create_open_gig(
    db: AsyncSession, client_id: str = _TEST_CLIENT_ID
) -> GigModel:
    """Create a gig and set it to OPEN status."""
    gig = await create_gig(
        db,
        client_id,
        CreateGigInput(
            title="Build a widget",
            description="Full description",
            total_amount="1000",
            currency="SOL",
            token_address=None,
            tags=[],
            required_skills=["Python"],
            deadline=None,
            milestones=_make_milestones(1000),
        ),
    )
    await db.execute(
        sa_update(GigModel).where(GigModel.id == gig.id).values(status="OPEN")
    )
    await db.flush()
    return gig


def _proposal_input(gig_id: str) -> CreateProposalInput:
    return CreateProposalInput(
        gig_id=gig_id,
        cover_letter="I am the best freelancer for this.",
        estimated_days=7,
    )


# ---------------------------------------------------------------------------
# create_proposal
# ---------------------------------------------------------------------------


class TestCreateProposal:
    @pytest.mark.asyncio
    async def test_happy_path_creates_pending_proposal(self, db: AsyncSession):
        gig = await _create_open_gig(db)
        proposal = await create_proposal(
            db, _TEST_FREELANCER_ID, _proposal_input(gig.id)
        )
        assert proposal.id is not None
        assert proposal.status == "PENDING"
        assert proposal.gig_id == gig.id
        assert proposal.freelancer_id == _TEST_FREELANCER_ID

    @pytest.mark.asyncio
    async def test_creates_notification_for_client(self, db: AsyncSession):
        from sqlalchemy import select

        gig = await _create_open_gig(db)
        await create_proposal(db, _TEST_FREELANCER_ID, _proposal_input(gig.id))

        result = await db.execute(
            select(NotificationModel).where(
                NotificationModel.user_id == _TEST_CLIENT_ID,
                NotificationModel.type == "NOTIFICATION_TYPE_PROPOSAL_RECEIVED",
            )
        )
        notif = result.scalar_one_or_none()
        assert notif is not None

    @pytest.mark.asyncio
    async def test_gig_not_found_raises_error(self, db: AsyncSession):
        with pytest.raises(ProposalError) as exc_info:
            await create_proposal(
                db,
                _TEST_FREELANCER_ID,
                CreateProposalInput(
                    gig_id="00000000-0000-0000-0000-000000000000",
                    cover_letter="Hello",
                    estimated_days=5,
                ),
            )
        assert exc_info.value.code == "GIG_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_draft_gig_raises_error(self, db: AsyncSession):
        gig = await create_gig(
            db,
            _TEST_CLIENT_ID,
            CreateGigInput(
                title="Draft gig",
                description="desc",
                total_amount="1000",
                currency="SOL",
                token_address=None,
                tags=[],
                required_skills=[],
                deadline=None,
                milestones=_make_milestones(1000),
            ),
        )
        with pytest.raises(ProposalError) as exc_info:
            await create_proposal(db, _TEST_FREELANCER_ID, _proposal_input(gig.id))
        assert exc_info.value.code == "GIG_NOT_OPEN"

    @pytest.mark.asyncio
    async def test_duplicate_proposal_raises_error(self, db: AsyncSession):
        gig = await _create_open_gig(db)
        await create_proposal(db, _TEST_FREELANCER_ID, _proposal_input(gig.id))
        with pytest.raises(ProposalError) as exc_info:
            await create_proposal(db, _TEST_FREELANCER_ID, _proposal_input(gig.id))
        assert exc_info.value.code == "DUPLICATE_PROPOSAL"

    @pytest.mark.asyncio
    async def test_invalid_estimated_days_raises_error(self, db: AsyncSession):
        gig = await _create_open_gig(db)
        with pytest.raises(ProposalError) as exc_info:
            await create_proposal(
                db,
                _TEST_FREELANCER_ID,
                CreateProposalInput(
                    gig_id=gig.id,
                    cover_letter="Hello",
                    estimated_days=0,
                ),
            )
        assert exc_info.value.code == "INVALID_ESTIMATED_DAYS"


# ---------------------------------------------------------------------------
# list_proposals
# ---------------------------------------------------------------------------


class TestListProposals:
    @pytest.mark.asyncio
    async def test_returns_proposals_for_gig(self, db: AsyncSession):
        gig = await _create_open_gig(db)
        await create_proposal(db, _TEST_FREELANCER_ID, _proposal_input(gig.id))
        proposals, total = await list_proposals(db, gig.id, _TEST_CLIENT_ID)
        assert total == 1
        assert proposals[0].freelancer_id == _TEST_FREELANCER_ID

    @pytest.mark.asyncio
    async def test_forbidden_for_non_owner(self, db: AsyncSession):
        other_client = "cccccccc-0000-0000-0000-000000000001"
        gig = await _create_open_gig(db)
        with pytest.raises(ProposalError) as exc_info:
            await list_proposals(db, gig.id, other_client)
        assert exc_info.value.code == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_gig_not_found_raises_error(self, db: AsyncSession):
        with pytest.raises(ProposalError) as exc_info:
            await list_proposals(
                db, "00000000-0000-0000-0000-000000000000", _TEST_CLIENT_ID
            )
        assert exc_info.value.code == "GIG_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_pagination(self, db: AsyncSession):
        gig = await _create_open_gig(db)
        await create_proposal(db, _TEST_FREELANCER_ID, _proposal_input(gig.id))
        await create_proposal(db, _TEST_FREELANCER_ID_2, _proposal_input(gig.id))

        page1, total = await list_proposals(
            db, gig.id, _TEST_CLIENT_ID, page=1, page_size=1
        )
        assert total == 2
        assert len(page1) == 1

        page2, _ = await list_proposals(
            db, gig.id, _TEST_CLIENT_ID, page=2, page_size=1
        )
        assert len(page2) == 1
        assert page1[0].id != page2[0].id


# ---------------------------------------------------------------------------
# accept_proposal
# ---------------------------------------------------------------------------


class TestAcceptProposal:
    @pytest.mark.asyncio
    async def test_accept_sets_gig_in_progress(self, db: AsyncSession):
        from sqlalchemy import select

        gig = await _create_open_gig(db)
        proposal = await create_proposal(
            db, _TEST_FREELANCER_ID, _proposal_input(gig.id)
        )

        accepted = await accept_proposal(db, proposal.id, _TEST_CLIENT_ID)
        assert accepted.status == "ACCEPTED"

        gig_result = await db.execute(select(GigModel).where(GigModel.id == gig.id))
        updated_gig = gig_result.scalar_one()
        assert updated_gig.status == "IN_PROGRESS"
        assert updated_gig.freelancer_id == _TEST_FREELANCER_ID

    @pytest.mark.asyncio
    async def test_accept_rejects_other_proposals(self, db: AsyncSession):
        from sqlalchemy import select
        from src.infra.models import ProposalModel

        gig = await _create_open_gig(db)
        p1 = await create_proposal(db, _TEST_FREELANCER_ID, _proposal_input(gig.id))
        p2 = await create_proposal(db, _TEST_FREELANCER_ID_2, _proposal_input(gig.id))

        await accept_proposal(db, p1.id, _TEST_CLIENT_ID)

        p2_result = await db.execute(
            select(ProposalModel).where(ProposalModel.id == p2.id)
        )
        p2_updated = p2_result.scalar_one()
        assert p2_updated.status == "REJECTED"

    @pytest.mark.asyncio
    async def test_accept_creates_notifications(self, db: AsyncSession):
        from sqlalchemy import select

        gig = await _create_open_gig(db)
        p1 = await create_proposal(db, _TEST_FREELANCER_ID, _proposal_input(gig.id))
        await create_proposal(db, _TEST_FREELANCER_ID_2, _proposal_input(gig.id))

        await accept_proposal(db, p1.id, _TEST_CLIENT_ID)

        accepted_notif = await db.execute(
            select(NotificationModel).where(
                NotificationModel.user_id == _TEST_FREELANCER_ID,
                NotificationModel.type == "NOTIFICATION_TYPE_PROPOSAL_ACCEPTED",
            )
        )
        assert accepted_notif.scalar_one_or_none() is not None

        rejected_notif = await db.execute(
            select(NotificationModel).where(
                NotificationModel.user_id == _TEST_FREELANCER_ID_2,
                NotificationModel.type == "NOTIFICATION_TYPE_PROPOSAL_REJECTED",
            )
        )
        assert rejected_notif.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_forbidden_for_non_owner(self, db: AsyncSession):
        other_client = "cccccccc-0000-0000-0000-000000000001"
        gig = await _create_open_gig(db)
        proposal = await create_proposal(
            db, _TEST_FREELANCER_ID, _proposal_input(gig.id)
        )
        with pytest.raises(ProposalError) as exc_info:
            await accept_proposal(db, proposal.id, other_client)
        assert exc_info.value.code == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_proposal_not_found_raises_error(self, db: AsyncSession):
        with pytest.raises(ProposalError) as exc_info:
            await accept_proposal(
                db, "00000000-0000-0000-0000-000000000000", _TEST_CLIENT_ID
            )
        assert exc_info.value.code == "PROPOSAL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_already_accepted_proposal_raises_error(self, db: AsyncSession):
        gig = await _create_open_gig(db)
        proposal = await create_proposal(
            db, _TEST_FREELANCER_ID, _proposal_input(gig.id)
        )
        await accept_proposal(db, proposal.id, _TEST_CLIENT_ID)

        with pytest.raises(ProposalError) as exc_info:
            await accept_proposal(db, proposal.id, _TEST_CLIENT_ID)
        assert exc_info.value.code in ("GIG_NOT_OPEN", "PROPOSAL_NOT_PENDING")


# ---------------------------------------------------------------------------
# withdraw_proposal
# ---------------------------------------------------------------------------


class TestWithdrawProposal:
    @pytest.mark.asyncio
    async def test_withdraw_sets_status_withdrawn(self, db: AsyncSession):
        gig = await _create_open_gig(db)
        proposal = await create_proposal(
            db, _TEST_FREELANCER_ID, _proposal_input(gig.id)
        )

        withdrawn = await withdraw_proposal(db, proposal.id, _TEST_FREELANCER_ID)
        assert withdrawn.status == "WITHDRAWN"

    @pytest.mark.asyncio
    async def test_forbidden_for_non_owner(self, db: AsyncSession):
        gig = await _create_open_gig(db)
        proposal = await create_proposal(
            db, _TEST_FREELANCER_ID, _proposal_input(gig.id)
        )
        with pytest.raises(ProposalError) as exc_info:
            await withdraw_proposal(db, proposal.id, _TEST_FREELANCER_ID_2)
        assert exc_info.value.code == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_proposal_not_found_raises_error(self, db: AsyncSession):
        with pytest.raises(ProposalError) as exc_info:
            await withdraw_proposal(
                db, "00000000-0000-0000-0000-000000000000", _TEST_FREELANCER_ID
            )
        assert exc_info.value.code == "PROPOSAL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_cannot_withdraw_non_pending_proposal(self, db: AsyncSession):
        gig = await _create_open_gig(db)
        proposal = await create_proposal(
            db, _TEST_FREELANCER_ID, _proposal_input(gig.id)
        )
        await accept_proposal(db, proposal.id, _TEST_CLIENT_ID)

        with pytest.raises(ProposalError) as exc_info:
            await withdraw_proposal(db, proposal.id, _TEST_FREELANCER_ID)
        assert exc_info.value.code == "PROPOSAL_NOT_PENDING"


# ---------------------------------------------------------------------------
# reject_proposal
# ---------------------------------------------------------------------------


class TestRejectProposal:
    @pytest.mark.asyncio
    async def test_reject_sets_status_rejected(self, db: AsyncSession):
        gig = await _create_open_gig(db)
        proposal = await create_proposal(
            db, _TEST_FREELANCER_ID, _proposal_input(gig.id)
        )

        rejected = await reject_proposal(db, proposal.id, _TEST_CLIENT_ID)
        assert rejected.status == "REJECTED"

    @pytest.mark.asyncio
    async def test_reject_creates_notification(self, db: AsyncSession):
        from sqlalchemy import select

        gig = await _create_open_gig(db)
        proposal = await create_proposal(
            db, _TEST_FREELANCER_ID, _proposal_input(gig.id)
        )

        await reject_proposal(db, proposal.id, _TEST_CLIENT_ID)

        result = await db.execute(
            select(NotificationModel).where(
                NotificationModel.user_id == _TEST_FREELANCER_ID,
                NotificationModel.type == "NOTIFICATION_TYPE_PROPOSAL_REJECTED",
            )
        )
        notif = result.scalar_one_or_none()
        assert notif is not None

    @pytest.mark.asyncio
    async def test_forbidden_for_non_owner(self, db: AsyncSession):
        other_client = "cccccccc-0000-0000-0000-000000000001"
        gig = await _create_open_gig(db)
        proposal = await create_proposal(
            db, _TEST_FREELANCER_ID, _proposal_input(gig.id)
        )
        with pytest.raises(ProposalError) as exc_info:
            await reject_proposal(db, proposal.id, other_client)
        assert exc_info.value.code == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_proposal_not_found_raises_error(self, db: AsyncSession):
        with pytest.raises(ProposalError) as exc_info:
            await reject_proposal(
                db, "00000000-0000-0000-0000-000000000000", _TEST_CLIENT_ID
            )
        assert exc_info.value.code == "PROPOSAL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_cannot_reject_non_pending_proposal(self, db: AsyncSession):
        gig = await _create_open_gig(db)
        proposal = await create_proposal(
            db, _TEST_FREELANCER_ID, _proposal_input(gig.id)
        )
        await accept_proposal(db, proposal.id, _TEST_CLIENT_ID)

        with pytest.raises(ProposalError) as exc_info:
            await reject_proposal(db, proposal.id, _TEST_CLIENT_ID)
        assert exc_info.value.code == "PROPOSAL_NOT_PENDING"


# ---------------------------------------------------------------------------
# get_my_proposal
# ---------------------------------------------------------------------------


class TestGetMyProposal:
    @pytest.mark.asyncio
    async def test_returns_proposal_when_exists(self, db: AsyncSession):
        gig = await _create_open_gig(db)
        created = await create_proposal(
            db, _TEST_FREELANCER_ID, _proposal_input(gig.id)
        )

        result = await get_my_proposal(db, gig.id, _TEST_FREELANCER_ID)
        assert result is not None
        assert result.id == created.id

    @pytest.mark.asyncio
    async def test_returns_none_when_no_proposal(self, db: AsyncSession):
        gig = await _create_open_gig(db)
        result = await get_my_proposal(db, gig.id, _TEST_FREELANCER_ID)
        assert result is None
