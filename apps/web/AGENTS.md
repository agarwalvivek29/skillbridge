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

## Forbidden Actions for Agents

- Changing the build output target or deployment config without approval
- Removing TypeScript strict mode
- Adding tracking scripts or analytics without product approval

---

## Agent Capabilities

Agents may use any available MCP servers, skills, and tools as needed.

### MCP Servers in Use

| MCP Server | Purpose | Added by |
|---|---|---|
| (none yet) | | |
