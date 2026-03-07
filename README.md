# [Project Name]

> Replace this with a one-paragraph description of your project.

---

## What's in This Repository

This is a full-stack monorepo template with built-in guardrails for controlled, spec-driven, agentic development.

```
apps/          Frontend applications (TypeScript)
services/      Backend microservices (TypeScript, Python, Go, Rust)
packages/      Shared libraries and utilities
infra/         Local dev infrastructure (docker-compose) and AWS guidance
docs/          Specs, ADRs, and conventions
scripts/       Scaffold and utility scripts
```

---

## Getting Started

See [docs/ONBOARDING.md](docs/ONBOARDING.md) for the full setup guide.

**Quick start:**

```bash
# 1. Make scripts executable
chmod +x scripts/*.sh

# 2. Install git hooks
npm install

# 3. Create your first service
./scripts/new-service.sh

# 4. Start local infrastructure
docker compose -f infra/docker-compose.yml up -d
```

**Using agent orchestrator (ao):**

```bash
# Configure ao for this project
cp agent-orchestrator.yaml.example agent-orchestrator.yaml
# Fill in repo and path, then:

ao init                              # install workspace hooks
ao start                             # launch dashboard + lifecycle manager
ao spawn my-project #42              # spawn an agent on a GitHub Issue
ao batch-spawn my-project #42 #43    # spawn agents in parallel
ao status                            # watch all sessions
```

See [docs/ONBOARDING.md](docs/ONBOARDING.md#step-8-set-up-agent-orchestrator-ao--recommended) for full ao setup.

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

Key architectural decisions are recorded in [docs/adr/](docs/adr/).

| ADR | Decision | Status |
|---|---|---|
| [0001](docs/adr/0001-monorepo-structure.md) | Monorepo with per-service isolation | Accepted |

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | TypeScript, [framework] |
| Backend | TypeScript / Python / Go / Rust |
| Database | PostgreSQL, MongoDB, Redis |
| Queues | Kafka, RabbitMQ, Redis |
| Infra | AWS, Docker Compose |

---

## Contributing

1. Find or create a GitHub Issue
2. Write a spec: `docs/specs/[ISSUE-NUMBER]-[name].md`
3. Create an ADR if needed
4. Branch: `git checkout -b feat/[ISSUE-NUMBER]-[desc]`
5. Implement following [docs/CONVENTIONS.md](docs/CONVENTIONS.md)
6. Open a PR using the PR template
