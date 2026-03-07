# Spec: User Authentication (Wallet SIWE + Email/JWT)

> Copy this file to `docs/specs/[ISSUE-NUMBER]-[feature-name].md` and fill it in.
> The spec must be completed and linked in the GitHub Issue before implementation begins.

**Issue**: #1
**Status**: Approved
**Author**: Agent (ao)
**Date**: 2026-03-07
**Services Affected**: `services/api`

---

## Summary

Implement dual authentication for SkillBridge: Sign-In with Ethereum (SIWE) for wallet users and email/password for traditional login. Both flows produce a JWT used for all subsequent authenticated API calls. Wallet address and email can be linked to the same User record.

---

## Background and Motivation

SkillBridge targets both crypto-native users (who prefer wallet-based authentication) and mainstream users who want traditional email login. A dual auth system maximizes onboarding conversion. SIWE is the EIP-4361 standard for wallet authentication, avoiding password management for Web3 users entirely.

---

## Scope

### In Scope

- SIWE nonce generation endpoint (`GET /v1/auth/nonce`)
- SIWE verify endpoint (`POST /v1/auth/wallet`) — verifies signature, creates or retrieves User, issues JWT
- Email registration endpoint (`POST /v1/auth/register`)
- Email login endpoint (`POST /v1/auth/login`)
- JWT auth middleware applied to all routes except `/health` and `/metrics`
- User DB table with `wallet_address` and `email` both nullable (but at least one required)
- `User` proto type and generated Python bindings

### Out of Scope

- OAuth (Google, GitHub, Twitter) login — deferred to v2
- JWT refresh tokens — v1 uses single long-lived tokens (configurable TTL)
- 2FA — deferred to v1 complete
- Email verification flow — users are ACTIVE immediately after registration in v1

---

## Acceptance Criteria

- [ ] Given a user with MetaMask, when they call `GET /v1/auth/nonce?address=0x...`, then they receive a unique nonce valid for 5 minutes
- [ ] Given a valid SIWE signature, when calling `POST /v1/auth/wallet`, then a JWT is returned and the user record is created (first time) or retrieved (returning user)
- [ ] Given an invalid or expired SIWE signature, when calling `POST /v1/auth/wallet`, then a `400 Bad Request` with error code `INVALID_SIGNATURE` is returned
- [ ] Given valid email + password, when calling `POST /v1/auth/register`, then a `201 Created` with JWT is returned and the user is stored with bcrypt-hashed password
- [ ] Given duplicate email on registration, when calling `POST /v1/auth/register`, then `409 Conflict` with `EMAIL_ALREADY_EXISTS` is returned
- [ ] Given valid email + password, when calling `POST /v1/auth/login`, then `200 OK` with JWT is returned
- [ ] Given wrong password on login, when calling `POST /v1/auth/login`, then `401 Unauthorized` with `INVALID_CREDENTIALS` is returned
- [ ] Given a valid JWT in `Authorization: Bearer`, when calling a protected route, then the request is authorized
- [ ] Given no credentials, when calling a protected route, then `401 Unauthorized` with `UNAUTHORIZED` is returned
- [ ] Given a valid `X-API-Key` header, when calling a protected route from a service, then the request is authorized
- [ ] `GET /health` and `GET /metrics` are accessible without any credentials
- [ ] Passwords are never stored in plaintext (bcrypt with cost factor 12)
- [ ] Nonces are single-use — verified nonce is invalidated immediately

---

## Technical Design

### Architecture Overview

```
Client
  │
  ├── GET  /v1/auth/nonce?address=0x...    ─── Returns {nonce, expires_at}
  │
  ├── POST /v1/auth/wallet                 ─── SIWE: verify sig → upsert user → JWT
  │   Body: {message, signature}
  │
  ├── POST /v1/auth/register               ─── Email: hash password → create user → JWT
  │   Body: {email, password, name}
  │
  └── POST /v1/auth/login                  ─── Email: verify password → JWT
      Body: {email, password}

All other routes ──▶ Auth Middleware ──▶ Handler
                         │
                    Check X-API-Key header first
                    Then check Authorization: Bearer
                    Fail → 401 UNAUTHORIZED
```

### API Changes

#### New Endpoints

```
GET /v1/auth/nonce?address={wallet_address}
Response 200: {
  "nonce": "abc123xyz",
  "expires_at": "2026-03-07T12:05:00Z"
}

POST /v1/auth/wallet
Request: {
  "message": "<SIWE message string>",
  "signature": "0x..."
}
Response 200: {
  "token": "<jwt>",
  "user": { "id": "...", "wallet_address": "0x...", "email": null, "name": null, "status": "USER_STATUS_ACTIVE", "role": "USER_ROLE_MEMBER" }
}
Response 400: { "code": "INVALID_SIGNATURE", "message": "SIWE signature verification failed" }
Response 400: { "code": "NONCE_EXPIRED", "message": "Nonce has expired or already been used" }

POST /v1/auth/register
Request: {
  "email": "alice@example.com",
  "password": "supersecure123",
  "name": "Alice"
}
Response 201: {
  "token": "<jwt>",
  "user": { "id": "...", "wallet_address": null, "email": "alice@example.com", "name": "Alice", "status": "USER_STATUS_ACTIVE", "role": "USER_ROLE_MEMBER" }
}
Response 409: { "code": "EMAIL_ALREADY_EXISTS", "message": "An account with this email already exists" }
Response 422: { "code": "VALIDATION_FAILED", "message": "...", "field_errors": [...] }

POST /v1/auth/login
Request: {
  "email": "alice@example.com",
  "password": "supersecure123"
}
Response 200: {
  "token": "<jwt>",
  "user": { ... }
}
Response 401: { "code": "INVALID_CREDENTIALS", "message": "Invalid email or password" }
```

