# ai-reviewer — OpenReview Instance

This service is a self-hosted deployment of [`vercel-labs/openreview`](https://github.com/vercel-labs/openreview), an AI-powered PR review bot backed by Claude Sonnet 4.6.

SkillBridge uses it to automatically review freelancer work submissions: when a freelancer submits a GitHub PR URL, the api posts `@openreview` as a PR comment, OpenReview runs its review, and the verdict feeds back to the api via GitHub webhook.

**Language**: TypeScript (Next.js)
**Type**: GitHub App / Webhook Handler
**Issue**: #7

---

## How it fits into SkillBridge

```
Freelancer submits PR URL
        ↓
api posts "@openreview" comment on the PR
        ↓
OpenReview (this service) receives the mention via GitHub App webhook
        ↓
OpenReview reviews the PR with Claude, posts PR Review (APPROVED / CHANGES_REQUESTED)
        ↓
GitHub sends pull_request_review event → api /v1/webhooks/github
        ↓
api updates submission + milestone status, writes ReviewReport
```

---

## Setup

### 1. Clone OpenReview into this directory

```bash
# from repo root
git clone https://github.com/vercel-labs/openreview services/ai-reviewer
# or if already inside this directory:
git clone https://github.com/vercel-labs/openreview .
```

### 2. Install dependencies

```bash
bun install
```

### 3. Configure environment

```bash
cp .env.example .env
# fill in real values — see table below
```

### 4. Create a GitHub App

Go to `https://github.com/settings/apps/new`:

| Field                  | Value                                                              |
| ---------------------- | ------------------------------------------------------------------ |
| Webhook URL            | `https://your-openreview-domain/api/webhooks`                      |
| Webhook Secret         | value for `GITHUB_APP_WEBHOOK_SECRET`                              |
| Repository permissions | Contents (R/W), Issues (R/W), Pull requests (R/W), Metadata (R)    |
| Subscribe to events    | Issue comments, Pull request review comments, Pull request reviews |

Generate a private key. Note the App ID and Installation ID.

### 5. Install the GitHub App on freelancer repos

`https://github.com/apps/{your-app-name}` → Install → select repos where freelancers will submit PRs.

### 6. Run

```bash
bun dev          # local, port 3000
```

Or deploy to Vercel (recommended for production).

---

## Environment Variables

| Variable                     | Description                             |
| ---------------------------- | --------------------------------------- |
| `ANTHROPIC_API_KEY`          | Claude API key                          |
| `GITHUB_APP_ID`              | GitHub App ID                           |
| `GITHUB_APP_INSTALLATION_ID` | Installation ID for your repos          |
| `GITHUB_APP_PRIVATE_KEY`     | App private key (use `\n` for newlines) |
| `GITHUB_APP_WEBHOOK_SECRET`  | Webhook HMAC secret                     |

---

## Troubleshooting

| Problem                   | Solution                                                         |
| ------------------------- | ---------------------------------------------------------------- |
| Review not triggered      | Confirm GitHub App is installed on the PR's repo                 |
| Webhook not received      | Check App webhook URL and secret match                           |
| Verdicts not reaching api | Confirm api `GITHUB_WEBHOOK_SECRET` matches App's webhook secret |
| Service won't start       | Check `.env` has all required variables from `.env.example`      |
| DB connection refused     | Ensure `docker compose up -d` has been run                       |
