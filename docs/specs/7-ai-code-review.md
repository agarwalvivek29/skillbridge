# Spec: AI Code Review via OpenReview

**Issue**: #7
**Status**: Implemented
**Author**: agarwalvivek29
**Date**: 2026-03-08
**Services Affected**: `services/api`

---

## Summary

When a freelancer submits work with a GitHub PR URL, the API posts `@openreview` as a comment on the PR. The `openreview` GitHub App bot reviews the code and posts a `pull_request_review` event back. The API receives this via a webhook, records a `ReviewReportModel`, and automatically transitions the submission and milestone to `APPROVED` or `REVISION_REQUESTED`.

---

## Background and Motivation

Manual client review is slow and inconsistent. An AI pre-review layer catches obvious issues before the client sees the work, reducing revision cycles and giving freelancers structured feedback faster. This is a core SkillBridge differentiator — no competitor at commercial scale combines smart contract escrow with AI quality verification.

---

## Scope

### In Scope

- `POST /v1/webhooks/github` — receives `pull_request_review` events from the openreview GitHub App bot
- `post_openreview_comment` — posts `@openreview` on the PR when a submission is created
- `ReviewReportModel` + migration 0006 — stores per-submission review verdict, score, and body
- Auto-transition: `approved` → submission `APPROVED` + milestone `APPROVED`; `changes_requested` → submission `REJECTED` + milestone `REVISION_REQUESTED`
- Notifications for both client and freelancer on review completion
- Idempotency guard: duplicate webhook events for the same submission are no-ops
- HMAC signature verification on all webhook events

### Out of Scope

- AI auto-approval triggering the milestone payment flow directly (handled by issue #6)
- Dispute raising/resolution (issue #9)
- Custom AI model replacing the openreview bot (future)
- Retry mechanism for failed `@openreview` comment posting (v2)

---

## Acceptance Criteria

- [x] Given a submission with a GitHub PR `repo_url` is created, then `@openreview` is posted as a PR comment
- [x] Given a `pull_request_review` webhook with `state=approved` from the openreview bot, then submission → `APPROVED`, milestone → `APPROVED`, `ReviewReportModel(verdict=PASS, score=100)` created, notifications sent to client and freelancer
- [x] Given a `pull_request_review` webhook with `state=changes_requested` from the openreview bot, then submission → `REJECTED`, milestone → `REVISION_REQUESTED`, `ReviewReportModel(verdict=FAIL, score=0)` created, notifications sent
- [x] Given a webhook event not from the openreview bot login, then event is ignored (200 `ignored`)
- [x] Given a webhook event with an invalid or missing `X-Hub-Signature-256`, then 401 returned
- [x] Given a duplicate webhook for an already-processed submission, then no-op (idempotent)
- [x] Given a submission already in `APPROVED` or `REJECTED` status, then webhook is ignored
- [x] Given `repo_url` is not a GitHub PR URL (`/pull/\d+`), then submission creation returns 422

---

## Technical Design

### Architecture Overview

```
Freelancer submits work (POST /v1/submissions)
  └── API posts @openreview comment on GitHub PR
        └── openreview bot reviews PR
              └── GitHub sends pull_request_review webhook
                    └── POST /v1/webhooks/github
                          └── process_openreview_verdict()
                                ├── submission.status → APPROVED / REJECTED
                                ├── milestone.status → APPROVED / REVISION_REQUESTED
                                ├── ReviewReportModel created
                                └── Notifications sent to client + freelancer
```

No server-side AI inference. The `openreview` GitHub App is the AI reviewer; this service only processes its verdict.

### API Changes

#### New Endpoints

```
POST /v1/webhooks/github
Headers: X-GitHub-Event, X-Hub-Signature-256
Request: GitHub webhook payload (pull_request_review event)
Response: { status: "ok" | "ignored" }
```

The endpoint is exempt from JWT auth middleware — verified by HMAC (`X-Hub-Signature-256`) instead.

#### Modified Endpoints

`POST /v1/submissions` — `repo_url` validator tightened to require a GitHub PR URL (`https://github.com/{owner}/{repo}/pull/{number}`). GitLab URLs are no longer accepted in v1.

### Data Model Changes

#### New table: `review_reports` (migration 0006)

```sql
CREATE TABLE review_reports (
  id            UUID PRIMARY KEY,
  submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
  verdict       VARCHAR(32) NOT NULL,       -- "PASS" or "FAIL"
  score         INTEGER NOT NULL,           -- v1: binary — 100 = PASS, 0 = FAIL
  body          TEXT NOT NULL DEFAULT '',   -- raw review body from openreview bot
  model_version VARCHAR(64) NOT NULL DEFAULT 'openreview',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_review_reports_submission_id ON review_reports(submission_id);
```

### New Config

| Variable                | Default            | Description                                                                                         |
| ----------------------- | ------------------ | --------------------------------------------------------------------------------------------------- |
| `GITHUB_TOKEN`          | `""`               | PAT with `repo` scope — posts `@openreview` comment; if empty, comment posting is skipped           |
| `GITHUB_WEBHOOK_SECRET` | `""`               | HMAC secret for `X-Hub-Signature-256` verification; if empty, signature check is skipped (dev only) |
| `OPENREVIEW_BOT_LOGIN`  | `"openreview-bot"` | GitHub login of the openreview bot; events from other users are ignored                             |

---

## Security Considerations

- Webhook endpoint uses HMAC-SHA256 (`X-Hub-Signature-256`) for authentication — not JWT
- `hmac.compare_digest` used for constant-time comparison (timing-attack safe)
- If `GITHUB_WEBHOOK_SECRET` is unset, signature check is skipped — acceptable in dev, **must be set in production**
- All `/v1/webhooks/` routes are exempt from JWT middleware; future routes added under this prefix will also be unauthenticated

---

## Observability

- **Logs**: INFO when `@openreview` comment is successfully posted
- **Logs**: WARNING when `post_openreview_comment` fails (includes `submission_id` for manual recovery)
- **Logs**: INFO when webhook is ignored (non-bot reviewer, unsupported event type, already-terminal submission)
- **Logs**: WARNING when webhook references a `pr_url` with no matching submission

---

## Testing Plan

### Unit Tests

- `test_review_domain.py` — covering `process_openreview_verdict` for approved, changes_requested, unknown state, missing submission, idempotency, terminal-status guard

### Integration Tests

- `test_webhooks_api.py` — covering valid/invalid HMAC, ignored events, full approved/rejected flows

### Manual Testing Steps

1. Create a submission with a GitHub PR URL
2. Verify `@openreview` comment appears on the PR
3. Approve the PR review as the openreview bot
4. Verify webhook received: submission → APPROVED, milestone → APPROVED, ReviewReport created

---

## Migration / Rollout Plan

- **Database migrations**: Yes — migration 0006 creates `review_reports` table
- **Breaking changes**: Yes — `repo_url` on submissions now requires a GitHub PR URL; GitLab URLs rejected
- **Feature flag**: No
- **Rollback plan**: Run migration 0006 downgrade; remove `GITHUB_TOKEN` / `GITHUB_WEBHOOK_SECRET` from environment

---

## References

- Related issues: #5 (work submission), #6 (milestone approval), #9 (disputes)
- Related PR: #59
