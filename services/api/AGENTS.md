# AGENTS.md — api

> This file is the agent contract for the `api` service.
> Every agent (Claude Code, Copilot, Codex, Cursor, or other AI) MUST read this file before modifying anything in this service directory.
> Keep this file up to date as the service evolves.

---

## Service Overview

**Name**: `api`
**Purpose**: Core backend API for SkillBridge. Owns user auth (SIWE + email/JWT), gig management, milestone tracking, work submissions, and portfolio management. Coordinates with the `ai-reviewer` service via Celery/Redis and triggers smart contract interactions on Base L2.
**Owner**: Platform team
**Created**: 2026-03-07
**Issue**: #1
**Spec**: `docs/specs/1-user-auth.md`
**ADR**: `docs/adr/0002-tech-stack.md`

---

## Tech Stack

- **Language**: Python 3.12
- **Runtime**: Python 3.12 (managed by uv)
- **Framework**: FastAPI + uvicorn
- **Database**: PostgreSQL (SQLAlchemy 2.0 async + asyncpg driver)
- **Migrations**: alembic
- **Queue**: Redis (as Celery broker for ai-reviewer tasks)
- **Protocol**: REST API

---

## Repository Layout

```
services/api/
├── src/
│   └── api/
│       ├── __init__.py
│       ├── main.py          # FastAPI app factory, lifespan, middleware registration
│       ├── config.py        # pydantic-settings — all env vars validated here
│       ├── api/             # Route handlers (controllers)
│       │   ├── __init__.py
│       │   ├── auth.py      # /v1/auth/* routes
│       │   └── health.py    # /health, /metrics
│       ├── domain/          # Business logic — zero framework imports
│       │   ├── __init__.py
│       │   ├── auth.py      # hash_password, verify_password, issue_jwt, verify_jwt
│       │   └── siwe.py      # generate_nonce, verify_siwe_message
│       └── infra/           # DB, queue, external clients
│           ├── __init__.py
│           ├── database.py  # SQLAlchemy engine and session factory
│           ├── models.py    # ORM models (derived from proto enums)
│           └── user_repo.py # User repository (DB access)
├── migrations/              # alembic migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py  # users + siwe_nonces tables
├── tests/
│   ├── unit/
│   │   ├── test_domain_auth.py
│   │   └── test_domain_siwe.py
│   └── e2e/
│       ├── conftest.py
│       ├── test_auth_email.py
│       ├── test_auth_wallet.py
│       └── test_auth_middleware.py
├── pyproject.toml
├── .env.example
├── Dockerfile
├── Dockerfile.dev
└── README.md
```

---

## Key Entry Points

- **Main**: `src/api/main.py` — FastAPI app factory; health/metrics routes registered before auth middleware
- **Routes**: `src/api/api/auth.py` — auth endpoints
- **Config**: `src/api/config.py` — all env vars validated here; import `settings` not `os.environ`

---

## Environment Variables

See `.env.example` for all required variables.

Key variables:
| Variable | Description | Example |
|---|---|---|
| `PORT` | HTTP server port | `8000` |
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/skillbridge` |
| `JWT_SECRET` | HS256 signing secret (min 32 chars) | `change-me-in-production-32-chars` |
| `JWT_EXPIRY_SECONDS` | Token TTL in seconds | `3600` |
| `API_KEY` | Service-to-service API key (min 16 chars) | `change-me-16chars` |
| `SIWE_DOMAIN` | Expected SIWE domain for signature verification | `skillbridge.xyz` |
| `SIWE_CHAIN_ID` | Expected EVM chain ID (8453 = Base mainnet, 84532 = Base Sepolia) | `84532` |
| `NONCE_TTL_SECONDS` | SIWE nonce validity window | `300` |

---

## Interfaces

### Exposes

- `GET /health` — liveness probe (EXEMPT from auth)
- `GET /metrics` — Prometheus metrics (EXEMPT from auth)
- `GET /v1/auth/nonce?address={wallet_address}` — get SIWE nonce
- `POST /v1/auth/wallet` — SIWE verify + JWT
- `POST /v1/auth/register` — email registration + JWT
- `POST /v1/auth/login` — email login + JWT

### Consumes

- PostgreSQL: `users`, `siwe_nonces` tables
- Redis: Celery task broker (for dispatching AI review tasks — added in future issues)

### Events Published

- None in v1 auth (future: UserCreatedEvent via Redis/Celery)

---

## Local Development

```bash
# From repo root — start postgres
docker compose -f infra/docker-compose.yml up -d postgres

