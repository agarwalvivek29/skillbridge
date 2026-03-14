"""
domain/auth.py — Pure business logic for authentication.
No FastAPI imports. No DB session. All side-effect-free helpers + DB-taking functions.
"""

import base64
import secrets
import string
from datetime import datetime, timedelta, timezone

import base58
import bcrypt as _bcrypt
import nacl.signing
from jose import jwt
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.domain.enums import UserRole, UserStatus
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
    Wallet address is stored as-is (base58 is case-sensitive).
    """
    normalised = wallet_address
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
    Wallet address is matched as-is (base58 is case-sensitive).
    """
    normalised = wallet_address
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
# Solana message helpers
# ---------------------------------------------------------------------------


def build_solana_sign_in_message(wallet_address: str, nonce: str) -> str:
    """
    Build the plaintext message that Solana wallets sign for authentication.

    Format:
        SkillBridge wants you to sign in with your Solana account:
        <base58_wallet_address>

        Nonce: <nonce>
        Issued At: <iso_timestamp>
    """
    issued_at = datetime.now(timezone.utc).isoformat()
    return (
        f"SkillBridge wants you to sign in with your Solana account:\n"
        f"{wallet_address}\n"
        f"\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued_at}"
    )


# ---------------------------------------------------------------------------
# Solana Ed25519 signature verification
# ---------------------------------------------------------------------------


def verify_solana_signature(
    wallet_address: str,
    message: str,
    signature: str,
    expected_nonce: str,
) -> bool:
    """
    Verify an Ed25519 signature from a Solana wallet.

    Steps:
    1. Decode the base58 public key from wallet_address
    2. Decode the base64-encoded signature
    3. Verify the Ed25519 signature over the UTF-8 message bytes
    4. Check that the nonce in the message matches expected_nonce

    Returns True only if all checks pass; False on any failure.
    """
    try:
        # Check that the expected nonce appears in the message
        if f"Nonce: {expected_nonce}" not in message:
            return False

        # Check that the claimed wallet address appears in the signed message
        if wallet_address not in message:
            return False

        # Decode the base58 public key
        pubkey_bytes = base58.b58decode(wallet_address)
        if len(pubkey_bytes) != 32:
            return False

        # Decode the base64 signature
        sig_bytes = base64.b64decode(signature)

        # Verify Ed25519 signature — raises BadSignatureError if invalid
        verify_key = nacl.signing.VerifyKey(pubkey_bytes)
        verify_key.verify(message.encode("utf-8"), sig_bytes)

        return True
    except Exception:  # noqa: BLE001 — catch all verification errors
        return False


# ---------------------------------------------------------------------------
# User DB helpers
# ---------------------------------------------------------------------------


async def get_user_by_email(db: AsyncSession, email: str) -> UserModel | None:
    result = await db.execute(select(UserModel).where(UserModel.email == email))
    return result.scalar_one_or_none()


async def get_user_by_wallet(db: AsyncSession, wallet_address: str) -> UserModel | None:
    result = await db.execute(
        select(UserModel).where(UserModel.wallet_address == wallet_address)
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
        status=UserStatus.ACTIVE,
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
            wallet_address=wallet_address,
            name=short,
            role=UserRole.FREELANCER,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        await db.flush()
    return user
