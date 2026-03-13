# AGENTS.md — api

> Agent contract for the `api` service.
> Read this before modifying anything in this service directory.

---

## Service Overview

**Name**: `api`
**Purpose**: The core backend for SkillBridge. Owns all business entities — Users, Gigs, Milestones, Submissions, Portfolio, and Disputes. Handles authentication (Solana wallet Ed25519 signing + email/JWT), triggers smart contract calls on Base L2 for fund release, enqueues AI review jobs, and serves as the single source of truth for all mutable state.
**Language**: Python
**Framework**: FastAPI
**Created**: 2026-03-07
**ADR**: `docs/adr/0002-tech-stack.md`

---

## Tech Stack

- **Language**: Python 3.12
- **Framework**: FastAPI (async)
- **Database**: PostgreSQL (via SQLAlchemy async + Alembic migrations)
- **Queue**: Redis + Celery (producer only — enqueues review jobs for `ai-reviewer`)
- **Blockchain**: web3.py (calls Base L2 smart contracts)
- **Auth**: Solana Ed25519 message signing (PyNaCl + base58) for wallet auth; JWT (python-jose) for session tokens
- **File storage**: boto3 (S3 presigned URL generation)
- **Protocol**: REST

---

## Repository Layout

```
services/api/
├── src/
│   ├── api/           # FastAPI routers (users, gigs, milestones, submissions, portfolio)
│   ├── domain/        # Business logic — no FastAPI imports here
│   ├── infra/         # DB session, S3 client, Celery producer, web3 client
│   ├── migrations/    # Alembic migrations
│   └── config.py      # Pydantic Settings — all env vars validated here
├── tests/
│   ├── unit/          # domain function tests
│   └── e2e/           # API endpoint tests (httpx AsyncClient)
├── Dockerfile
├── Dockerfile.dev
├── .env.example
└── README.md
```

---

## Key Entry Points

- **Main**: `src/main.py` — FastAPI app, middleware stack, router registration
- **Config**: `src/config.py` — import `settings` not `os.environ`
- **Routers**: `src/api/` — one file per resource
- **DB models**: generated from `packages/schema/proto/api/v1/`

---

## Environment Variables

See `.env.example` for all required variables.

| Variable                 | Description                             |
| ------------------------ | --------------------------------------- |
| `DATABASE_URL`           | PostgreSQL connection string            |
| `REDIS_URL`              | Redis connection string (for Celery)    |
| `JWT_SECRET`             | Min 32 chars — JWT signing key          |
| `JWT_EXPIRY_SECONDS`     | Default 3600                            |
| `API_KEY`                | Min 16 chars — service-to-service key   |
| `BASE_RPC_URL`           | Base L2 RPC endpoint                    |
| `ESCROW_FACTORY_ADDRESS` | Deployed EscrowFactory contract address |
| `AWS_ACCESS_KEY_ID`      | S3 access key                           |
| `AWS_SECRET_ACCESS_KEY`  | S3 secret key                           |
| `S3_BUCKET`              | S3 bucket name                          |

---

## Interfaces

### Exposes (REST)

- `GET /v1/auth/nonce?wallet_address=<addr>` — generate nonce for Solana wallet auth (public)
- `POST /v1/auth/wallet` — Solana Ed25519 wallet login, returns JWT (public)
- `POST /v1/auth/email/register` — email registration, returns JWT (public)
- `POST /v1/auth/email/login` — email/password login, returns JWT (public)
- `GET/POST /v1/users` — user CRUD (auth required)
- `GET /v1/gigs` — list open gigs for discovery board; supports filters: `skill`, `currency`, `min_amount`, `max_amount`, `status_filter` (public)
- `POST /v1/gigs` — create gig (auth required, CLIENT role)
- `GET /v1/gigs/:id` — get single gig with milestones (public)
- `PUT /v1/gigs/:id` — update gig (auth required, CLIENT role, DRAFT only)
- `DELETE /v1/gigs/:id` — delete gig (auth required, CLIENT role, DRAFT only)
- `POST /v1/proposals` — submit proposal for OPEN gig (auth required, FREELANCER role)
- `GET /v1/gigs/:id/proposals` — list proposals for gig (auth required, CLIENT role, gig owner)
- `POST /v1/proposals/:id/accept` — accept proposal, sets gig IN_PROGRESS (auth required, CLIENT role, gig owner)
- `POST /v1/proposals/:id/withdraw` — withdraw PENDING proposal (auth required, FREELANCER role, proposal owner)
- `POST /v1/gigs/:id/milestones` — add milestone to gig (auth required)
- `POST /v1/milestones/:id/submissions` — submit work (FREELANCER role, must be assigned freelancer)
- `GET /v1/milestones/:id/submissions` — list submissions / revision history (auth required)
- `GET /v1/submissions/:id` — get single submission (auth required)
- `POST /v1/submissions/upload-url` — generate S3 presigned PUT URL for file upload (auth required)
- `POST /v1/milestones/:id/approve` — approve milestone + trigger fund release (auth required)
- `GET/POST/PUT/DELETE /v1/portfolio` — portfolio item CRUD (auth required)
- `GET /health`, `GET /metrics` (no auth required)

### Events Published (to Celery/Redis)

- `review.enqueue` — triggers ai-reviewer when submission created with repo_url

### Blockchain Calls (outbound)

- `GigEscrow.completeMilestone(index)` on Base L2 — called on milestone approval

---

## Auth Middleware

All routes except the following prefixes require authentication:
`/health`, `/metrics`, `/v1/auth/`, `/docs`, `/redoc`, `/openapi.json`

1. `X-API-Key` — service-to-service (matched against `API_KEY`)
2. `Authorization: Bearer <jwt>` — user token (verified with `JWT_SECRET`)

Never add unprotected routes. Auth middleware is first in the chain.

---

## Schema Package Usage

All domain types come from `packages/schema/proto/api/v1/`.

```python
from schema.api.v1 import User, UserStatus, Gig, GigStatus, Milestone, Submission, PortfolioItem
```

Never define `class`, `dataclass`, or `TypedDict` for business domain concepts in service code.

---

## Forbidden Actions for Agents

- Modifying Alembic migrations after they've been applied
- Adding unprotected routes
- Committing secrets or private keys
- Calling smart contracts with real ETH on mainnet without human approval
- Defining domain types locally (use schema package)

---

## Agent Capabilities

Agents may use any available MCP servers, skills, and tools as needed.

### MCP Servers in Use

| MCP Server | Purpose | Added by |
| ---------- | ------- | -------- |
| (none yet) |         |          |

---

## Related ADRs

- [ADR 0001](../../docs/adr/0001-monorepo-structure.md) — Monorepo structure
- [ADR 0002](../../docs/adr/0002-tech-stack.md) — Tech stack decisions
- [ADR 0003](../../docs/adr/0003-solana-auth.md) — Replace SIWE with Solana message signing
