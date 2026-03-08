# Architecture — SkillBridge

> The technical source of truth for this project.
> Update this document when architecture changes. Reference it in every ADR.

## System Overview

SkillBridge is a freelance marketplace where trust is enforced by technology, not intermediaries. The system has four layers: a Next.js frontend (web), a FastAPI backend (api), a self-hosted GitHub App AI reviewer (ai-reviewer), and Solidity smart contracts on Base L2 (contracts). Funds are locked in on-chain escrow at gig creation and released automatically when milestones are approved. AI-powered code review triggers on @openreview mention in PRs and delivers verdicts via GitHub webhook. All mutable state lives in PostgreSQL; files in S3.

## Service Map

| Service       | Language            | Type                                         | Responsibility                                                                                                                                                                                                          | Primary DB          | Queue           |
| ------------- | ------------------- | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- | --------------- |
| `web`         | TypeScript          | Next.js App                                  | All UI: gig board, profile/portfolio, workspace, wallet, disputes                                                                                                                                                       | —                   | —               |
| `api`         | Python              | REST API (FastAPI)                           | Users, Gigs, Milestones, Submissions, Portfolio, Disputes, on-chain event relay                                                                                                                                         | PostgreSQL          | Celery producer |
| `ai-reviewer` | TypeScript / Python | GitHub App (Next.js) + Async Worker (Celery) | Self-hosted openreview instance; reviews PRs with Claude Sonnet 4.6 on @openreview mention; verdict delivered via pull_request_review webhook; also: requirement parsing, code analysis, verification report generation | PostgreSQL (writes) | Celery consumer |
| `contracts`   | Solidity            | Smart Contracts (Base L2)                    | EscrowFactory, GigEscrow, on-chain fund lock/release                                                                                                                                                                    | —                   | —               |

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

| Entity           | Proto file                                                              | Key fields                                                                                                                         | Status lifecycle                                                              | Events                                                         |
| ---------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `User`           | `api/v1/user.proto`                                                     | id, wallet_address, email, role (FREELANCER\|CLIENT\|ADMIN), skills[], hourly_rate_wei                                             | ACTIVE / SUSPENDED                                                            | UserCreated                                                    |
| `Gig`            | `api/v1/gig.proto`                                                      | id, client_id, freelancer_id, title, total_amount, currency (ETH\|USDC), token_address, contract_address, deadline                 | DRAFT → OPEN → IN_PROGRESS → COMPLETED / CANCELLED                            | GigCreated, GigFunded, GigCompleted                            |
| `Milestone`      | `api/v1/milestone.proto`                                                | id, gig_id, description, amount, criteria, order, due_date, revision_count                                                         | PENDING → SUBMITTED → UNDER_REVIEW → APPROVED / REVISION_REQUESTED / DISPUTED | MilestoneSubmitted, MilestoneApproved, MilestoneDisputed       |
| `Submission`     | `api/v1/submission.proto`                                               | id, milestone_id, freelancer_id, repo_url, files[], revision_number, previous_submission_id                                        | PENDING → UNDER_REVIEW → APPROVED / REJECTED                                  | SubmissionCreated, SubmissionReviewed                          |
| `ReviewReport`   | `ai_reviewer/v1/report.proto` (also stored in DB as openreview verdict) | id, submission_id, score (0 or 100), findings[], verdict (PASS\|FAIL), body (raw review text), model_version                       | PENDING → COMPLETE (written on webhook receipt)                               | ReviewCompleted                                                |
| `EscrowContract` | `contracts/v1/escrow.proto`                                             | id, gig_id, chain_address, network, total_amount, token_address, platform_fee_basis_points (500=5%), released_amount               | DEPLOYING → FUNDED → PARTIALLY_RELEASED → SETTLED / DISPUTED                  | EscrowFunded, FundsReleased (net_amount + platform_fee_amount) |
| `PortfolioItem`  | `api/v1/portfolio.proto`                                                | id, user_id, title, description, files[], external_url, verified_gig_id                                                            | —                                                                             | —                                                              |
| `AuthNonce`      | `api/v1/auth.proto`                                                     | wallet_address, nonce, expires_at                                                                                                  | ephemeral (deleted post-auth)                                                 | —                                                              |
| `Proposal`       | `api/v1/proposal.proto`                                                 | id, gig_id, freelancer_id, cover_letter, estimated_days                                                                            | PENDING → ACCEPTED / REJECTED / WITHDRAWN                                     | ProposalSubmitted, ProposalAccepted                            |
| `Dispute`        | `api/v1/dispute.proto`                                                  | id, milestone_id, gig_id, raised_by_user_id, reason, ai_evidence_summary, resolution, freelancer_split_amount                      | OPEN → DISCUSSION → ARBITRATION → RESOLVED                                    | DisputeRaised, DisputeResolved                                 |
| `DisputeMessage` | `api/v1/dispute.proto`                                                  | id, dispute_id, user_id, content                                                                                                   | —                                                                             | —                                                              |
| `Reputation`     | `api/v1/reputation.proto`                                               | id, user_id, wallet_address, gigs_completed, gigs_as_client, total_earned, average_ai_score, dispute_rate_pct, average_rating_x100 | DB cache, synced from chain                                                   | —                                                              |
| `Review`         | `api/v1/review.proto`                                                   | id, gig_id, reviewer_id, reviewee_id, rating (1–5), comment, is_visible                                                            | hidden until both submit or 7-day window closes                               | ReviewSubmitted                                                |
| `Notification`   | `api/v1/notification.proto`                                             | id, user_id, type (14 types), payload_json, read_at                                                                                | unread (read_at null) → read                                                  | —                                                              |

