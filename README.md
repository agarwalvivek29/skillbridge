# SkillBridge

**AI-Powered Freelance Platform with Smart Contract Escrow on Solana**

Freelancers and clients transact with confidence — payment guaranteed by on-chain escrow, quality verified by AI code review — without platform lock-in or 20% fees.

<p align="center">
  <img src="https://img.shields.io/badge/Solana-Devnet-blueviolet?logo=solana" alt="Solana Devnet" />
  <img src="https://img.shields.io/badge/Next.js-14-black?logo=nextdotjs" alt="Next.js 14" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Anchor-0.30-blue?logo=rust" alt="Anchor" />
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License" />
  <br/>
  <a href="https://explorer.solana.com/address/3X7iYXhNtwX6QH8Bf6dKgQTEyVkvyHgKLGhozzTD4suo?cluster=devnet">
    <img src="https://img.shields.io/badge/Escrow_Program-3X7iYX...D4suo-9945FF?logo=solana&logoColor=white" alt="Escrow Program" />
  </a>
</p>

---

## The Problem

The $582B gig economy runs on distrust. 71% of freelancers have experienced payment issues; 48% of clients have had contractors underdeliver. Existing platforms charge 20% fees, have broken dispute systems, and no objective quality signal.

## The Solution

SkillBridge locks funds in Solana smart contracts and uses AI (Claude) to verify deliverable quality — making trust automatic, not platform-dependent.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   CLIENT        │     │   ESCROW        │     │   FREELANCER    │     │   AI REVIEWER   │     │   SETTLEMENT    │
│                 │     │                 │     │                 │     │                 │     │                 │
│  Create gig     │────>│  Funds locked   │────>│  Submit work    │────>│  Analyze code   │────>│  Funds released │
│  + milestones   │     │  on Solana PDA  │     │  per milestone  │     │  vs criteria    │     │  to freelancer  │
│  + criteria     │     │  (SOL / USDC)   │     │  (repo + files) │     │  (Claude)       │     │  on-chain       │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └────────┬────────┘     └─────────────────┘
                                                                                 │
                                                                        ┌────────┴─────────┐
                                                                        │  PASS ──> Auto   │
                                                                        │          approve │
                                                                        │  FAIL ──> Client │
                                                                        │          reviews │
                                                                        └──────────────────┘
```

---

## Features

| Feature             | Status  | Description                                                                             |
| ------------------- | ------- | --------------------------------------------------------------------------------------- |
| Wallet Auth         | Live    | Solana wallet sign-in (Phantom, Solflare) with Ed25519 signature verification           |
| Email Linking       | Live    | Two-step onboarding: wallet connect then email + password                               |
| Gig Creation        | Live    | Multi-milestone gigs with acceptance criteria and deadline                              |
| Escrow Funding      | Live    | Deposit SOL/USDC to on-chain escrow PDA via Anchor program                              |
| Gig Discovery       | Live    | Browse, search, filter gigs by category, skills, budget                                 |
| Proposals           | Live    | Freelancers submit proposals, clients accept/reject                                     |
| Portfolio           | Live    | Showcase projects with URL previews, GitHub cards, verified delivery badges             |
| Dashboard           | Live    | Role-specific views for clients (gig management) and freelancers (earnings, milestones) |
| Notifications       | Live    | In-app notification system with read/unread tracking                                    |
| AI Code Review      | Planned | Claude analyzes submissions against acceptance criteria                                 |
| Dispute Resolution  | Planned | AI evidence + community arbitration                                                     |
| On-chain Reputation | Planned | Verifiable track record on Solana                                                       |
| Ratings & Reviews   | Planned | Blind mutual ratings with tag-based feedback                                            |

---

## Tech Stack

| Layer               | Technology                                                  |
| ------------------- | ----------------------------------------------------------- |
| **Frontend**        | Next.js 14, TypeScript, Tailwind CSS, Solana Wallet Adapter |
| **Backend**         | Python 3.12, FastAPI, SQLAlchemy (async), Alembic           |
| **Smart Contracts** | Rust, Anchor 0.30, deployed to Solana Devnet                |
| **Database**        | PostgreSQL 17                                               |
| **Queue**           | Redis + Celery                                              |
| **AI**              | Claude API (Anthropic)                                      |
| **Schema**          | Protocol Buffers (buf) with Go/Python/TS codegen            |
| **Storage**         | AWS S3 (presigned uploads)                                  |

---

## Quick Start

### Prerequisites

- Node.js 20+, pnpm 10+
- Python 3.12+, uv
- Docker (for PostgreSQL + Redis)
- Solana CLI (optional, for contract deployment)

### 1. Clone and install

```bash
git clone https://github.com/agarwalvivek29/skillbridge.git
cd skillbridge
npm install          # git hooks
```

### 2. Start infrastructure

```bash
docker compose -f infra/docker-compose.yml up -d postgres redis
```

### 3. Set up the API

```bash
cd services/api
cp .env.example .env    # edit with your values
uv sync --extra dev     # install dependencies

