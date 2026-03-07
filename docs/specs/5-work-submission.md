# Spec: Work Submission (Repo URL + File Upload)

**Issue**: #5
**Status**: Approved
**Author**: engineering
**Date**: 2026-03-07
**Services Affected**: `services/api`

---

## Summary

Assigned freelancers can submit work for a milestone by providing a GitHub/GitLab repo URL and/or uploading files. Each submission creates a versioned `Submission` record linked to its milestone. Re-submissions after a revision request are linked to their predecessor via `previous_submission_id`, forming an auditable revision chain.

---

## Background and Motivation

Milestones represent units of work in a gig. The freelancer must be able to deliver evidence of completion (code repo, design files, screenshots) so the client and AI reviewer can evaluate it. Without a submission mechanism there is no way to trigger payment or the AI review pipeline.

---

## Scope

### In Scope

- `POST /v1/milestones/{milestone_id}/submissions` — create a submission (repo URL + file keys)
- `GET /v1/milestones/{milestone_id}/submissions` — list all submissions for a milestone (revision history)
- `GET /v1/submissions/{submission_id}` — get a single submission
- `POST /v1/submissions/upload-url` — generate a presigned S3 PUT URL for direct browser upload
- Milestone status transitions: PENDING/REVISION_REQUESTED → SUBMITTED → UNDER_REVIEW
- `revision_count` increment on each submission
- Celery task `review.enqueue` enqueued on each submission
- In-app notification (`NOTIFICATION_TYPE_SUBMISSION_RECEIVED`) created for the client

### Out of Scope

