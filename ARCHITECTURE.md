# Architecture — SkillBridge

> The technical source of truth for this project.
> Update this document when architecture changes. Reference it in every ADR.

## System Overview

SkillBridge is a freelance marketplace with smart contract escrow on Base L2 and an AI quality verification layer. The system is a TypeScript/Python microservice monorepo: a Next.js frontend talks to a Python FastAPI backend, which coordinates with a Celery-based AI reviewer service (Claude Sonnet 4.6) and Solidity contracts on Base L2. All services share a schema-first type system via `packages/schema/proto/`.

## Service Map

| Service       | Language   | Type            | Responsibility                                                                         | Primary DB | Queue          |
| ------------- | ---------- | --------------- | -------------------------------------------------------------------------------------- | ---------- | -------------- |
| `web`         | TypeScript | Next.js App     | Client-facing UI: gig discovery, portfolio, checkout, dashboard                        | —          | —              |
| `api`         | Python     | REST API        | Core business logic: users, gigs, milestones, submissions, portfolios; issues JWTs     | PostgreSQL | Redis (Celery) |
| `ai-reviewer` | Python     | Worker          | Celery worker consuming review tasks; calls Claude Sonnet 4.6; produces review reports | PostgreSQL | Redis (Celery) |
| `contracts`   | Solidity   | Smart Contracts | Escrow contract, reputation NFT, badge minting on Base L2                              | —          | —              |

## Data Flow

```
[Browser / MetaMask]
        │
        ▼
  [web — Next.js]  ──── REST (JWT) ────▶ [api — FastAPI]
                                               │
                         ┌─────────────────────┤
                         │                     │
                         ▼                     ▼
                  [PostgreSQL]         [Redis / Celery]
                                               │
                                               ▼
                                    [ai-reviewer — Celery Worker]
                                               │
                                               ▼
                                   [Anthropic API — Claude]
                                               │
                                               ▼
                                      [PostgreSQL (reports)]

[api] ──── viem / ethers ────▶ [Base L2 — Escrow Contract]
[api] ──── viem / ethers ────▶ [Base L2 — Reputation Contract]
```

## Core Domain Model

| Entity         | Proto file                                          | Key fields                                       | Status lifecycle                                                    | Events                 |
| -------------- | --------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------- | ---------------------- |
| `User`         | `packages/schema/proto/api/v1/user.proto`           | id, email, wallet_address, status, role          | PENDING_VERIFICATION → ACTIVE → INACTIVE → BANNED                   | UserCreatedEvent       |
| `Gig`          | `packages/schema/proto/api/v1/gig.proto`            | id, client_id, title, budget, status             | DRAFT → OPEN → IN_PROGRESS → COMPLETED → CANCELLED                  | GigCreatedEvent        |
| `Milestone`    | `packages/schema/proto/api/v1/milestone.proto`      | id, gig_id, amount, status                       | PENDING → IN_PROGRESS → SUBMITTED → APPROVED → DISPUTED → CANCELLED | MilestoneApprovedEvent |
| `Submission`   | `packages/schema/proto/api/v1/submission.proto`     | id, milestone_id, freelancer_id, repo_url, files | PENDING → REVIEWED → ACCEPTED → REJECTED                            | SubmissionCreatedEvent |
| `Portfolio`    | `packages/schema/proto/api/v1/portfolio.proto`      | id, user_id, items, badge_token_ids              | —                                                                   | —                      |
| `ReviewReport` | `packages/schema/proto/ai_reviewer/v1/report.proto` | id, submission_id, verdict, summary, score       | PENDING → COMPLETED → FAILED                                        | ReviewCompletedEvent   |
| `Escrow`       | `packages/schema/proto/contracts/v1/escrow.proto`   | contract_address, gig_id, amount, status         | LOCKED → RELEASED → DISPUTED → REFUNDED                             | EscrowReleasedEvent    |

## Technology Stack

