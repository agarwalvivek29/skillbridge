# Architecture — SkillBridge

> The technical source of truth for this project.
> Update this document when architecture changes. Reference it in every ADR.

## System Overview

SkillBridge is a freelance marketplace where trust is enforced by technology, not intermediaries. The system has four layers: a Next.js frontend (web), a FastAPI backend (api), an async Python AI worker (ai-reviewer), and Solidity smart contracts on Base L2 (contracts). Funds are locked in on-chain escrow at gig creation and released automatically when milestones are approved. AI-powered code review (Phase 2) will make approval automatic for qualifying deliverables. All mutable state lives in PostgreSQL; files in S3; background jobs flow through a Redis/Celery queue.

## Service Map

| Service | Language | Type | Responsibility | Primary DB | Queue |
|---|---|---|---|---|---|
| `web` | TypeScript | Next.js App | All UI: gig board, profile/portfolio, workspace, wallet, disputes | — | — |
| `api` | Python | REST API (FastAPI) | Users, Gigs, Milestones, Submissions, Portfolio, Disputes, on-chain event relay | PostgreSQL | Celery producer |
| `ai-reviewer` | Python | Async Worker (Celery) | Requirement parsing, code analysis (Claude Sonnet 4.6), verification report generation | PostgreSQL (writes) | Celery consumer |
| `contracts` | Solidity | Smart Contracts (Base L2) | EscrowFactory, GigEscrow, on-chain fund lock/release | — | — |

## Data Flow

```
[Browser]
    │  wagmi/viem (wallet tx signed client-side)
    │  REST/fetch (app data)
    ▼
[web — Next.js]
    │  REST (JSON)
    ▼
[api — FastAPI] ──────────────────────────────────▶ [PostgreSQL]
    │                                               [S3 — submissions, portfolio files]
    │  enqueue review job (on submission)
    ▼
[Redis]
    │
    ▼
[ai-reviewer — Celery Worker]
    │  clone repo / read files
    ▼
[Subprocess / sandbox]
    │  call Claude API (claude-sonnet-4-6)
    │  run linters, parse criteria
    │  write ReviewReport to PostgreSQL
    ▼
[PostgreSQL] ◀── api polls report status, notifies web via SSE
    │
    │  on approval (manual v1 / AI verdict v2)
    ▼
[api] ── calls contract ──▶ [Base L2 — GigEscrow.completeMilestone()]
                                │
                                ▼
                         [Freelancer wallet receives ETH/USDC]
```

## Core Domain Model

| Entity | Proto file | Key fields | Status lifecycle | Events |
|---|---|---|---|---|
| `User` | `packages/schema/proto/api/v1/user.proto` | id, wallet_address, email, role | ACTIVE / SUSPENDED | UserCreated |
| `Gig` | `packages/schema/proto/api/v1/gig.proto` | id, client_id, freelancer_id, title, total_amount, contract_address | DRAFT → OPEN → IN_PROGRESS → COMPLETED / CANCELLED | GigCreated, GigFunded, GigCompleted |
| `Milestone` | `packages/schema/proto/api/v1/milestone.proto` | id, gig_id, description, amount, criteria, order | PENDING → SUBMITTED → UNDER_REVIEW → APPROVED / REVISION_REQUESTED | MilestoneSubmitted, MilestoneApproved |
| `Submission` | `packages/schema/proto/api/v1/submission.proto` | id, milestone_id, freelancer_id, repo_url, files[], notes | PENDING → UNDER_REVIEW → APPROVED / REJECTED | SubmissionCreated, SubmissionReviewed |
| `ReviewReport` | `packages/schema/proto/ai_reviewer/v1/report.proto` | id, submission_id, score, findings[], verdict, model_version | PENDING → COMPLETE | ReviewCompleted |
| `EscrowContract` | `packages/schema/proto/contracts/v1/escrow.proto` | id, gig_id, chain_address, network, total_amount, released_amount | DEPLOYING → FUNDED → PARTIALLY_RELEASED → SETTLED / DISPUTED | EscrowFunded, FundsReleased |
| `PortfolioItem` | `packages/schema/proto/api/v1/portfolio.proto` | id, user_id, title, description, files[], external_url, verified_gig_id | — | — |