# From services/api
cp .env.example .env
# Edit .env — set DATABASE_URL, JWT_SECRET, API_KEY, etc.
uv sync
uv run alembic upgrade head
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Running Tests

```bash
# From services/api
uv run pytest tests/unit/    # unit tests
uv run pytest tests/e2e/     # e2e tests (requires running DB)
uv run pytest                # all tests
```

---

## Auth Middleware

This service uses dual-mode authentication middleware on **all routes** except `/health` and `/metrics`.

Accepted credentials (checked in this order):

1. `X-API-Key: <value>` — must match `API_KEY` env var (service-to-service)
2. `Authorization: Bearer <jwt>` — verified with `JWT_SECRET` env var (user or service token)

**Required env vars** (must be set in `.env`, validated at startup):

- `JWT_SECRET` — minimum 32 characters
- `API_KEY` — minimum 16 characters
- `JWT_EXPIRY_SECONDS` — default 3600

**Agent rules:**

- Never add an unprotected route without explicit human approval
- Never log the value of `JWT_SECRET`, `API_KEY`, or any token
- Auth middleware must be the first middleware applied (before logging, rate-limiting)
- `/health` and `/metrics` are registered on `app` directly before auth middleware is applied

---

## Schema Package Usage

This service's data types are defined in `packages/schema/proto/api/v1/`.

**Schema-First Rule**: NEVER define a type, interface, struct, enum, or class for a business domain concept in service code. All types come from the generated schema.

```python
# Import generated types:
from schema.api.v1 import User, UserStatus, UserRole
```

If you need a new type:

1. Add it to `packages/schema/proto/api/v1/`
2. Run `cd packages/schema && ./scripts/generate.sh`
3. Commit proto + generated output
4. Import the generated type here

---

## Testing Requirements

Backend services MUST have both test directories:

- `tests/unit/` — one test per public domain function
- `tests/e2e/` — happy path test per API endpoint

```bash
uv run pytest tests/unit/   # unit
uv run pytest tests/e2e/    # e2e
```

---

## Forbidden Actions for Agents

> These actions require explicit human approval and must NOT be performed autonomously.

- Modifying existing alembic migrations in `migrations/versions/`
- Changing the service's public API contract (adding/removing endpoints, changing response shape)
- Adding new external service dependencies
- Changing `SIWE_DOMAIN` or `SIWE_CHAIN_ID` defaults
- Modifying `Dockerfile` for production builds
- Any write operation to production databases

---

## Architectural Constraints

- All business logic in `domain/` — zero FastAPI/SQLAlchemy imports there
- Database access only through repository interfaces in `infra/`
- Pydantic models for request/response validation; domain types from generated proto
- SIWE nonces are single-use and expire after `NONCE_TTL_SECONDS`
- wallet_address stored in EIP-55 checksummed form (mixed case)

---

## Known Issues and Gotchas

- The `siwe` Python library requires `eth-account` ≥ 0.9 — check compatibility before upgrades
- SQLAlchemy async requires `asyncpg` (not `psycopg2`) as the driver
- alembic `env.py` must use async context for async engine — see `migrations/env.py`

---

## Related ADRs

- [ADR 0001](../../docs/adr/0001-monorepo-structure.md) — Monorepo structure
- [ADR 0002](../../docs/adr/0002-tech-stack.md) — Tech stack decisions

---

## Changelog

| Date       | Change                                                    | Author     |
| ---------- | --------------------------------------------------------- | ---------- |
| 2026-03-07 | Service created; user auth (SIWE + email/JWT) implemented | Agent (ao) |
