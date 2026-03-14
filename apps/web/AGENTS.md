# AGENTS.md — web

> Agent contract for the `web` frontend app.
> Read this before modifying anything in this app directory.

## App Overview

**Name**: `web`
**Framework**: nextjs (TypeScript)
**Purpose**: [Describe what this app does]
**Owner**: [team or person]
**Created**: 2026-03-07
**Issue**: #TBD
**Spec**: `docs/specs/TBD-web.md`

---

## Tech Stack

- **Framework**: nextjs
- **Language**: TypeScript (strict mode)
- **Package manager**: pnpm
- **Styling**: [Tailwind / CSS Modules / styled-components]
- **State management**: [Zustand / TanStack Query / Context / etc.]
- **Testing**: [Vitest / Jest + Testing Library / Playwright]

---

## Key Entry Points

- **Main**: `src/app/page.tsx` (Next.js) or `src/main.tsx` (Vite)
- **Config**: `src/config/env.ts` — validated env vars, import this not `process.env`
- **API client**: `src/lib/api.ts`

---

## Environment Variables

See `.env.example` for all required variables.

---

## Local Development

```bash
cd apps/web
cp .env.example .env.local
pnpm install
pnpm dev
```

---

## Amount Formatting

All monetary amounts from the API are in the smallest unit (lamports for SOL, 10^6 for USDC). Always use `formatAmountWithCurrency()` from `lib/format.ts` when displaying amounts to users. Never render raw on-chain values.

---

## Safe Array Access

Always use `?? []` when accessing array fields from API responses. API responses may return `null` or `undefined` for optional arrays. Examples:

- `gig.milestones ?? []`
- `gig.skills ?? gig.required_skills ?? []`

Never trust that an array field will be present — always provide a fallback.

---

## Authentication Flow

- `/auth` is the single entry point for authentication. The navbar shows a "Log In" button that routes to `/auth`, not a wallet connect modal.
- Two-step onboarding: wallet sign-in → email linking → profile setup.
- Do not add wallet connect buttons or modals outside the auth page.

---

## API Client Layer

Frontend API client functions (in `lib/api/*.ts`) are responsible for mapping between frontend-friendly form names and API field names. For example, `createGig` maps `skills` → `required_skills`, `category` → `tags`, auto-computes `total_amount`, and adds `order` to milestones. Components should call API client functions, not construct raw API payloads.

---

## Forbidden Actions for Agents

- Changing the build output target or deployment config without approval
- Removing TypeScript strict mode
- Adding tracking scripts or analytics without product approval

---

## Agent Capabilities

Agents may use any available MCP servers, skills, and tools as needed.

### MCP Servers in Use

| MCP Server | Purpose | Added by |
| ---------- | ------- | -------- |
| (none yet) |         |          |
