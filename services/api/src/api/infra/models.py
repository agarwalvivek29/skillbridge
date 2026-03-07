"""
SQLAlchemy ORM models.

Enum values mirror the proto-generated UserStatus / UserRole enum names.
Never define enum values here that don't exist in the proto.
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Index, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


class DBUserStatus(enum.StrEnum):
    PENDING_VERIFICATION = "USER_STATUS_PENDING_VERIFICATION"
    ACTIVE = "USER_STATUS_ACTIVE"
    INACTIVE = "USER_STATUS_INACTIVE"
    BANNED = "USER_STATUS_BANNED"


class DBUserRole(enum.StrEnum):
    MEMBER = "USER_ROLE_MEMBER"
    ADMIN = "USER_ROLE_ADMIN"
    SUPER_ADMIN = "USER_ROLE_SUPER_ADMIN"


def _new_uuid() -> str:
    return str(uuid.uuid4())


class UserModel(Base):
    __tablename__ = "users"

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    email: str | None = Column(String(255), unique=True, nullable=True)
    name: str | None = Column(String(255), nullable=True)
    password_hash: str | None = Column(String(255), nullable=True)
    wallet_address: str | None = Column(String(42), unique=True, nullable=True)
    status: DBUserStatus = Column(
        SAEnum(DBUserStatus, name="user_status", native_enum=False),
        nullable=False,
        default=DBUserStatus.ACTIVE,
    )
    role: DBUserRole = Column(
        SAEnum(DBUserRole, name="user_role", native_enum=False),
        nullable=False,
        default=DBUserRole.MEMBER,
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )


class SiweNonceModel(Base):
    __tablename__ = "siwe_nonces"

    nonce: str = Column(String(64), primary_key=True)
    address: str = Column(String(42), nullable=False)
    expires_at: datetime = Column(DateTime(timezone=True), nullable=False)
    used: bool = Column(Boolean, nullable=False, default=False)
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )

    __table_args__ = (
        Index("idx_siwe_nonces_address", "address"),
        Index("idx_siwe_nonces_expires_at", "expires_at"),
    )