# Run migrations
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/skillbridge" \
  uv run alembic upgrade head

# Start dev server
uv run uvicorn src.main:app --reload --port 8000
```

### 4. Set up the frontend

```bash
cd apps/web
cp .env.example .env.local
pnpm install
pnpm dev                # http://localhost:3000
```

### 5. Run tests

```bash
cd services/api
uv run pytest -v        # 308+ tests
```

---

## Architecture

```
                    +------------------+
                    |   Next.js 14     |
                    |   (apps/web)     |
                    +--------+---------+
                             |
                    REST API (JSON)
                             |
                    +--------+---------+
                    |    FastAPI       |
                    |  (services/api)  |
                    +--+----+------+--+
                       |    |      |
              +--------+  ++-+  +-+--------+
              |  PostgreSQL  | |   Redis    |
              |              | |  (Celery)  |
              +--------------+ +-----------+
                             |
                    +--------+---------+
                    |  Solana Devnet   |
                    |  Anchor Escrow   |
                    |  (gig_escrow)    |
                    +------------------+
```

**Deployed Contract:** [`3X7iYXhNtwX6QH8Bf6dKgQTEyVkvyHgKLGhozzTD4suo`](https://explorer.solana.com/address/3X7iYXhNtwX6QH8Bf6dKgQTEyVkvyHgKLGhozzTD4suo?cluster=devnet) on Solana Devnet

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design, data flow, and domain model.

---

## Project Structure

```
skillbridge/
  apps/
    web/                  Next.js 14 frontend
  services/
    api/                  FastAPI backend (Python 3.12)
    contracts/            Anchor/Rust smart contracts
    ai-reviewer/          AI code review worker (planned)
  packages/
    schema/
      proto/              Protobuf definitions (source of truth)
      generated/          Go, Python, TypeScript bindings
  infra/                  Docker Compose (PostgreSQL, Redis)
  docs/
    adr/                  Architecture Decision Records
    specs/                Feature specifications
    CORE_RULES.md         Development rules
```

---

## Key Design Decisions

| ADR                                         | Decision                                 |
| ------------------------------------------- | ---------------------------------------- |
| [0001](docs/adr/0001-monorepo-structure.md) | Monorepo with per-service isolation      |
| [0002](docs/adr/0002-tech-stack.md)         | FastAPI + Solana + PostgreSQL + Redis    |
| [0003](docs/adr/0003-solana-migration.md)   | Migrated from Ethereum Base L2 to Solana |

---

## Development Rules

All contributors (human and AI) follow the same rules. Key principles:

- **Proto is the single source of truth** for field names across all layers
- **Use enums, not strings** — `domain/enums.py` defines all status/role/currency constants
- **Spec before code** — write `docs/specs/[ISSUE]-*.md` before implementing features
- **ADR before architecture** — document decisions in `docs/adr/`
- **Conventional commits** — `type(scope): description`

See [docs/CORE_RULES.md](docs/CORE_RULES.md) for the full ruleset.

---

## Contributing

1. Find or create a [GitHub Issue](https://github.com/agarwalvivek29/skillbridge/issues)
2. Write a spec: `docs/specs/[ISSUE-NUMBER]-[name].md`
3. Create an ADR if making architectural decisions
4. Branch: `git checkout -b feat/[ISSUE-NUMBER]-[desc]`
5. Follow [CORE_RULES.md](docs/CORE_RULES.md) and [CONVENTIONS.md](docs/CONVENTIONS.md)
6. Open a PR — all changes go through review

---

## For AI Agents

- **Claude Code**: Read [CLAUDE.md](CLAUDE.md) first
- **Other AI tools**: Read the service-specific `AGENTS.md` before touching any code
- **Schema changes**: Update proto first, regenerate, then implement

---

## License

MIT