| Layer           | Technology                                      | Reason                                                                                      |
| --------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Frontend        | TypeScript + Next.js 14                         | SSR for gig discovery SEO; App Router + wagmi for wallet integration; fast iteration        |
| API             | Python 3.12 + FastAPI                           | Async HTTP; pydantic for validation; excellent for LLM-adjacent services; uv for deps       |
| AI Reviewer     | Python 3.12 + Celery + Agno                     | Celery for reliable background task queue; Agno for Claude agent orchestration              |
| Smart Contracts | Solidity + Foundry                              | Foundry is the fastest, most reliable Solidity testing framework; Base L2 is EVM-compatible |
| Primary DB      | PostgreSQL 17                                   | ACID guarantees for financial data; JSONB for flexible metadata; mature SQLAlchemy support  |
| Queue           | Redis + Celery                                  | Lightweight; sufficient for current volume; native Python integration; easy local dev       |
| Infra           | Docker Compose (local) + AWS ECS Fargate (prod) | No k8s ops overhead; per-service scaling; managed containers                                |
| Schema          | Protobuf + buf                                  | Language-agnostic schema-first type system shared across Python, TypeScript, Go             |
| Blockchain      | Base L2 (Coinbase L2 on Ethereum)               | Low gas fees; EVM-compatible; Coinbase wallet integration; growing ecosystem                |

## Infrastructure

- **Local**: `infra/docker-compose.yml` — PostgreSQL, Redis, and per-service stubs
- **Production** (planned): AWS ECS Fargate; RDS PostgreSQL; ElastiCache Redis; S3 for file uploads; Secrets Manager for credentials
- **Blockchain**: Base L2 mainnet (production), Base Sepolia testnet (staging/dev)
- All services share a single PostgreSQL instance in local dev (separate schemas per service in production)

## Auth Strategy

- **FE→BE**: JWT Bearer tokens (`Authorization: Bearer <token>`), verified with `JWT_SECRET`
- **BE↔BE**: API Key (`X-API-Key: <key>`), matched against `API_KEY` env var
- **Wallet auth**: SIWE (Sign-In with Ethereum) — user signs nonce, API verifies with `eth_account`, issues JWT
- **Email auth**: bcrypt-hashed password, verified at login, JWT issued on success
- Token expiry: 3600 seconds (1 hour), configurable via `JWT_EXPIRY_SECONDS`
- Exempt paths: `GET /health`, `GET /metrics` (explicitly allowlisted)

## Scaling & Risk

| Risk                                          | Likelihood | Impact   | Mitigation                                                                |
| --------------------------------------------- | ---------- | -------- | ------------------------------------------------------------------------- |
| Smart contract bug locking funds              | Low        | Critical | Foundry fuzz testing; audit before mainnet; upgradeable proxy pattern     |
| AI reviewer unavailable blocking fund release | Medium     | High     | Fallback to manual client approval; retry queue with exponential backoff  |
| PostgreSQL single point of failure            | Low        | High     | RDS Multi-AZ in production; PgBouncer connection pooling                  |
| Base L2 congestion / high gas                 | Low        | Medium   | Gas estimation before tx; retry with higher gas; display estimate to user |

**Expected peak load**: 1,000 concurrent users, 100 gig activations/day, 50 AI review tasks/hour
**First bottleneck under load**: AI reviewer queue depth (Celery workers + Anthropic API rate limits)

## Architectural Constraints

- All data types defined in `packages/schema/proto/` before service code
- No direct DB access across service boundaries — only HTTP or queue
- All services must expose `GET /health` and `GET /metrics`
- Auth middleware is first in the middleware chain on all services
- Smart contract interactions go through the `api` service only — other services never call contracts directly
- SIWE nonces are single-use — invalidated immediately after successful verification

## Key ADRs

| ADR                                         | Decision                                                                | Status   |
| ------------------------------------------- | ----------------------------------------------------------------------- | -------- |
| [0001](docs/adr/0001-monorepo-structure.md) | Monorepo with per-service isolation                                     | Accepted |
| [0002](docs/adr/0002-tech-stack.md)         | Primary tech stack choices (Python/FastAPI, PostgreSQL, Redis, Base L2) | Accepted |