## Technology Stack

| Layer | Technology | Reason |
|---|---|---|
| Frontend | TypeScript + Next.js 14 | SSR for gig board SEO; wagmi/viem for wallet integration; hybrid SSR+SPA model |
| Backend API | Python + FastAPI | Async-native, plays well with AI/ML libs, strong typing with Pydantic, matches ai-reviewer language |
| AI Worker | Python + Celery + Claude Sonnet 4.6 | Long-running sandboxed jobs; same language as api; Claude API for code analysis |
| Blockchain | Solidity on Base L2 | Low gas fees (~$0.01/tx), EVM-compatible, Coinbase ecosystem, good tooling (Foundry/Hardhat) |
| Primary DB | PostgreSQL | Relational data with clear FK relationships; ACID guarantees for financial data; JSONB for flexible criteria/findings |
| Job Queue | Redis + Celery | Sufficient for MVP-scale review jobs; simple retry/backoff; no need for Kafka's operational overhead yet |
| File Storage | AWS S3 | Submissions and portfolio assets; presigned URLs for direct browser upload |
| Infra (local) | Docker Compose | MVP/portfolio — no ECS complexity until product-market fit |

## Infrastructure

- **Local dev**: Docker Compose with services: `web`, `api`, `ai-reviewer`, `postgres`, `redis`
- **Blockchain**: Base L2 (testnet: Base Sepolia for dev, Base Mainnet for prod)
- **File storage**: S3 bucket per environment (`skillbridge-dev`, `skillbridge-prod`)
- **AI**: Anthropic API (external) — `ANTHROPIC_API_KEY` in env

## Auth Strategy

- **FE → BE**: JWT Bearer tokens (`Authorization: Bearer <token>`), verified with `JWT_SECRET`
- **BE ↔ BE**: API Key (`X-API-Key: <key>`), matched against `API_KEY` env var
- **Wallet auth**: Sign-in with Ethereum (SIWE) — wallet signs a nonce, api verifies signature, issues JWT
- Token expiry: controlled by `JWT_EXPIRY_SECONDS`
- Exempt paths: `GET /health`, `GET /metrics`

## Scaling & Risk

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Smart contract bug locks funds permanently | Low | Critical | Foundry tests with fuzzing; no upgradeable proxies in v1; manual emergency withdrawal by client+freelancer multisig |
| AI reviewer false positive (passes bad code) | Medium | High | Human override always available in v1; AI is advisory not binding until v2 |
| AI reviewer false negative (blocks good code) | Medium | Medium | Score threshold tunable; client can override AI verdict |
| PostgreSQL as single point of failure | Low | High | Daily automated backups; connection pooling (pgBouncer) before scaling |
| Base L2 downtime or high gas spike | Low | Medium | Retry queue for on-chain calls; show estimated gas before tx confirmation |

**Expected peak load (MVP)**: 100 concurrent users, <10 review jobs/hour
**First bottleneck under load**: ai-reviewer worker — scale by adding Celery workers horizontally

## Architectural Constraints

- All data types defined in `packages/schema/proto/` before service code — no local type definitions for domain entities
- No direct DB access across service boundaries — ai-reviewer writes only to its own tables; api owns all reads
- All services must expose `GET /health` and `GET /metrics`
- Auth middleware is first in the middleware chain on all services
- Smart contract addresses are stored in DB and verified on-chain before any fund release call
- Never store private keys in DB or env files — wallet signing is always client-side or via hardware wallet

## Key ADRs

| ADR | Decision | Status |
|---|---|---|
| [0001](docs/adr/0001-monorepo-structure.md) | Monorepo with per-service isolation | Accepted |
| [0002](docs/adr/0002-tech-stack.md) | Core tech stack: FastAPI, Base L2, PostgreSQL, Redis+Celery | Accepted |
