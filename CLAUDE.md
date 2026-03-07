# CLAUDE.md — Agent Contract for Claude Code

> This file governs how Claude Code operates in this repository and all projects derived from it.
> Read this before taking **any** action.

---

## ⚠️ Bootstrap Check — Read This First

**Before anything else: does `BOOTSTRAP.md` exist in this repository?**

```bash
ls BOOTSTRAP.md 2>/dev/null && echo "EXISTS" || echo "NOT FOUND"
```

| Result | What to do |
|---|---|
| `EXISTS` | **Stop.** Read `BOOTSTRAP.md` and complete onboarding before any other work. The project is not initialized. |
| `NOT FOUND` | Continue reading this file. The project is live. |

---

<!-- POST-BOOTSTRAP: After completing BOOTSTRAP.md and deleting it, uncomment the block below
     and delete the ⚠️ Bootstrap Check section above.

## Project Context

Read these before every session:
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — system overview, service map, data flow, tech stack, constraints
- **[PRODUCT.md](PRODUCT.md)** — product vision, target users, core features, roadmap

> **Missing file check**: If either `ARCHITECTURE.md` or `PRODUCT.md` does not exist, **stop immediately**.
> Tell the human: "Bootstrap was not completed — `ARCHITECTURE.md` and/or `PRODUCT.md` are missing.
> Please re-run the bootstrap process (restore `BOOTSTRAP.md` from git and follow it) before starting any work."
> Do not proceed with any task until both files exist.

-->

---

## Mandatory Pre-Flight Checks

Before starting any task, you MUST:

1. **Read `docs/CORE_RULES.md`** — The binding rules for this repository. No exceptions.
2. **Find the GitHub Issue** — Task context, requirements, and acceptance criteria come from the linked issue.
3. **Check for a spec** — Look in `docs/specs/` for a file matching the issue number. If none exists for a feature task, stop and create one before proceeding.
4. **Check relevant ADRs** — Scan `docs/adr/` for decisions that affect the area you're working in.
5. **Read `AGENTS.md` for the service** — If you're modifying a specific service, read its `AGENTS.md` before touching any code.
6. **Check `packages/schema/proto/`** — If your task involves any data type (entity, enum, event, request/response shape), verify it's defined in proto. If not, define it there first before writing any service code.

---

## Workflow Gates

### Gate 1: Spec Gate
- **Non-trivial features require a spec.** If `docs/specs/[ISSUE-NUMBER]-*.md` does not exist, create it using `docs/specs/TEMPLATE.md` before writing any implementation code.
- Bug fixes, dependency updates, and documentation changes are exempt.

### Gate 2: Plan Gate
- **Changes touching more than 2 files or introducing new architecture require an approved plan.**
- Use `EnterPlanMode` to explore, design, and present your plan. Do not write production code during planning.
- Exit planning only after the plan is approved by the user.

### Gate 3: ADR Gate
- **Any architectural decision requires an ADR.** See `docs/adr/README.md` for what triggers an ADR.
- Create the ADR in `docs/adr/[NNNN]-[title].md` before implementing the decision.

---

## File and Code Rules

- **Never create a new service manually.** Always use `scripts/new-service.sh`.
- **Prefer editing existing files over creating new ones.**
- **Never skip git hooks.** Do not use `--no-verify` or `--no-gpg-sign`.
- **Never commit to `main` directly.** All changes go through a PR on a feature branch.
- **Never hardcode secrets.** Use `.env` files (gitignored). Update `.env.example` with placeholder values.
- **Never modify `infra/docker-compose.yml` or AWS configs without explicit human approval.**

---

## Task Tracking Discipline

Use the built-in task system for any multi-step work:

```
TaskCreate  → when starting a complex task
TaskUpdate  → mark in_progress before beginning, completed when done
TaskList    → check for next task after completing one
```

Break large tasks into smaller, independently completable units. Never mark a task complete if tests are failing or implementation is partial.

---

## Memory Management

Maintain `.claude/memory/` to preserve context across sessions:

- `MEMORY.md` — high-level summary, always loaded (keep under 200 lines)
- Topic files (e.g., `auth.md`, `database.md`) — detailed notes linked from `MEMORY.md`

Write to memory when you discover:
- Stable architectural patterns in this repo
- Non-obvious conventions or gotchas
- Important file paths and entry points
- Solutions to recurring problems

