"""
api/auth.py — Auth endpoints (nonce, wallet login, email register, email login).
All four endpoints are public (exempt from auth middleware).
"""

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import base58

from src.domain import auth as auth_domain
from src.domain.enums import UserRole
from src.infra.database import get_db
from src.infra.models import AuthNonceModel

router = APIRouter(prefix="/v1/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response Pydantic models (thin wrappers — shape comes from proto)
# ---------------------------------------------------------------------------


class NonceResponse(BaseModel):
    nonce: str
    expires_at: str  # ISO-8601


class WalletLoginRequest(BaseModel):
    wallet_address: str
    signature: str
    message: str


class EmailRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = UserRole.FREELANCER

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {UserRole.FREELANCER, UserRole.CLIENT}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class EmailLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    wallet_address: str | None = None
    email: str | None = None
    name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    role: str
    created_at: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user_id: str
    user: UserOut


def _auth_response(token: str, expires_in: int, user) -> AuthResponse:
    return AuthResponse(
        access_token=token,
        expires_in=expires_in,
        user_id=user.id,
        user=UserOut(
            id=user.id,
            wallet_address=user.wallet_address,
            email=user.email,
            name=user.name,
            bio=user.bio,
            avatar_url=user.avatar_url,
            role=user.role,
            created_at=user.created_at.isoformat() if user.created_at else "",
        ),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/nonce", response_model=NonceResponse)
async def get_nonce(
    wallet_address: str = Query(..., description="Solana wallet address (base58)"),
    db: AsyncSession = Depends(get_db),
) -> NonceResponse:
    """Step 1 of wallet auth: generate a one-time nonce for the given Solana wallet address."""
    # Solana base58 addresses are 32-44 characters
    if not wallet_address or len(wallet_address) < 32 or len(wallet_address) > 44:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_WALLET_ADDRESS",
                "message": "Must be a valid base58 Solana address (32-44 characters)",
            },
        )
    # Validate that it is valid base58
    try:
        decoded = base58.b58decode(wallet_address)
        if len(decoded) != 32:
            raise ValueError("Invalid public key length")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_WALLET_ADDRESS",
                "message": "Must be a valid base58 Solana address",
            },
        )
    record = await auth_domain.create_nonce(db, wallet_address)
    return NonceResponse(
        nonce=record.nonce,
        expires_at=record.expires_at.astimezone(timezone.utc).isoformat(),
    )


@router.post("/wallet", response_model=AuthResponse)
async def wallet_login(
    body: WalletLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Step 2 of wallet auth: verify Solana Ed25519 signature, delete nonce, upsert user, issue JWT."""
    # Fetch nonce record WITHOUT consuming it yet — consume only after sig is verified
    result = await db.execute(
        select(AuthNonceModel).where(
            AuthNonceModel.wallet_address == body.wallet_address
        )
    )
    nonce_record = result.scalar_one_or_none()
    if nonce_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "NONCE_INVALID_OR_EXPIRED",
                "message": "Nonce not found or expired. Request a new nonce.",
            },
        )

    # Verify Ed25519 signature BEFORE consuming the nonce (prevents DoS nonce-burning)
    valid = auth_domain.verify_solana_signature(
        wallet_address=body.wallet_address,
        message=body.message,
        signature=body.signature,
        expected_nonce=nonce_record.nonce,
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_SIGNATURE",
                "message": "Signature verification failed",
            },
        )

    # Signature is valid — now consume (delete) the nonce
    consumed = await auth_domain.consume_nonce(db, body.wallet_address)
    if consumed is None:
        # Expired between the fetch and now (edge case)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "NONCE_INVALID_OR_EXPIRED",
                "message": "Nonce expired. Request a new nonce.",
            },
        )

    user = await auth_domain.upsert_wallet_user(db, body.wallet_address)
    token, expires_in = auth_domain.create_access_token(user.id, user.role)
    return _auth_response(token, expires_in, user)


@router.post(
    "/email/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def email_register(
    body: EmailRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Register with email + password. Returns JWT on success."""
    existing = await auth_domain.get_user_by_email(db, body.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMAIL_TAKEN",
                "message": "A user with this email already exists",
            },
        )

    password_hash = auth_domain.hash_password(body.password)
    try:
        user = await auth_domain.create_user_email(
            db=db,
            email=body.email,
            name=body.name,
            password_hash=password_hash,
            role=body.role,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMAIL_TAKEN",
                "message": "A user with this email already exists",
            },
        )
    token, expires_in = auth_domain.create_access_token(user.id, user.role)
    return _auth_response(token, expires_in, user)


@router.post("/email/login", response_model=AuthResponse)
async def email_login(
    body: EmailLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Login with email + password. Returns JWT on success."""
    user = await auth_domain.get_user_by_email(db, body.email)
    if user is None or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Email or password is incorrect",
            },
        )

    if not auth_domain.verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Email or password is incorrect",
            },
        )

    token, expires_in = auth_domain.create_access_token(user.id, user.role)
    return _auth_response(token, expires_in, user)
