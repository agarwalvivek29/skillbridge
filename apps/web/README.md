# web

> Replace with a one-paragraph description of this app.

**Framework**: nextjs (TypeScript)
**Issue**: #TBD

---

## Local Development

```bash
cd apps/web
cp .env.example .env.local  # or .env for Vite
pnpm install
pnpm dev
```

---

## Testing

```bash
pnpm test         # unit tests
pnpm test:e2e     # end-to-end tests (Playwright)
```

---

## Build

```bash
pnpm build
pnpm start        # preview production build
```
