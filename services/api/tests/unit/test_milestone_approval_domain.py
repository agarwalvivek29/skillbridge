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
    approve_milestone,
    build_release_instruction_data,
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
    UserModel,
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
        currency="SOL",
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
            chain_address="0xABCDEF1234567890AbcdEF1234567890aBcdef12",
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
# build_release_instruction_data (pure, no DB)
# ---------------------------------------------------------------------------

# A known base58-encoded Solana program ID for testing
_TEST_PROGRAM_ID = "11111111111111111111111111111111"


class TestBuildReleaseInstructionData:
    def test_basic_structure_with_all_wallets(self):
        result = build_release_instruction_data(
            gig_id="gig-1",
            milestone_index=0,
            freelancer_wallet="FrEeLaNcErPubKey1111111111111111111111111111",
            client_wallet="CLiEnTwAlLeTpUbKeY111111111111111111111111111",
            program_id=_TEST_PROGRAM_ID,
        )
        assert result["program_id"] == _TEST_PROGRAM_ID
        assert result["milestone_index"] == 0
        assert isinstance(result["escrow_seeds"], list)
        assert result["escrow_seeds"][0] == "escrow"
        assert isinstance(result["accounts"], list)
        # escrow_pda + client_signer + freelancer + system_program = 4 accounts
        assert len(result["accounts"]) == 4

    def test_no_freelancer_wallet(self):
        result = build_release_instruction_data(
            gig_id="gig-2",
            milestone_index=1,
            freelancer_wallet=None,
            client_wallet="CLiEnTwAlLeTpUbKeY111111111111111111111111111",
            program_id=_TEST_PROGRAM_ID,
        )
        # escrow_pda + client_signer + system_program = 3 accounts
        assert len(result["accounts"]) == 3

    def test_no_client_wallet(self):
        result = build_release_instruction_data(
            gig_id="gig-2",
            milestone_index=1,
            freelancer_wallet="FrEeLaNcErPubKey1111111111111111111111111111",
            client_wallet=None,
            program_id=_TEST_PROGRAM_ID,
        )
        # escrow_pda + freelancer + system_program = 3 accounts
        assert len(result["accounts"]) == 3

    def test_escrow_pda_placeholder_is_first_account(self):
        result = build_release_instruction_data(
            gig_id="gig-3",
            milestone_index=0,
            freelancer_wallet="SomeWallet111111111111111111111111111111111",
            client_wallet="CLiEnTwAlLeTpUbKeY111111111111111111111111111",
            program_id=_TEST_PROGRAM_ID,
        )
        assert result["accounts"][0]["is_escrow_pda"] is True
        assert result["accounts"][0]["pubkey"] is None
        assert result["accounts"][0]["is_writable"] is True

    def test_client_is_signer(self):
        result = build_release_instruction_data(
            gig_id="gig-4",
            milestone_index=0,
            freelancer_wallet="FrEeLaNcErPubKey1111111111111111111111111111",
            client_wallet="CLiEnTwAlLeTpUbKeY111111111111111111111111111",
            program_id=_TEST_PROGRAM_ID,
        )
        # client should be second account and a signer
        client_account = result["accounts"][1]
        assert (
            client_account["pubkey"] == "CLiEnTwAlLeTpUbKeY111111111111111111111111111"
        )
        assert client_account["is_signer"] is True

    def test_escrow_seeds_contain_gig_id_hex(self):
        result = build_release_instruction_data(
            gig_id="gig-5",
            milestone_index=0,
            freelancer_wallet=None,
            client_wallet=None,
            program_id=_TEST_PROGRAM_ID,
        )
        assert result["escrow_seeds"][0] == "escrow"
        assert result["escrow_seeds"][1] == "gig-5".encode("utf-8").hex()


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
            .values(escrow_pda="EscrowOnChainAddr11111111111111111111111111")
        )
        await db.flush()

        # Create user records with wallet addresses
        db.add(
            UserModel(
                id=_CLIENT_ID,
                name="Client",
                wallet_address="CLiEnTwAlLeT1111111111111111111111111111111",
            )
        )
        db.add(
            UserModel(
                id=_FREELANCER_ID,
                name="Freelancer",
                wallet_address="FrEeLaNcErWaLlEt1111111111111111111111111",
            )
        )
        await db.flush()

        # Patch settings for Solana config
        from src.config import settings

        monkeypatch.setattr(settings, "escrow_program_id", _TEST_PROGRAM_ID)
        monkeypatch.setattr(settings, "solana_cluster", "devnet")

        result = await get_release_tx(db, milestone_id, _CLIENT_ID)

        assert result["program_id"] == _TEST_PROGRAM_ID
        assert isinstance(result["escrow_seeds"], list)
        assert result["escrow_seeds"][0] == "escrow"
        assert result["milestone_index"] == 0  # order=1, index=0
        assert result["cluster"] == "devnet"
        assert isinstance(result["accounts"], list)
        # escrow_pda + client_signer + freelancer + system_program = 4
        assert len(result["accounts"]) == 4

    @pytest.mark.asyncio
    async def test_client_signer_in_accounts(self, db: AsyncSession, monkeypatch):
        gig_id, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "APPROVED")
        await db.execute(
            sa_update(GigModel)
            .where(GigModel.id == gig_id)
            .values(escrow_pda="EscrowOnChainAddr11111111111111111111111111")
        )
        await db.flush()

        db.add(
            UserModel(
                id=_CLIENT_ID,
                name="Client",
                wallet_address="CLiEnTwAlLeT1111111111111111111111111111111",
            )
        )
        db.add(
            UserModel(
                id=_FREELANCER_ID,
                name="Freelancer",
                wallet_address="FrEeLaNcErWaLlEt1111111111111111111111111",
            )
        )
        await db.flush()

        from src.config import settings

        monkeypatch.setattr(settings, "escrow_program_id", _TEST_PROGRAM_ID)
        monkeypatch.setattr(settings, "solana_cluster", "devnet")

        result = await get_release_tx(db, milestone_id, _CLIENT_ID)

        # client should be a signer in accounts
        client_accounts = [
            a
            for a in result["accounts"]
            if a.get("pubkey") == "CLiEnTwAlLeT1111111111111111111111111111111"
        ]
        assert len(client_accounts) == 1
        assert client_accounts[0]["is_signer"] is True

    @pytest.mark.asyncio
    async def test_disputed_raises_409(self, db: AsyncSession):
        gig_id, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "DISPUTED")
        await db.execute(
            sa_update(GigModel)
            .where(GigModel.id == gig_id)
            .values(escrow_pda="SomeSolanaAddress111111111111111111111111111")
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
    async def test_no_escrow_pda_raises_error(self, db: AsyncSession):
        _, milestone_id = await _setup_in_progress_gig(db)
        await _set_milestone_status(db, milestone_id, "APPROVED")
        # Gig has no escrow_pda (default is None)

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
            .values(escrow_pda="SomeSolanaAddress111111111111111111111111111")
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
