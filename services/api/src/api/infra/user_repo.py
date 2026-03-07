"""
User repository — all DB access for users and SIWE nonces.

Business logic lives in domain/; this module only handles persistence.
"""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.infra.models import SiweNonceModel, UserModel


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> UserModel | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        return result.scalar_one_or_none()

    async def get_by_wallet(self, wallet_address: str) -> UserModel | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.wallet_address == wallet_address)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> UserModel | None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> UserModel:
        user = UserModel(**kwargs)
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user


class NonceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, nonce: str, address: str, expires_at: datetime) -> SiweNonceModel:
        record = SiweNonceModel(nonce=nonce, address=address, expires_at=expires_at)
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_valid(self, nonce: str, address: str) -> SiweNonceModel | None:
        """Return the nonce record if it exists, is not used, and has not expired."""
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(SiweNonceModel).where(
                SiweNonceModel.nonce == nonce,
                SiweNonceModel.address == address,
                SiweNonceModel.used.is_(False),
                SiweNonceModel.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def mark_used(self, nonce: str) -> None:
        """Mark a nonce as used so it cannot be replayed."""
        await self._session.execute(
            update(SiweNonceModel).where(SiweNonceModel.nonce == nonce).values(used=True)
        )
