# Spec: User Authentication (Wallet SIWE + Email/JWT)

> **Issue**: #1
> **Status**: Approved
> **Author**: ao agent
> **Date**: 2026-03-07
> **Services Affected**: `services/api`

---

## Summary

Implement dual authentication for SkillBridge: Sign-In with Ethereum (SIWE) for wallet users and email/password for traditional login. Both flows issue a JWT used for all subsequent API calls. This is the foundational auth layer that all other features depend on.

---

## Background and Motivation

SkillBridge targets crypto-native freelancers who prefer wallet-based identity. However, we also want to serve users who prefer email/password. Both flows must produce the same JWT artifact so that downstream middleware is auth-method agnostic.

Without this feature no other authenticated endpoint can be built or tested.

---

## Scope

### In Scope

- `GET /v1/auth/nonce?wallet_address=<addr>` — generates ephemeral nonce
- `POST /v1/auth/wallet` — SIWE signature verification, issues JWT
- `POST /v1/auth/email/register` — create user with hashed password, issues JWT
- `POST /v1/auth/email/login` — verify credentials, issues JWT
- JWT middleware applied to all routes (exempt: `/health`, `/metrics`)
- PostgreSQL tables: `users`, `auth_nonces`
- Alembic migration for both tables

### Out of Scope

- OAuth / social login
- JWT refresh tokens (can be added in a follow-up)
- Email verification flow
- Password reset flow
- Rate limiting (follow-up)

---

## Acceptance Criteria

- [ ] `GET /v1/auth/nonce?wallet_address=<addr>` returns `{nonce, expires_at}` and stores `AuthNonce` in DB with 10-minute TTL
- [ ] `POST /v1/auth/wallet` verifies SIWE signature via `eth_account`, deletes `AuthNonce`, upserts `User`, returns `AuthResponse`
- [ ] `POST /v1/auth/email/register` creates user with bcrypt-hashed password, returns `AuthResponse`
- [ ] `POST /v1/auth/email/login` verifies bcrypt hash, returns `AuthResponse`
- [ ] All four endpoints return `AuthResponse` shape: `{access_token, token_type: "Bearer", expires_in, user_id}`
- [ ] JWT middleware rejects requests missing/invalid tokens with `401 + ErrorResponse`
- [ ] `/health` and `/metrics` bypass auth middleware
- [ ] `AuthNonce` rows are hard-deleted after successful SIWE verification
- [ ] Passwords are never stored in plaintext — bcrypt only
- [ ] Unit tests cover: nonce creation, SIWE verification, JWT encode/decode, bcrypt helpers
- [ ] E2E tests cover happy path of all four endpoints
- [ ] `docker compose up api` starts cleanly

---

## Technical Design

### Architecture Overview

```
Browser / Client
    │
    ├── GET /v1/auth/nonce?wallet_address=0x...
    │       → DB: INSERT auth_nonces(wallet_address, nonce, expires_at)
    │       ← {nonce, expires_at}
    │
    ├── POST /v1/auth/wallet {wallet_address, signature, message}
    │       → eth_account.verify SIWE message + signature
    │       → DB: DELETE auth_nonces WHERE wallet_address=...
    │       → DB: UPSERT users (wallet_address)
    │       ← AuthResponse {access_token, ...}
    │
    ├── POST /v1/auth/email/register {email, password, name, role}
    │       → bcrypt.hash(password)
    │       → DB: INSERT users
    │       ← AuthResponse
    │
    └── POST /v1/auth/email/login {email, password}
            → DB: SELECT user WHERE email=...
            → bcrypt.verify(password, hash)
            ← AuthResponse
```

### API Changes

#### New Endpoints

```
GET  /v1/auth/nonce?wallet_address=<addr>
Response 200: { nonce: string, expires_at: string (ISO8601) }
Response 400: ErrorResponse

POST /v1/auth/wallet
Body: { wallet_address: string, signature: string, message: string }
Response 200: AuthResponse
Response 400: ErrorResponse (invalid signature / expired nonce)
Response 401: ErrorResponse

POST /v1/auth/email/register
Body: { email: string, password: string, name: string, role: "FREELANCER"|"CLIENT" }
Response 201: AuthResponse
Response 400: ErrorResponse (email taken, validation)
Response 422: Validation error

POST /v1/auth/email/login
Body: { email: string, password: string }
Response 200: AuthResponse
Response 401: ErrorResponse (wrong credentials)
```

