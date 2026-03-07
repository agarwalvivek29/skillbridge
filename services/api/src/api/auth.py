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

from src.domain import auth as auth_domain
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
    role: str = "USER_ROLE_FREELANCER"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"USER_ROLE_FREELANCER", "USER_ROLE_CLIENT"}
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


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/nonce", response_model=NonceResponse)
async def get_nonce(
    wallet_address: str = Query(..., description="EVM wallet address (0x...)"),
    db: AsyncSession = Depends(get_db),
) -> NonceResponse:
    """Step 1 of SIWE: generate a one-time nonce for the given wallet address."""
    if not wallet_address.startswith("0x") or len(wallet_address) != 42:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_WALLET_ADDRESS",
                "message": "Must be a 42-char hex address starting with 0x",
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
    """Step 2 of SIWE: verify signature, delete nonce, upsert user, issue JWT."""
    # Fetch nonce record WITHOUT consuming it yet — consume only after sig is verified
    result = await db.execute(
        select(AuthNonceModel).where(
            AuthNonceModel.wallet_address == body.wallet_address.lower()
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

    # Verify signature BEFORE consuming the nonce (prevents DoS nonce-burning)
    valid = auth_domain.verify_siwe_signature(
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
    return AuthResponse(access_token=token, expires_in=expires_in, user_id=user.id)


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
    return AuthResponse(access_token=token, expires_in=expires_in, user_id=user.id)


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
    return AuthResponse(access_token=token, expires_in=expires_in, user_id=user.id)