- Notification retrieval/read endpoints (Issue #12)
- AI review processing itself (Issue #7)
- Milestone approval / fund release (Issue #6)
- Dispute flow (Issue #9)

---

## Acceptance Criteria

- [ ] Freelancer can submit a repo URL (GitHub/GitLab) and/or file keys for a milestone
- [ ] Files are uploaded directly to S3 via presigned PUT URL; API only stores the resulting S3 key
- [ ] First submission has `revision_number = 1`, `previous_submission_id = null`
- [ ] Re-submissions (after REVISION_REQUESTED) get `revision_number = prev + 1` and `previous_submission_id` pointing to the prior submission
- [ ] Submission creates a `Submission` record and enqueues Celery task `review.enqueue` with `submission_id`
- [ ] Milestone status transitions: PENDING/REVISION_REQUESTED → SUBMITTED → UNDER_REVIEW; `revision_count` incremented
- [ ] Submission status: created as PENDING, updated to UNDER_REVIEW after enqueue
- [ ] Client is notified (`NOTIFICATION_TYPE_SUBMISSION_RECEIVED`) on new submission
- [ ] Only the assigned freelancer (`gig.freelancer_id`) can submit on a given gig
- [ ] Submission rejected if milestone is not in a submittable state (returns 409)
- [ ] Unauthenticated or wrong-role requests return 401/403

---

## Technical Design

### Architecture Overview

```
Freelancer Browser
  │
  ├─ POST /v1/submissions/upload-url   → api returns presigned S3 PUT URL + file_key
  │
  ├─ PUT <presigned S3 URL> (direct)   → file lands in S3 (does NOT route through api)
  │
  └─ POST /v1/milestones/{id}/submissions (file_keys=["s3://..."], repo_url="...")
       │
       ├─ api: validate, create SubmissionModel (PENDING)
       ├─ api: update MilestoneModel status → SUBMITTED, revision_count++
       ├─ api: enqueue Celery task review.enqueue(submission_id)
       ├─ api: update SubmissionModel status → UNDER_REVIEW
       ├─ api: update MilestoneModel status → UNDER_REVIEW
       └─ api: create NotificationModel (NOTIFICATION_TYPE_SUBMISSION_RECEIVED → client)
```

### API Changes

#### New Endpoints

```
POST /v1/milestones/{milestone_id}/submissions
Authorization: Bearer <token>   (FREELANCER role, must be assigned freelancer)
Request:
{
  "repo_url": "https://github.com/user/repo",   // optional
  "file_keys": ["submissions/uuid/file.zip"],   // optional; keys from upload-url
  "notes": "Implemented per spec...",           // optional
  "previous_submission_id": "uuid"              // required on re-submission
}
Response 201:
{
  "id": "uuid",
  "milestone_id": "uuid",
  "freelancer_id": "uuid",
  "repo_url": "https://...",
  "file_keys": ["..."],
  "notes": "...",
  "status": "UNDER_REVIEW",
  "revision_number": 1,
  "previous_submission_id": null,
  "created_at": "...",
  "updated_at": "..."
}

GET /v1/milestones/{milestone_id}/submissions
Authorization: Bearer <token>
Response 200:
{
  "submissions": [ <SubmissionOut>... ]
}

GET /v1/submissions/{submission_id}
Authorization: Bearer <token>
Response 200: <SubmissionOut>

POST /v1/submissions/upload-url
Authorization: Bearer <token>
Request: { "filename": "screenshot.png", "content_type": "image/png" }
Response 200:
{
  "upload_url": "https://s3.amazonaws.com/...",
  "file_key": "submissions/2026/uuid/screenshot.png"
}
```

### Data Model Changes

#### New Tables

```sql
CREATE TABLE submissions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  milestone_id    UUID NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
  freelancer_id   UUID NOT NULL REFERENCES users(id),
  repo_url        TEXT,
  file_keys       TEXT[] NOT NULL DEFAULT '{}',
  notes           TEXT NOT NULL DEFAULT '',
  status          VARCHAR(32) NOT NULL DEFAULT 'PENDING',
  revision_number INTEGER NOT NULL DEFAULT 1,
  previous_submission_id UUID REFERENCES submissions(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notifications (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES users(id),
  type         VARCHAR(64) NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  read_at      TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Queue / Event Changes

- **New event published**: Celery task `review.enqueue` with payload `{"submission_id": "<uuid>"}`
  - Broker: Redis (`REDIS_URL`)
  - Consumer: `ai-reviewer` service (Issue #7)

### Dependencies

- `boto3` — already in pyproject.toml (S3 presigned URL generation)
- `celery[redis]` — already in pyproject.toml (task queue)

---

## Security Considerations

- Only `USER_ROLE_FREELANCER` may create submissions; role check enforced in router
- Caller's `user_id` must match `gig.freelancer_id`; checked in domain layer
- S3 presigned URLs are time-limited (default 15 minutes) and scoped to a single object key
- File keys validated to ensure they are `submissions/...` prefix only (prevent path traversal)
- `repo_url` validated to be a GitHub or GitLab HTTPS URL

---

## Observability

- **Logs**: `submission created submission_id=... milestone_id=... revision=...` at INFO
- **Logs**: `review.enqueue dispatched submission_id=...` at INFO
- **Logs**: `celery unavailable, skipping enqueue` at WARNING when Redis unreachable

---

## Testing Plan

### Unit Tests (`tests/unit/test_submission_domain.py`)

- Happy path: first submission created with revision_number=1
- Re-submission after REVISION_REQUESTED: revision_number increments, previous_submission_id set
- Submission rejected if milestone status is APPROVED (409)
- Submission rejected if freelancer is not the assigned freelancer (403)
- Submission rejected if milestone not found (404)
- Submission rejected if gig has no assigned freelancer (409)

### Integration Tests (`tests/e2e/test_submission_api.py`)

- POST creates submission and returns 201
- Unauthenticated POST returns 401
- CLIENT role POST returns 403
- GET milestone submissions returns revision list
- GET single submission returns correct data

---

## Migration / Rollout Plan

- **Database migrations**: Yes — migration `0003_create_submissions_and_notifications.py`
- **Breaking changes**: No — additive only
- **Feature flag**: No
- **Rollback plan**: `alembic downgrade 0002` drops both new tables; no data loss to existing tables

---

## References

- Related ADRs: [ADR 0002](../adr/0002-tech-stack.md) (Redis+Celery, S3)
- Proto: `packages/schema/proto/api/v1/submission.proto`
- Issue #5
