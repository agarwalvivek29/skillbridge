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
    _b58decode,
    _b58encode,
    approve_milestone,
    build_release_instruction_data,
    confirm_release,
    derive_escrow_pda,
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
# Base58 helpers and PDA derivation (pure, no DB)
# ---------------------------------------------------------------------------

# A known base58-encoded Solana program ID for testing
_TEST_PROGRAM_ID = "11111111111111111111111111111111"


class TestBase58:
    def test_roundtrip(self):
        original = b"\x00\x01\x02\x03\xff"
        encoded = _b58encode(original)
        decoded = _b58decode(encoded)
        assert decoded == original

    def test_known_value(self):
        # System program: all zeros (32 bytes) encodes to 32 '1' chars
        decoded = _b58decode(_TEST_PROGRAM_ID)
        assert decoded == b"\x00" * 32


class TestDeriveEscrowPda:
    def test_returns_base58_string(self):
        pda = derive_escrow_pda("gig-123", _TEST_PROGRAM_ID)
        assert isinstance(pda, str)
        assert len(pda) > 0
        # Must be valid base58 (roundtrip)
        decoded = _b58decode(pda)
        assert len(decoded) == 32  # Solana public key is 32 bytes

    def test_deterministic(self):
        pda1 = derive_escrow_pda("gig-abc", _TEST_PROGRAM_ID)
        pda2 = derive_escrow_pda("gig-abc", _TEST_PROGRAM_ID)
        assert pda1 == pda2

    def test_different_gig_ids_produce_different_pdas(self):
        pda1 = derive_escrow_pda("gig-aaa", _TEST_PROGRAM_ID)
        pda2 = derive_escrow_pda("gig-bbb", _TEST_PROGRAM_ID)
        assert pda1 != pda2


class TestBuildReleaseInstructionData:
    def test_basic_structure(self):
        result = build_release_instruction_data(
            gig_id="gig-1",
            milestone_index=0,
            freelancer_wallet="FrEeLaNcErPubKey1111111111111111111111111111",
            program_id=_TEST_PROGRAM_ID,
        )
        assert result["program_id"] == _TEST_PROGRAM_ID
        assert result["milestone_index"] == 0
        assert isinstance(result["escrow_pda"], str)
        assert isinstance(result["accounts"], list)
        # escrow_pda + freelancer + system_program = 3 accounts
        assert len(result["accounts"]) == 3

    def test_no_freelancer_wallet(self):
        result = build_release_instruction_data(
            gig_id="gig-2",
            milestone_index=1,
            freelancer_wallet=None,
            program_id=_TEST_PROGRAM_ID,
        )
        # escrow_pda + system_program = 2 accounts (no freelancer)
        assert len(result["accounts"]) == 2

    def test_escrow_pda_is_first_account(self):
        result = build_release_instruction_data(
            gig_id="gig-3",
            milestone_index=0,
            freelancer_wallet="SomeWallet111111111111111111111111111111111",
            program_id=_TEST_PROGRAM_ID,
        )
        assert result["accounts"][0]["pubkey"] == result["escrow_pda"]
        assert result["accounts"][0]["is_writable"] is True


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
    async def test_returns_solana_instruction_data_for_approved_milestone(
        self, db: AsyncSession, monkeypatch
    ):
        gig_id, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "APPROVED")
        # Set a contract address on the gig (Solana base58 pubkey)
        await db.execute(
            sa_update(GigModel)
            .where(GigModel.id == gig_id)
            .values(contract_address="FrEeLaNcErPubKey1111111111111111111111111111")
        )
        await db.flush()

        # Patch settings for Solana config
        from src.config import settings

        monkeypatch.setattr(settings, "escrow_program_id", _TEST_PROGRAM_ID)
        monkeypatch.setattr(settings, "solana_cluster", "devnet")

        result = await get_release_tx(db, milestone_id, _CLIENT_ID)

        assert result["program_id"] == _TEST_PROGRAM_ID
        assert isinstance(result["escrow_pda"], str)
        assert result["milestone_index"] == 0  # order=1, index=0
        assert result["cluster"] == "devnet"
        assert isinstance(result["accounts"], list)
        assert len(result["accounts"]) >= 2  # escrow_pda + freelancer + system_program

    @pytest.mark.asyncio
    async def test_disputed_raises_409(self, db: AsyncSession):
        gig_id, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "DISPUTED")
        await db.execute(
            sa_update(GigModel)
            .where(GigModel.id == gig_id)
            .values(contract_address="SomeSolanaAddress111111111111111111111111111")
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

    @pytest.mark.asyncio
    async def test_no_program_id_raises_error(self, db: AsyncSession, monkeypatch):
        gig_id, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "APPROVED")
        await db.execute(
            sa_update(GigModel)
            .where(GigModel.id == gig_id)
            .values(contract_address="SomeSolanaAddress111111111111111111111111111")
        )
        await db.flush()

        from src.config import settings

        monkeypatch.setattr(settings, "escrow_program_id", "")

        with pytest.raises(MilestoneApprovalError) as exc_info:
            await get_release_tx(db, milestone_id, _CLIENT_ID)

        assert exc_info.value.code == "NO_PROGRAM_ID"


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
