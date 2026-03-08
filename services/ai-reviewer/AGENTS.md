# AGENTS.md — ai-reviewer

> Agent contract for the `ai-reviewer` service.
> Read this before modifying anything in this service directory.

---

## Service Overview

**Name**: `ai-reviewer`
**Purpose**: Async Celery worker that performs AI-powered code review on freelancer submissions. Consumes `review.enqueue` jobs from Redis, clones the submitted repository, runs linters and static analysis, calls Claude Sonnet 4.6 to evaluate the submission against the milestone's acceptance criteria, and writes a `ReviewReport` to PostgreSQL.
**Language**: Python 3.12
**Type**: Worker (Celery consumer — no HTTP server)
**Created**: 2026-03-07
**ADR**: `docs/adr/0002-tech-stack.md`

---

## Tech Stack

- **Language**: Python 3.12
- **Queue**: Redis + Celery (consumer)
- **AI**: Anthropic Python SDK (`claude-sonnet-4-6`)
- **Database**: PostgreSQL (SQLAlchemy async — writes ReviewReport only)
- **Sandboxing**: subprocess (git clone to temp dir, run linters, cleanup)
- **Protocol**: Worker (no HTTP)

---

## Repository Layout

```
services/ai-reviewer/
├── src/
│   ├── tasks/         # Celery task definitions (review_submission.py)
│   ├── reviewer/      # Core review logic — criteria parsing, code analysis, report generation
│   ├── sandbox/       # Subprocess management — clone, lint, cleanup
│   ├── infra/         # DB session, Celery app init, Anthropic client
│   └── config.py      # Pydantic Settings — all env vars validated here
├── tests/
│   ├── unit/          # reviewer logic tests (mocked Claude API)
│   └── e2e/           # full review flow tests (real repo, mocked Claude)
├── Dockerfile
├── Dockerfile.dev
├── .env.example
└── README.md
```

---

## Key Entry Points

- **Celery app**: `src/infra/celery_app.py`
- **Main task**: `src/tasks/review_submission.py` — `review_submission(submission_id: str)`
- **Config**: `src/config.py` — import `settings` not `os.environ`

---

## Environment Variables

| Variable                 | Description                                       |
| ------------------------ | ------------------------------------------------- |
| `REDIS_URL`              | Redis connection string (Celery broker + backend) |
| `DATABASE_URL`           | PostgreSQL — for writing ReviewReport             |
| `ANTHROPIC_API_KEY`      | Claude API key                                    |
| `REVIEW_MODEL`           | Default: `claude-sonnet-4-6`                      |
| `REVIEW_SCORE_THRESHOLD` | Pass threshold (0–100), default 70                |
| `API_KEY`                | Min 16 chars — for any internal API calls         |

---

## Review Flow

```
1. Celery task receives submission_id
2. Load Submission + Milestone (acceptance_criteria) from DB
3. Clone repo to temp directory (subprocess, timeout 60s)
4. Run linters: ruff (Python), eslint (JS/TS), skip if unrecognized lang
5. Build prompt: acceptance_criteria + repo structure + key file contents
6. Call Claude API (claude-sonnet-4-6) with structured output prompt
7. Parse response: verdict (PASS/FAIL/NEEDS_REVISION), score, findings[]
8. Write ReviewReport to DB
9. Cleanup temp directory (always, even on error)
```

---

## Schema Package Usage

Report types come from `packages/schema/proto/ai_reviewer/v1/report.proto`.

```python
from schema.ai_reviewer.v1 import ReviewReport, ReviewVerdict, ReviewFinding, ReviewStatus
```

Never define domain types locally.

---

## Constraints

- Sandbox temp directories must always be cleaned up (use `try/finally`)
- Max repo size: 500MB (reject with error if exceeded)
- Max review timeout: 5 minutes total (Celery task timeout)
- Never log file contents or code in production logs (may contain secrets)
- Claude API calls must include retry logic (max 3 attempts, exponential backoff)
- Only writes to `review_reports` table — never reads/writes other service tables

---

## Forbidden Actions for Agents

- Executing code from cloned repositories (lint only — never `python repo_code.py`)
- Writing to any table other than `review_reports`
- Storing cloned repo contents anywhere persistent
- Hardcoding the Claude model version — always use `settings.review_model`
- Adding an HTTP server to this worker

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
