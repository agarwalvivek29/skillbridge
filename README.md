# SkillBridge

> AI-Powered Freelance Platform with Smart Contract Escrow.
> Freelancers and clients transact with confidence — payment guaranteed by smart contracts on Base L2, quality verified by AI — without platform lock-in or 20% fees.

---

## What's in This Repository

Full-stack monorepo with spec-driven, agentic development guardrails.

```
apps/          Frontend applications (TypeScript)
services/      Backend microservices (Python, TypeScript)
packages/      Shared libraries (schema/proto)
infra/         Local dev infrastructure (docker-compose)
docs/          Specs, ADRs, and conventions
scripts/       Scaffold and utility scripts
```

---

## Services

| Service | Language | Responsibility |
|---|---|---|
| `web` | TypeScript / Next.js 14 | All UI — gig board, profiles, workspace, wallet |
| `api` | Python / FastAPI | Users, Gigs, Milestones, Submissions, Portfolio, Disputes |
| `ai-reviewer` | Python / Celery | Code analysis, requirement parsing, verification reports (Claude Sonnet 4.6) |
| `contracts` | Solidity | EscrowFactory, GigEscrow on Base L2 |

---

## Getting Started

See [docs/ONBOARDING.md](docs/ONBOARDING.md) for the full setup guide.

**Quick start:**

```bash
# 1. Make scripts executable
chmod +x scripts/*.sh

# 2. Install git hooks
npm install

# 3. Start local infrastructure
docker compose -f infra/docker-compose.yml up -d

# 4. Create a new service
./scripts/new-service.sh
```

**Using agent orchestrator (ao):**

```bash
cp agent-orchestrator.yaml.example agent-orchestrator.yaml
# Fill in repo and path, then:

ao init
ao start
ao spawn skillbridge #42
ao status
```

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | TypeScript + Next.js 14 + wagmi/viem |
| Backend | Python + FastAPI |
| AI Worker | Python + Celery + Claude Sonnet 4.6 |
| Blockchain | Solidity on Base L2 (Foundry) |
| Database | PostgreSQL |
| Queue | Redis + Celery |
| Storage | AWS S3 |
| Infra | Docker Compose (local) |

---

## The Rules

All contributors (human and AI) follow the same rules:

- **[Core Rules](docs/CORE_RULES.md)** — The binding rules for this repository
- **[Conventions](docs/CONVENTIONS.md)** — Language-specific coding standards
- **[ADR Process](docs/adr/README.md)** — How architectural decisions are made and recorded

**The short version:**
1. Open a GitHub Issue before starting any work
2. Write a spec in `docs/specs/` before writing any feature code
3. Create an ADR before making architectural decisions
4. Get a plan approved before implementing non-trivial changes
5. All commits follow [Conventional Commits](https://www.conventionalcommits.org/)
6. All changes go through a PR — no direct pushes to `main`

---

## For AI Agents

- **Claude Code**: Read [CLAUDE.md](CLAUDE.md) first
- **Other AI tools**: Read [AGENTS.md](AGENTS.md) first
- **Working in a service**: Read `services/[name]/AGENTS.md` before touching any code

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for full system design, data flow, and domain model.

Key architectural decisions in [docs/adr/](docs/adr/):

| ADR | Decision | Status |
|---|---|---|
| [0001](docs/adr/0001-monorepo-structure.md) | Monorepo with per-service isolation | Accepted |
| [0002](docs/adr/0002-tech-stack.md) | Core tech stack: FastAPI, Base L2, PostgreSQL, Redis+Celery | Accepted |

---

## Contributing

1. Find or create a GitHub Issue
2. Write a spec: `docs/specs/[ISSUE-NUMBER]-[name].md`
3. Create an ADR if needed
4. Branch: `git checkout -b feat/[ISSUE-NUMBER]-[desc]`
5. Implement following [docs/CONVENTIONS.md](docs/CONVENTIONS.md)
6. Open a PR using the PR template