Do NOT write: session-specific state, incomplete conclusions, or anything that duplicates `CORE_RULES.md`.

---

## Capabilities and Tools

You may use any available skills, MCP servers, and tools as needed to complete tasks. Common useful MCPs:

- `filesystem` — file operations
- `github` — issue/PR management, branch operations
- `postgres`/`mongo` — database inspection (read-only in production)
- Web search — for researching libraries and patterns

Document any MCP or tool you add to a workflow in the relevant service's `AGENTS.md`.

---

## Service Modification Checklist

When modifying a service:

- [ ] Read `services/[name]/AGENTS.md`
- [ ] Spec exists in `docs/specs/`
- [ ] ADR created if architectural decision needed
- [ ] Plan approved (EnterPlanMode for >2 files)
- [ ] Auth middleware applied to all new routes (check it's not bypassed)
- [ ] `JWT_SECRET` and `API_KEY` present in `.env.example` with placeholder values
- [ ] New data types defined in `packages/schema/proto/` — NOT in service code
- [ ] `packages/schema/generated/` regenerated and committed if proto changed
- [ ] Unit tests written for new domain functions (`tests/unit/`)
- [ ] E2E tests written for new API endpoints (`tests/e2e/`)
- [ ] `.env.example` updated if new env vars added
- [ ] `AGENTS.md` updated if service behavior or architecture changed
- [ ] All commits follow `type(scope): description` format

---

## Creating a New Service

```bash
# Always use the scaffold script
./scripts/new-service.sh

# Then follow the printed next steps:
# 1. Create GitHub Issue
# 2. Write spec in docs/specs/
# 3. Create ADR if needed
# 4. Plan → implement → PR
```

---

## Schema-First Rule (Critical)

Before writing any type definition in service code:

1. Check if the type exists in `packages/schema/proto/`
2. If not → create the `.proto` definition first
3. Run `cd packages/schema && ./scripts/generate.sh`
4. Commit the proto + generated files
5. Import the generated type in the service

Never define a `type`, `interface`, `struct`, `class`, `dataclass`, or `enum` for a business domain concept in service code. The generated types from `packages/schema` are the only source of truth.

---

## When Spawned via `ao`

If you were launched by `ao spawn` or `ao start`, you are in **orchestrated mode**. The following rules apply and override the defaults in "Behavior Boundaries" below:

- **You are in a git worktree** — your workspace is isolated from `main` and every other session. Never touch another session's branch or the `main` branch directly.
- **Your task is a GitHub Issue** — the issue title and body are your primary context. Before writing any implementation code, check `docs/specs/` for a matching spec file (`[ISSUE-NUMBER]-*.md`). If none exists and the task is a feature, create the spec first (Spec Gate still applies).
- **`docs/CORE_RULES.md` is already in your system prompt** — ao injected it via `agentRulesFile`. You do not need to re-read it, but it still fully binds you.
- **Pushing your branch is pre-authorized** — `ao` monitors the PR lifecycle. Push your feature branch and open a PR when the implementation is complete. Do NOT push to `main` or any branch you did not create.
- **ao manages the PR pipeline** — after you push, ao will automatically: forward CI failures back to you, forward review comments back to you, and notify the human when approval + green CI are reached. Do your work; ao handles the loop.
- **Respond to `ao send` messages** — if ao sends you a message (CI logs, review comments, instructions), treat it as your active task. Address it fully before marking work done.
- **Do not manually create, close, or comment on GitHub Issues or PRs** — use `gh pr create` to open your PR (once), then let ao manage the rest.

---

## Behavior Boundaries

Without explicit human approval, you MUST NOT:

- Push to remote branches
- Create, close, or comment on GitHub Issues or PRs
- Modify CI/CD pipeline configurations
- Drop or migrate databases
- Change infrastructure (AWS, docker-compose services)
- Delete files that may represent in-progress work
- Force-push any branch

When in doubt: stop, explain what you were about to do, and ask.

---

## Quick Reference

| Situation | Action |
|---|---|
| Feature request with no spec | Create spec first, then plan |
| Architectural decision needed | Create ADR before implementing |
| Task touches >2 files | EnterPlanMode |
| Unclear requirements | AskUserQuestion — never assume |
| Potential secret in code | Flag it, do not commit |
| CI check failing | Fix root cause, never use --no-verify |
| New service needed | Run `scripts/new-service.sh` |