#### New Endpoints (Infrastructure)

```
GET /health
Response 200: { "status": "ok" }

GET /metrics
Response 200: (Prometheus text format)
```

### Data Model Changes

#### New Tables

```sql
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         VARCHAR(255) UNIQUE,
  name          VARCHAR(255),
  password_hash VARCHAR(255),          -- nullable for wallet-only users
  wallet_address VARCHAR(42) UNIQUE,   -- nullable for email-only users; EIP-55 checksummed
  status        VARCHAR(50) NOT NULL DEFAULT 'USER_STATUS_ACTIVE',
  role          VARCHAR(50) NOT NULL DEFAULT 'USER_ROLE_MEMBER',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- At least one of email or wallet_address must be present
ALTER TABLE users ADD CONSTRAINT users_identity_check
  CHECK (email IS NOT NULL OR wallet_address IS NOT NULL);

CREATE TABLE siwe_nonces (
  nonce        VARCHAR(64) PRIMARY KEY,
  address      VARCHAR(42) NOT NULL,
  expires_at   TIMESTAMPTZ NOT NULL,
  used         BOOLEAN NOT NULL DEFAULT false,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_siwe_nonces_address ON siwe_nonces(address);
CREATE INDEX idx_siwe_nonces_expires_at ON siwe_nonces(expires_at);
```

### Dependencies

New Python packages required:

- `fastapi` + `uvicorn` — HTTP server
- `sqlalchemy[asyncio]` + `asyncpg` — async ORM + PostgreSQL driver
- `alembic` — migrations
- `pydantic-settings` — env var validation
- `python-jose[cryptography]` or `pyjwt` — JWT signing/verification
- `passlib[bcrypt]` — password hashing
- `siwe` — SIWE message parsing and verification
- `eth-account` — Ethereum signature verification
- `prometheus-fastapi-instrumentator` — /metrics endpoint
- `structlog` — structured logging
- `betterproto` — generated proto types

---

## Security Considerations

- Passwords stored with bcrypt (cost factor 12) — never plaintext
- SIWE nonces are cryptographically random (secrets.token_hex(32)), single-use, expire in 5 minutes
- JWT signed with HS256 + shared secret (min 32 chars); expiry configurable via `JWT_EXPIRY_SECONDS`
- `JWT_SECRET` and `API_KEY` never logged
- All auth endpoints rate-limited (via middleware) to prevent brute force
- SIWE message domain and chain ID validated against expected values
- wallet_address stored in EIP-55 checksummed form

---

## Observability

- **Logs**: Auth method (`api-key` | `jwt`) and subject (`user:{id}` | `service`) logged at INFO on success; failures at WARN
- **Metrics**: `/metrics` endpoint via prometheus-fastapi-instrumentator (request count, latency)
- **Alerts**: Repeated `INVALID_CREDENTIALS` from same IP → alert (future work)

---

## Testing Plan

### Unit Tests (`tests/unit/`)

- `test_domain_auth.py`: test `hash_password`, `verify_password`, `generate_nonce`, `issue_jwt`, `verify_jwt`
- `test_domain_siwe.py`: test SIWE message parsing, signature verification (mock eth_account)

### E2E Tests (`tests/e2e/`)

- `test_auth_wallet.py`: GET /v1/auth/nonce → POST /v1/auth/wallet happy path
- `test_auth_email.py`: POST /v1/auth/register → POST /v1/auth/login happy path
- `test_auth_middleware.py`: protected route with no creds, valid JWT, valid API key, invalid JWT

### Manual Testing Steps

1. `docker compose up -d postgres` (start DB)
2. `cd services/api && cp .env.example .env && uv run alembic upgrade head`
3. `uv run uvicorn src.api.main:app --reload`
4. `curl http://localhost:8000/health` → `{"status":"ok"}`
5. `curl -X POST http://localhost:8000/v1/auth/register -H "Content-Type: application/json" -d '{"email":"test@test.com","password":"password123","name":"Test"}'`
6. Copy the JWT from the response; test protected route with `Authorization: Bearer <token>`

---

## Migration / Rollout Plan

- **Database migrations**: Yes — alembic migration creates `users` and `siwe_nonces` tables
- **Breaking changes**: No — new service, no existing consumers
- **Feature flag**: No
- **Rollback plan**: `alembic downgrade -1` removes the tables; no data loss risk in v1

---

## Open Questions

| Question                                              | Owner   | Status                      |
| ----------------------------------------------------- | ------- | --------------------------- |
| Should wallet-only users be asked to add email later? | Product | Open (v1: optional linking) |

---

## References

- Related ADR: [ADR 0002](../adr/0002-tech-stack.md)
- EIP-4361 SIWE: https://eips.ethereum.org/EIPS/eip-4361
- Issue: #1
