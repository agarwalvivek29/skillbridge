# 0002 Core Tech Stack

**Date**: 2026-03-07
**Status**: Accepted
**Deciders**: agarwalvivek29
**Issue**: Bootstrap

## Context

SkillBridge requires four distinct technical layers:

1. A user-facing web application with wallet integration
2. A backend API managing business entities and on-chain interactions
3. An async AI worker for code review jobs
4. Smart contracts for trustless escrow on a low-cost EVM chain

The stack decisions need to be made upfront because they affect every service's tooling, dependencies, and generated type imports from `packages/schema`.

## Decision

### Frontend: Next.js 14 (TypeScript) with wagmi/viem

We will use Next.js 14 with the App Router, TypeScript, and Tailwind CSS. wagmi/viem handles wallet connection and on-chain reads/writes from the browser.

**Rationale**: SSR for gig board SEO; hybrid SSR+SPA for the workspace UI. wagmi/viem is the standard for React wallet integration in 2026 and has first-class Base L2 support.

### Backend API: Python + FastAPI

We will use Python 3.12 with FastAPI (async) and SQLAlchemy + Alembic for the main API service.

**Rationale**: FastAPI is async-native and produces excellent OpenAPI docs automatically. Python is the same language as `ai-reviewer`, reducing context switching. Pydantic v2 integrates directly with betterproto-generated schema types.

### AI Worker: Python + Celery + Anthropic SDK

The `ai-reviewer` service will run as a Celery worker consuming from Redis, using the Anthropic Python SDK with `claude-sonnet-4-6`.

**Rationale**: AI review jobs are long-running (clone repo, run linters, call Claude API — up to 5 minutes). Decoupling from the API via a queue prevents blocking the main API process. Celery + Redis is sufficient for MVP-scale job volume and is operationally simple. Using a dedicated worker service means we can scale it independently from the API.

### Blockchain: Solidity on Base L2 (Foundry)

> **Note**: The blockchain decision in this ADR has been superseded by [ADR 0003](./0003-solana-migration.md). The project now uses Solana (Rust/Anchor) instead of Base L2 (Solidity/Foundry).

We will write contracts in Solidity ^0.8.24 and use Foundry for testing and deployment. Base L2 is the target network.

**Rationale**: Base L2 provides gas costs ~100x lower than Ethereum mainnet (~$0.01/tx), is EVM-compatible (standard Solidity tooling works), and is backed by Coinbase — aligned with the target user base of crypto-native freelancers. Foundry is preferred over Hardhat for its faster compilation, native fuzz testing, and Solidity-native test writing.

### Primary Database: PostgreSQL

All services share a single PostgreSQL 17 instance in local dev, with separate schemas or tables per service. Each service manages its own migrations via Alembic.

**Rationale**: All SkillBridge data is relational (gigs → milestones → submissions → reports). ACID guarantees are critical for financial data (escrow amounts, payment records). JSONB provides flexibility for acceptance criteria and review findings without schema rigidity.

### Job Queue: Redis + Celery

We will use Redis as both the Celery broker and result backend.

**Rationale**: Review jobs are low-volume at MVP scale (<10/hour). Kafka would add operational complexity (ZooKeeper or KRaft, partition management) that isn't justified. Redis + Celery provides reliable job queuing, retry logic, and result storage with minimal ops overhead. This can be replaced with Kafka if job volume exceeds Redis capacity.

### File Storage: AWS S3

Submission files and portfolio assets are stored in S3 with presigned URLs for direct browser upload.

**Rationale**: Standard, cost-effective, durable object storage. Presigned URLs avoid routing large file uploads through the API server.

## Consequences

### Positive

- Python shared between `api` and `ai-reviewer` reduces library duplication
- FastAPI + Pydantic integrates naturally with betterproto schema types
- Foundry's fuzz testing catches edge cases in financial contract logic
- Base L2's low gas makes escrow economically viable for small gigs ($100+)
- Celery worker can be scaled horizontally without touching the API

### Negative

- Python is slower than Go/Rust for raw throughput — acceptable at MVP scale
- No native TypeScript types for smart contract ABIs (use viem's ABI typing instead)
- Celery requires Redis to be available — single dependency for job queue reliability

### Neutral

- betterproto generates Python dataclasses, not Pydantic models directly — requires a small compatibility shim
- Base L2 requires users to bridge ETH from mainnet or buy directly on Coinbase

## Alternatives Considered

### TypeScript for API instead of Python

TypeScript would provide end-to-end type safety from frontend to backend. Rejected because: the `ai-reviewer` worker requires Python for AI library compatibility (Anthropic SDK, subprocess management), and running two languages adds more cognitive overhead than the type safety benefit at this scale.

### Hardhat instead of Foundry

Hardhat is more widely used and has a larger plugin ecosystem. Rejected because: Foundry's native fuzz testing is critical for financial contract correctness, and Foundry compilation is significantly faster. The team does not need Hardhat's JS/TS test compatibility.

### Kafka instead of Redis+Celery

Kafka provides event replay, multiple independent consumers, and higher throughput. Rejected because: at MVP scale, there is only one consumer (ai-reviewer) and no replay requirement. The operational overhead of Kafka (broker management, partition tuning) is not justified until job volume exceeds ~1000/hour. This decision should be revisited at that point.

### Polygon or Arbitrum instead of Base L2

Both are valid EVM L2s with low fees. Base is preferred because: Coinbase integration aligns with the target user base (crypto-native but mainstream-adjacent), Coinbase Smart Wallet provides the best onboarding UX for non-crypto users, and Base has strong EVM tooling support.