### Data Model Changes

#### New Tables

```sql
CREATE TABLE users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email       TEXT UNIQUE,              -- null for wallet-only users
  name        TEXT NOT NULL,
  password_hash TEXT,                   -- null for wallet-only users
  wallet_address TEXT UNIQUE,           -- null for email-only users
  role        TEXT NOT NULL DEFAULT 'FREELANCER',
  status      TEXT NOT NULL DEFAULT 'ACTIVE',
  avatar_url  TEXT,
  bio         TEXT,
  skills      TEXT[] DEFAULT '{}',
  hourly_rate_wei TEXT DEFAULT '0',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE auth_nonces (
  wallet_address  TEXT PRIMARY KEY,
  nonce           TEXT NOT NULL,
  expires_at      TIMESTAMPTZ NOT NULL
);
```

### Dependencies

New Python packages required:

- `fastapi` — web framework
- `uvicorn` — ASGI server
- `sqlalchemy[asyncio]` — async ORM
- `asyncpg` — async PostgreSQL driver
- `alembic` — DB migrations
- `python-jose[cryptography]` — JWT encode/decode
- `passlib[bcrypt]` — bcrypt password hashing
- `eth-account` — SIWE / EIP-191 signature verification
- `pydantic-settings` — config from env
- `httpx` — async HTTP client (tests)
- `pytest-asyncio` — async test support
- `betterproto` — generated proto dataclasses

---

## Security Considerations

- Passwords: bcrypt with default work factor (12). Never log passwords.
- SIWE message: verify domain + nonce match to prevent replay attacks.
- Nonces: hard-deleted on use; expire in 10 minutes.
- JWT: HS256, signed with `JWT_SECRET` (min 32 chars).
- Auth middleware: first in middleware chain; logs auth method + subject, never the token value.
- No token forwarding in response bodies beyond the AuthResponse.

---

## Observability

- **Logs**: `INFO` on successful auth (method=wallet|email, user_id=...). `WARNING` on failed attempts.
- **Metrics**: `/metrics` endpoint exposed (Prometheus-compatible, even if stub).
- **Alerts**: None required for v1.

---

## Testing Plan

### Unit Tests (`tests/unit/`)

- `test_jwt.py`: encode/decode, expiry, invalid signature
- `test_password.py`: hash creation, verification, wrong password
- `test_nonce.py`: nonce generation, expiry check, deletion
- `test_siwe.py`: valid signature, invalid signature, expired nonce

### E2E Tests (`tests/e2e/`)

- `test_auth.py`: full happy path for all four endpoints using `httpx.AsyncClient` + SQLite in-memory

### Manual Testing Steps

1. `docker compose up postgres api`
2. `curl "http://localhost:8000/v1/auth/nonce?wallet_address=0xDEAD..."`
3. Sign the SIWE message with a wallet and POST to `/v1/auth/wallet`
4. `POST /v1/auth/email/register` with test credentials
5. Use the returned JWT as `Authorization: Bearer <token>` on a protected route
6. Verify `/health` and `/metrics` work without a token

---

## Migration / Rollout Plan

- **Database migrations**: Yes — `alembic revision --autogenerate` for `users` and `auth_nonces` tables.
- **Breaking changes**: No — this is a greenfield service.
- **Feature flag**: No.
- **Rollback plan**: `alembic downgrade -1` to drop the tables; redeploy previous image (none exists — net new).

---

## Open Questions

| Question                                                           | Owner   | Status                                        |
| ------------------------------------------------------------------ | ------- | --------------------------------------------- |
| Should wallet-only users be required to set a name on first login? | Product | Resolved: default to truncated wallet address |

---

## References

- Related ADR: [ADR 0002](../adr/0002-tech-stack.md) — Tech stack (FastAPI, JWT, SIWE)
- Proto: `packages/schema/proto/api/v1/auth.proto`, `packages/schema/proto/api/v1/user.proto`
- Issue: #1
