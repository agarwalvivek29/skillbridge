"""
Unit tests for domain/milestone_approval.py.

Uses SQLite in-memory (aiosqlite) — no Docker dependency.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.gig import CreateGigInput, MilestoneInput, create_gig
from src.domain.milestone_approval import (
    MilestoneApprovalError,
    _encode_complete_milestone_calldata,
    approve_milestone,
    confirm_release,
    get_release_tx,
    request_revision,
)
from src.infra.database import Base
from src.infra.models import (
    EscrowContractModel,
    GigModel,
    MilestoneModel,
    NotificationModel,
)

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_CLIENT_ID = "cccccccc-0000-0000-0000-000000000001"
_FREELANCER_ID = "ffffffff-0000-0000-0000-000000000001"
_OTHER_CLIENT_ID = "cccccccc-0000-0000-0000-000000000002"

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


async def _add_escrow_contract(db: AsyncSession, gig_id: str) -> None:
    """Insert a minimal EscrowContractModel row for gig_id."""
    import uuid

    db.add(
        EscrowContractModel(
            id=str(uuid.uuid4()),
            gig_id=gig_id,
            contract_address="0xABCDEF1234567890AbcdEF1234567890aBcdef12",
        )
    )
    await db.flush()


async def _set_milestone_status(
    db: AsyncSession, milestone_id: str, status: str
) -> None:
    await db.execute(
        sa_update(MilestoneModel)
        .where(MilestoneModel.id == milestone_id)
        .values(status=status)
    )
    await db.flush()


# ---------------------------------------------------------------------------
# _encode_complete_milestone_calldata (pure, no DB)
# ---------------------------------------------------------------------------


class TestEncodeCalldata:
    def test_index_zero(self):
        calldata = _encode_complete_milestone_calldata(0)
        assert calldata.startswith("0x")
        # 4-byte selector + 32-byte index = 36 bytes = 72 hex chars + "0x" prefix
        assert len(calldata) == 2 + 72
        assert calldata[:10] == "0x5a36fb08"
        # index 0 → last 64 hex chars are all zeros
        assert calldata[10:] == "0" * 64

    def test_index_one(self):
        calldata = _encode_complete_milestone_calldata(1)
        assert calldata.startswith("0x5a36fb08")
        # 32-byte big-endian 1 → 63 zeros then '01'
        assert calldata[10:] == "0" * 62 + "01"

    def test_index_large(self):
        calldata = _encode_complete_milestone_calldata(255)
        assert calldata.startswith("0x5a36fb08")
        assert calldata[10:] == "0" * 62 + "ff"


# ---------------------------------------------------------------------------
# approve_milestone
# ---------------------------------------------------------------------------


class TestApproveMilestone:
    @pytest.mark.asyncio
    async def test_approve_under_review(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "UNDER_REVIEW")

        milestone = await approve_milestone(db, milestone_id, _CLIENT_ID)

        assert milestone.status == "APPROVED"

    @pytest.mark.asyncio
    async def test_approve_submitted(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "SUBMITTED")

        milestone = await approve_milestone(db, milestone_id, _CLIENT_ID)

        assert milestone.status == "APPROVED"

    @pytest.mark.asyncio
    async def test_approve_already_approved_is_idempotent(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "APPROVED")

        milestone = await approve_milestone(db, milestone_id, _CLIENT_ID)

        assert milestone.status == "APPROVED"

    @pytest.mark.asyncio
    async def test_approve_creates_notification_for_freelancer(self, db: AsyncSession):
        from sqlalchemy import select

        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "UNDER_REVIEW")

        await approve_milestone(db, milestone_id, _CLIENT_ID)

        result = await db.execute(
            select(NotificationModel).where(NotificationModel.user_id == _FREELANCER_ID)
        )
        notif = result.scalar_one()
        assert notif.type == "NOTIFICATION_TYPE_MILESTONE_APPROVED"

    @pytest.mark.asyncio
    async def test_approve_disputed_raises_409(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "DISPUTED")

        with pytest.raises(MilestoneApprovalError) as exc_info:
            await approve_milestone(db, milestone_id, _CLIENT_ID)

        assert exc_info.value.code == "MILESTONE_DISPUTED"

    @pytest.mark.asyncio
    async def test_approve_wrong_client_raises_forbidden(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "UNDER_REVIEW")

        with pytest.raises(MilestoneApprovalError) as exc_info:
            await approve_milestone(db, milestone_id, _OTHER_CLIENT_ID)

        assert exc_info.value.code == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_approve_pending_milestone_raises_not_approvable(
        self, db: AsyncSession
    ):
        _, milestone_id = await _setup_in_progress_gig(db)
        # Milestone starts as PENDING

        with pytest.raises(MilestoneApprovalError) as exc_info:
            await approve_milestone(db, milestone_id, _CLIENT_ID)

        assert exc_info.value.code == "MILESTONE_NOT_APPROVABLE"

    @pytest.mark.asyncio
    async def test_approve_unknown_milestone_raises_not_found(self, db: AsyncSession):
        with pytest.raises(MilestoneApprovalError) as exc_info:
            await approve_milestone(
                db, "00000000-0000-0000-0000-000000000000", _CLIENT_ID
            )

        assert exc_info.value.code == "MILESTONE_NOT_FOUND"


# ---------------------------------------------------------------------------
# request_revision
# ---------------------------------------------------------------------------


class TestRequestRevision:
    @pytest.mark.asyncio
    async def test_request_revision_under_review(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "UNDER_REVIEW")

        milestone = await request_revision(
            db, milestone_id, _CLIENT_ID, "Needs more tests"
        )

        assert milestone.status == "REVISION_REQUESTED"

    @pytest.mark.asyncio
    async def test_request_revision_submitted(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "SUBMITTED")

        milestone = await request_revision(db, milestone_id, _CLIENT_ID, "Missing docs")

        assert milestone.status == "REVISION_REQUESTED"

    @pytest.mark.asyncio
    async def test_request_revision_creates_notification_with_reason(
        self, db: AsyncSession
    ):
        import json
        from sqlalchemy import select

        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "UNDER_REVIEW")

        await request_revision(db, milestone_id, _CLIENT_ID, "Needs more tests")

        result = await db.execute(
            select(NotificationModel).where(NotificationModel.user_id == _FREELANCER_ID)
        )
        notif = result.scalar_one()
        assert notif.type == "NOTIFICATION_TYPE_REVISION_REQUESTED"
        payload = json.loads(notif.payload_json)
        assert payload["reason"] == "Needs more tests"

    @pytest.mark.asyncio
    async def test_request_revision_pending_raises_not_revisable(
        self, db: AsyncSession
    ):
        _, milestone_id = await _setup_in_progress_gig(db)
        # Milestone starts as PENDING

        with pytest.raises(MilestoneApprovalError) as exc_info:
            await request_revision(db, milestone_id, _CLIENT_ID, "reason")

        assert exc_info.value.code == "MILESTONE_NOT_REVISABLE"

    @pytest.mark.asyncio
    async def test_request_revision_wrong_client_raises_forbidden(
        self, db: AsyncSession
    ):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "UNDER_REVIEW")

        with pytest.raises(MilestoneApprovalError) as exc_info:
            await request_revision(db, milestone_id, _OTHER_CLIENT_ID, "reason")

        assert exc_info.value.code == "FORBIDDEN"


# ---------------------------------------------------------------------------
# get_release_tx
# ---------------------------------------------------------------------------


class TestGetReleaseTx:
    @pytest.mark.asyncio
    async def test_returns_calldata_for_approved_milestone(self, db: AsyncSession):
        gig_id, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "APPROVED")
        # Set a contract address on the gig
        await db.execute(
            sa_update(GigModel)
            .where(GigModel.id == gig_id)
            .values(contract_address="0xABCDEF1234567890AbcdEF1234567890aBcdef12")
        )
        await db.flush()

        result = await get_release_tx(db, milestone_id, _CLIENT_ID)

        assert (
            result["contract_address"] == "0xABCDEF1234567890AbcdEF1234567890aBcdef12"
        )
        assert result["milestone_index"] == 0  # order=1, index=0
        assert result["calldata"].startswith("0x5a36fb08")
        assert len(result["calldata"]) == 2 + 72
        assert isinstance(result["chain_id"], int)

    @pytest.mark.asyncio
    async def test_disputed_raises_409(self, db: AsyncSession):
        gig_id, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "DISPUTED")
        await db.execute(
            sa_update(GigModel)
            .where(GigModel.id == gig_id)
            .values(contract_address="0xABCDEF1234567890AbcdEF1234567890aBcdef12")
        )
        await db.flush()

        with pytest.raises(MilestoneApprovalError) as exc_info:
            await get_release_tx(db, milestone_id, _CLIENT_ID)

        assert exc_info.value.code == "MILESTONE_DISPUTED"

    @pytest.mark.asyncio
    async def test_not_approved_raises_error(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "UNDER_REVIEW")

        with pytest.raises(MilestoneApprovalError) as exc_info:
            await get_release_tx(db, milestone_id, _CLIENT_ID)

        assert exc_info.value.code == "MILESTONE_NOT_APPROVED"

    @pytest.mark.asyncio
    async def test_no_contract_address_raises_error(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "APPROVED")
        # Gig has no contract_address (default is None)

        with pytest.raises(MilestoneApprovalError) as exc_info:
            await get_release_tx(db, milestone_id, _CLIENT_ID)

        assert exc_info.value.code == "NO_CONTRACT_ADDRESS"


# ---------------------------------------------------------------------------
# confirm_release
# ---------------------------------------------------------------------------


class TestConfirmRelease:
    @pytest.mark.asyncio
    async def test_confirm_release_sets_paid(self, db: AsyncSession):
        gig_id, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "APPROVED")
        await _add_escrow_contract(db, gig_id)

        milestone = await confirm_release(db, milestone_id, _CLIENT_ID, "0xdeadbeef")

        assert milestone.status == "PAID"
        assert milestone.release_tx_hash == "0xdeadbeef"

    @pytest.mark.asyncio
    async def test_confirm_release_creates_notification(self, db: AsyncSession):
        import json
        from sqlalchemy import select

        gig_id, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "APPROVED")
        await _add_escrow_contract(db, gig_id)

        await confirm_release(db, milestone_id, _CLIENT_ID, "0xdeadbeef")

        result = await db.execute(
            select(NotificationModel).where(NotificationModel.user_id == _FREELANCER_ID)
        )
        notif = result.scalar_one()
        assert notif.type == "NOTIFICATION_TYPE_FUNDS_RELEASED"
        payload = json.loads(notif.payload_json)
        assert payload["tx_hash"] == "0xdeadbeef"

    @pytest.mark.asyncio
    async def test_confirm_release_not_approved_raises_error(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "UNDER_REVIEW")

        with pytest.raises(MilestoneApprovalError) as exc_info:
            await confirm_release(db, milestone_id, _CLIENT_ID, "0xdeadbeef")

        assert exc_info.value.code == "MILESTONE_NOT_APPROVED"

    @pytest.mark.asyncio
    async def test_confirm_release_no_escrow_contract_raises_error(
        self, db: AsyncSession
    ):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "APPROVED")
        # No EscrowContractModel inserted

        with pytest.raises(MilestoneApprovalError) as exc_info:
            await confirm_release(db, milestone_id, _CLIENT_ID, "0xdeadbeef")

        assert exc_info.value.code == "NO_CONTRACT_ADDRESS"

    @pytest.mark.asyncio
    async def test_confirm_release_wrong_client_raises_forbidden(
        self, db: AsyncSession
    ):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "APPROVED")

        with pytest.raises(MilestoneApprovalError) as exc_info:
            await confirm_release(db, milestone_id, _OTHER_CLIENT_ID, "0xdeadbeef")

        assert exc_info.value.code == "FORBIDDEN"
