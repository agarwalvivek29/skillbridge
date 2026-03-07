# 0002 — Primary Tech Stack

**Date**: 2026-03-07
**Status**: Accepted
**Deciders**: Project founders
**Issue**: N/A (bootstrap)

---

## Context

SkillBridge is a freelance marketplace with smart contract escrow on Base L2 and an AI quality verification layer. We need to choose languages, frameworks, databases, queue systems, and blockchain targets for the initial v1 build.

Key constraints:

- Team is familiar with Python for backend and TypeScript for frontend
- AI reviewer service needs tight integration with the Anthropic SDK
- Financial transactions require ACID guarantees
- Smart contracts must be EVM-compatible for Base L2
- Local development must work with `docker compose up` only
- AI agents operate on this codebase — clear, opinionated choices reduce ambiguity

---

## Decision

### Backend API Service: Python 3.12 + FastAPI

We will use Python with FastAPI for the core `api` service.

- FastAPI provides async support, automatic OpenAPI docs, and pydantic integration
- Python is the natural choice given the AI reviewer also being Python
- uv for dependency management (fastest Python package manager)
- SQLAlchemy 2.0 (async) for ORM; alembic for migrations

### AI Reviewer Service: Python 3.12 + Celery + Agno

- Celery with Redis broker for reliable background task processing
- Agno framework for Claude agent orchestration (recommended in CONVENTIONS.md)
- betterproto for consuming generated schema types

### Frontend: TypeScript + Next.js 14

- App Router for SSR on gig discovery (SEO-important)
- wagmi + viem for wallet connectivity (MetaMask, Coinbase Wallet)
- TypeScript for type safety across the full stack

### Smart Contracts: Solidity + Foundry

- Foundry for testing (faster and more reliable than Hardhat)
- Base L2 as the deployment target: low gas fees, EVM-compatible, Coinbase ecosystem

### Primary Database: PostgreSQL 17

- ACID guarantees are non-negotiable for financial data (escrow amounts, balances)
- JSONB for flexible metadata (submission files list, portfolio items)
- Mature SQLAlchemy support; widely understood

### Queue: Redis + Celery

- Redis is sufficient for current expected volume (< 100 AI review tasks/hour)
- Native Celery integration with Python services
- Simpler ops than Kafka/RabbitMQ at this scale
- If volume grows beyond Redis capacity → migrate to RabbitMQ (prefer over Kafka for task queues)

### Blockchain: Base L2

- EVM-compatible (can use Solidity + Foundry unchanged)
- Low gas fees vs Ethereum mainnet
- Coinbase Wallet integration is a first-class feature
- Growing ecosystem; Coinbase brand adds user trust

### Schema: Protobuf + buf

- Language-agnostic; generates TypeScript, Python, Go bindings from one source
- Enforces schema-first discipline across services
- betterproto for Python; ts-proto for TypeScript; protoc-gen-go for Go

---

## Consequences

### Positive

- Python consistency between api and ai-reviewer services simplifies shared patterns
- FastAPI + pydantic + betterproto creates a tight schema-first pipeline in Python
- Foundry tests are significantly faster than Hardhat (Rust-based)
- Base L2 keeps gas costs low for users (critical for adoption)
- Redis simplicity reduces local dev complexity

### Negative

- Python is slower than Go/Rust for CPU-bound work (not expected to be a bottleneck)
- Celery + Redis requires careful configuration for production reliability
- Base L2 is a newer ecosystem; some tooling less mature than Ethereum mainnet

### Neutral

- Alembic migrations require discipline (append-only, always include down migrations)
- betterproto code generation adds a step to the development workflow

---

## Alternatives Considered

### TypeScript/Node.js for API

Would unify language across web and api. Rejected because:

- Python has better LLM/AI library ecosystem (Anthropic SDK, betterproto)
- Team has deeper Python expertise for backend
- FastAPI is faster to develop against than Express/Fastify for complex APIs

### Kafka for Queue

Better for high-volume event streaming and event replay. Rejected because:

- Overkill for < 100 tasks/hour; adds significant operational complexity
- Redis + Celery achieves the same goals at this scale
- Can migrate to RabbitMQ → Kafka if volume demands it

### Hardhat for Smart Contracts

More common in the ecosystem. Rejected because:

- Foundry tests run in Rust (100x faster than Hardhat's JS-based runner)
- Native Solidity tests are more maintainable than JS test scripts
- Foundry has better fuzzing support

### Polygon / Arbitrum for L2

Other EVM-compatible L2s. Rejected because:

- Base L2 has Coinbase backing (user trust, wallet integration)
- Coinbase Wallet is a primary target wallet for this platform
- Base has competitive gas fees and growing developer ecosystem
