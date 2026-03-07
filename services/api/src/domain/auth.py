"""
domain/auth.py — Pure business logic for authentication.
No FastAPI imports. No DB session. All side-effect-free helpers + DB-taking functions.
"""

import secrets
import string
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
from jose import jwt
from siwe import SiweMessage
from siwe import DomainMismatch, ExpiredMessage, InvalidSignature, NonceMismatch
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.infra.models import AuthNonceModel, UserModel

# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the given plaintext password."""
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored bcrypt hash."""
    if not plain:
        return False
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

_ALGORITHM = "HS256"


def create_access_token(user_id: str, role: str) -> tuple[str, int]:
    """
    Issue a signed JWT.

    Returns (token, expires_in_seconds).
    """
    expires_in = settings.jwt_expiry_seconds
    exp = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {
        "sub": user_id,
        "role": role,
        "exp": exp,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT. Raises JWTError on failure.
    Returns the claims dict on success.
    """
    return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])


# ---------------------------------------------------------------------------
# Nonce helpers
# ---------------------------------------------------------------------------

_NONCE_ALPHABET = string.ascii_letters + string.digits
_NONCE_LENGTH = 32
_NONCE_TTL_MINUTES = 10


def _generate_nonce() -> str:
    return "".join(secrets.choice(_NONCE_ALPHABET) for _ in range(_NONCE_LENGTH))


async def create_nonce(db: AsyncSession, wallet_address: str) -> AuthNonceModel:
    """
    Generate a fresh nonce for the given wallet address and upsert it.
    Any previous nonce for this wallet is overwritten.
    Wallet address is normalised to lowercase before storage.
    """
    normalised = wallet_address.lower()
    nonce = _generate_nonce()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=_NONCE_TTL_MINUTES)

    # Upsert: delete existing then insert fresh
    await db.execute(
        delete(AuthNonceModel).where(AuthNonceModel.wallet_address == normalised)
    )
    record = AuthNonceModel(
        wallet_address=normalised,
        nonce=nonce,
        expires_at=expires_at,
    )
    db.add(record)
    await db.flush()
    return record


async def consume_nonce(db: AsyncSession, wallet_address: str) -> AuthNonceModel | None:
    """
    Retrieve the nonce for wallet_address and delete it atomically.
    Returns None if no nonce exists or if it has expired.
    Wallet address is normalised to lowercase before lookup.
    """
    normalised = wallet_address.lower()
    result = await db.execute(
        select(AuthNonceModel).where(AuthNonceModel.wallet_address == normalised)
    )
    record = result.scalar_one_or_none()
    if record is None:
        return None
    # SQLite returns naive datetimes; ensure comparison is tz-aware
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        await db.delete(record)
        return None
    await db.delete(record)
    return record


# ---------------------------------------------------------------------------
# SIWE verification
# ---------------------------------------------------------------------------

_SIWE_DOMAIN = "skillbridge.xyz"


def verify_siwe_signature(
    wallet_address: str,
    message: str,
    signature: str,
    expected_nonce: str,
) -> bool:
    """
    Verify a SIWE (EIP-4361) message and signature.

    Uses the `siwe` package for full EIP-4361 compliance:
    - Parses the structured SIWE message
    - Verifies the cryptographic signature
    - Checks domain matches _SIWE_DOMAIN
    - Checks nonce matches expected_nonce

    Returns True only if all checks pass; False on any failure.
    """
    try:
        siwe_msg = SiweMessage.from_message(message=message)
        siwe_msg.verify(
            signature=signature,
            domain=_SIWE_DOMAIN,
            nonce=expected_nonce,
        )
        # Extra check: recovered address must match the claimed wallet
        if siwe_msg.address.lower() != wallet_address.lower():
            return False
        return True
    except (
        InvalidSignature,
        DomainMismatch,
        NonceMismatch,
        ExpiredMessage,
        Exception,  # noqa: BLE001 — catch all siwe parse errors
    ):
        return False


# ---------------------------------------------------------------------------
# User DB helpers
# ---------------------------------------------------------------------------


async def get_user_by_email(db: AsyncSession, email: str) -> UserModel | None:
    result = await db.execute(select(UserModel).where(UserModel.email == email))
    return result.scalar_one_or_none()


async def get_user_by_wallet(db: AsyncSession, wallet_address: str) -> UserModel | None:
    result = await db.execute(
        select(UserModel).where(UserModel.wallet_address == wallet_address.lower())
    )
    return result.scalar_one_or_none()


async def create_user_email(
    db: AsyncSession, email: str, name: str, password_hash: str, role: str
) -> UserModel:
    user = UserModel(
        email=email,
        name=name,
        password_hash=password_hash,
        role=role,
        status="USER_STATUS_ACTIVE",
    )
    db.add(user)
    await db.flush()
    return user


async def upsert_wallet_user(db: AsyncSession, wallet_address: str) -> UserModel:
    """
    Find or create a user for the given wallet address.
    On first login the display name defaults to the truncated wallet address.
    New wallet users default to FREELANCER role (v1 limitation — see spec).
    """
    user = await get_user_by_wallet(db, wallet_address)
    if user is None:
        short = wallet_address[:6] + "…" + wallet_address[-4:]
        user = UserModel(
            wallet_address=wallet_address.lower(),
            name=short,
            role="USER_ROLE_FREELANCER",
            status="USER_STATUS_ACTIVE",
        )
        db.add(user)
        await db.flush()
    return user