> All proto paths are relative to `packages/schema/proto/`. No dual roles — a user is either FREELANCER or CLIENT (or ADMIN).

## Technology Stack

| Layer         | Technology                          | Reason                                                                                                                |
| ------------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Frontend      | TypeScript + Next.js 14             | SSR for gig board SEO; wagmi/viem for wallet integration; hybrid SSR+SPA model                                        |
| Backend API   | Python + FastAPI                    | Async-native, plays well with AI/ML libs, strong typing with Pydantic, matches ai-reviewer language                   |
| AI Reviewer   | TypeScript + Next.js (openreview)   | Self-hosted GitHub App; Claude Sonnet 4.6 via openreview; verdict relayed to api via GitHub webhook                   |
| AI Worker     | Python + Celery + Claude Sonnet 4.6 | Long-running sandboxed jobs; same language as api; Claude API for code analysis                                       |
| Blockchain    | Solidity on Base L2                 | Low gas fees (~$0.01/tx), EVM-compatible, Coinbase ecosystem, good tooling (Foundry/Hardhat)                          |
| Primary DB    | PostgreSQL                          | Relational data with clear FK relationships; ACID guarantees for financial data; JSONB for flexible criteria/findings |
| Job Queue     | Redis + Celery                      | Sufficient for MVP-scale review jobs; simple retry/backoff; no need for Kafka's operational overhead yet              |
| File Storage  | AWS S3                              | Submissions and portfolio assets; presigned URLs for direct browser upload                                            |
| Infra (local) | Docker Compose                      | MVP/portfolio — no ECS complexity until product-market fit                                                            |

## Infrastructure

- **Local dev**: Docker Compose with services: `web`, `api`, `postgres`, `redis`; `ai-reviewer` — Self-hosted openreview (Next.js) — deploy to Vercel or run locally with bun dev
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

| Risk                                          | Likelihood | Impact   | Mitigation                                                                                                          |
| --------------------------------------------- | ---------- | -------- | ------------------------------------------------------------------------------------------------------------------- |
| Smart contract bug locks funds permanently    | Low        | Critical | Foundry tests with fuzzing; no upgradeable proxies in v1; manual emergency withdrawal by client+freelancer multisig |
| AI reviewer false positive (passes bad code)  | Medium     | High     | Human override always available in v1; AI is advisory not binding until v2                                          |
| AI reviewer false negative (blocks good code) | Medium     | Medium   | Score threshold tunable; client can override AI verdict                                                             |
| PostgreSQL as single point of failure         | Low        | High     | Daily automated backups; connection pooling (pgBouncer) before scaling                                              |
| Base L2 downtime or high gas spike            | Low        | Medium   | Retry queue for on-chain calls; show estimated gas before tx confirmation                                           |

**Expected peak load (MVP)**: 100 concurrent users, <10 review jobs/hour
**First bottleneck under load**: api webhook handler volume — scale api horizontally; openreview scales via Vercel

## Architectural Constraints

- All data types defined in `packages/schema/proto/` before service code — no local type definitions for domain entities
- No direct DB access across service boundaries — ai-reviewer writes only to its own tables; api owns all reads
- All services must expose `GET /health` and `GET /metrics`
- Auth middleware is first in the middleware chain on all services
- Smart contract addresses are stored in DB and verified on-chain before any fund release call
- Never store private keys in DB or env files — wallet signing is always client-side or via hardware wallet

## Key ADRs

| ADR                                         | Decision                                                    | Status   |
| ------------------------------------------- | ----------------------------------------------------------- | -------- |
| [0001](docs/adr/0001-monorepo-structure.md) | Monorepo with per-service isolation                         | Accepted |
| [0002](docs/adr/0002-tech-stack.md)         | Core tech stack: FastAPI, Base L2, PostgreSQL, Redis+Celery | Accepted |
