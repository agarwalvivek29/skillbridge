# AGENTS.md — ai-reviewer

> Agent contract for the `ai-reviewer` service.
> Read this before modifying anything in this service directory.

---

## Service Overview

**Name**: `ai-reviewer`
**Purpose**: Self-hosted instance of [`vercel-labs/openreview`](https://github.com/vercel-labs/openreview). A GitHub App that reviews PRs with Claude Sonnet 4.6 when mentioned with `@openreview`. Triggered by the api service when a freelancer submits work; verdict delivered back to the api via GitHub's `pull_request_review` webhook.
**Language**: TypeScript (Next.js)
**Type**: GitHub App / Webhook Handler
**Created**: 2026-03-07
**Issue**: #7

---

## Tech Stack

- **Runtime**: Node.js / Bun
- **Framework**: Next.js (openreview app)
- **AI**: Anthropic SDK (`claude-sonnet-4-6`) — handled internally by openreview
- **Integration**: GitHub App (webhooks, PR comments, PR reviews)
- **Protocol**: HTTP (Next.js API routes handle GitHub webhook events)

---

## Repository Layout

This directory should contain the cloned `vercel-labs/openreview` codebase.
See README.md for setup instructions.

```
services/ai-reviewer/        ← clone vercel-labs/openreview here
├── app/
├── .env.example
└── README.md (this file documents SkillBridge-specific setup)
```

---

## Key Entry Points

- **Webhook handler**: `app/api/webhooks/route.ts` (openreview internal — handles `@openreview` mentions)
- **Outbound**: openreview posts PR Reviews (APPROVED / CHANGES_REQUESTED) back to GitHub
- **Inbound to api**: GitHub forwards `pull_request_review` events to `api /v1/webhooks/github`

---

## Environment Variables

| Variable                     | Description                        |
| ---------------------------- | ---------------------------------- |
| `ANTHROPIC_API_KEY`          | Claude API key                     |
| `GITHUB_APP_ID`              | GitHub App ID                      |
| `GITHUB_APP_INSTALLATION_ID` | Installation ID for target repos   |
| `GITHUB_APP_PRIVATE_KEY`     | App private key (newlines as `\n`) |
| `GITHUB_APP_WEBHOOK_SECRET`  | Webhook HMAC secret                |

---

## Review Flow

```
1. Freelancer submits work with a GitHub PR URL
2. api posts "@openreview" comment on the PR (services/api/src/infra/github.py)
3. GitHub notifies openreview (this service) via its App webhook
4. openreview clones repo, runs analysis, calls Claude Sonnet 4.6
5. openreview posts PR Review: APPROVED or CHANGES_REQUESTED
6. GitHub sends pull_request_review event to api /v1/webhooks/github
7. api processes verdict → updates submission + milestone + writes ReviewReport
```

---

## Constraints

- Never add custom business logic to this service — it is a vanilla openreview instance
- All verdict processing happens in `services/api/src/domain/review.py`
- `GITHUB_APP_WEBHOOK_SECRET` here and `GITHUB_WEBHOOK_SECRET` in the api must match

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
