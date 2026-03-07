"""
Auth route handlers — /v1/auth/*

All endpoints in this router are EXEMPT from the global auth middleware
(they produce tokens rather than consuming them).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, field_validator
from siwe import SiweMessage
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.domain.auth import hash_password, issue_jwt, verify_password
from api.domain.siwe import (
    InvalidMessageError,
    InvalidSignatureError,
    NonceExpiredError,
    generate_nonce,
    verify_siwe_message,
)
from api.infra.database import get_session
from api.infra.models import DBUserRole, DBUserStatus, UserModel
from api.infra.user_repo import NonceRepository, UserRepository

router = APIRouter(prefix="/v1/auth", tags=["auth"])


# ─── Request / Response models ────────────────────────────────────────────────


class WalletLoginBody(BaseModel):
    message: str
    signature: str


class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    name: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class UserPublicOut(BaseModel):
    id: str
    email: str | None
    name: str | None
    wallet_address: str | None
    status: str
    role: str

    model_config = {"from_attributes": True}

    @field_validator("status", mode="before")
    @classmethod
    def coerce_status(cls, v) -> str:
        return v.value if hasattr(v, "value") else str(v)

    @field_validator("role", mode="before")
    @classmethod
    def coerce_role(cls, v) -> str:
        return v.value if hasattr(v, "value") else str(v)


class AuthOut(BaseModel):
    token: str
    user: UserPublicOut


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _user_to_out(user: UserModel) -> UserPublicOut:
    return UserPublicOut.model_validate(user)


def _issue_token(user: UserModel) -> str:
    return issue_jwt(
        subject=user.id,
        secret=settings.jwt_secret,
        expiry_seconds=settings.jwt_expiry_seconds,
        role=user.role.value,
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/nonce")
async def get_nonce(
    address: str = Query(..., description="Ethereum wallet address (EIP-55 checksummed)"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Generate and store a SIWE nonce for the given wallet address."""
    nonce, expires_at = generate_nonce(ttl_seconds=settings.nonce_ttl_seconds)
    nonce_repo = NonceRepository(session)
    await nonce_repo.create(nonce=nonce, address=address, expires_at=expires_at)
    return {"nonce": nonce, "expires_at": expires_at.isoformat()}


@router.post("/wallet", response_model=AuthOut)
async def wallet_login(
    body: WalletLoginBody,
    session: AsyncSession = Depends(get_session),
) -> AuthOut:
    """Verify a SIWE message + signature and return a JWT."""
    user_repo = UserRepository(session)
    nonce_repo = NonceRepository(session)

    # Extract nonce from the SIWE message to look up the server record
    try:
        siwe_msg = SiweMessage.from_message(message=body.message)
        nonce = siwe_msg.nonce
        address = siwe_msg.address
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_MESSAGE", "message": f"Malformed SIWE message: {exc}"},
        ) from exc

    # Validate nonce against DB
    nonce_record = await nonce_repo.get_valid(nonce=nonce, address=address)
    if nonce_record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NONCE_EXPIRED", "message": "Nonce has expired or already been used"},
        )

    # Verify SIWE signature
    try:
        verified_address = verify_siwe_message(
            message=body.message,
            signature=body.signature,
            expected_domain=settings.siwe_domain,
            expected_chain_id=settings.siwe_chain_id,
            nonce=nonce,
        )
    except NonceExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NONCE_EXPIRED", "message": str(exc)},
        ) from exc
    except InvalidSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_SIGNATURE", "message": str(exc)},
        ) from exc
    except InvalidMessageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_MESSAGE", "message": str(exc)},
        ) from exc

    # Mark nonce as used (single-use)
    await nonce_repo.mark_used(nonce)

    # Upsert user
    user = await user_repo.get_by_wallet(verified_address)
    if user is None:
        user = await user_repo.create(
            wallet_address=verified_address,
            status=DBUserStatus.ACTIVE,
            role=DBUserRole.MEMBER,
        )

    token = _issue_token(user)
    return AuthOut(token=token, user=_user_to_out(user))


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=AuthOut)
async def register(
    body: RegisterBody,
    session: AsyncSession = Depends(get_session),
) -> AuthOut:
    """Register a new user with email + password and return a JWT."""
    user_repo = UserRepository(session)

    existing = await user_repo.get_by_email(body.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EMAIL_ALREADY_EXISTS",
                "message": "An account with this email already exists",
            },
        )

    user = await user_repo.create(
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
        status=DBUserStatus.ACTIVE,
        role=DBUserRole.MEMBER,
    )

    token = _issue_token(user)
    return AuthOut(token=token, user=_user_to_out(user))


@router.post("/login", response_model=AuthOut)
async def login(
    body: LoginBody,
    session: AsyncSession = Depends(get_session),
) -> AuthOut:
    """Authenticate with email + password and return a JWT."""
    user_repo = UserRepository(session)

    user = await user_repo.get_by_email(body.email)
    pwd_ok = (
        user is not None
        and user.password_hash is not None
        and verify_password(body.password, user.password_hash)
    )
    if not pwd_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"},
        )

    token = _issue_token(user)
    return AuthOut(token=token, user=_user_to_out(user))
