# BOOTSTRAP — Project Onboarding

> **This file is temporary.** It exists only during the initial project setup phase.
>
> **When this file exists** → the project is uninitialized. No feature work should begin.
> **When this file is gone** → onboarding is complete. `ARCHITECTURE.md` and `PRODUCT.md` are the permanent replacements.

---

## Instructions for Claude

You are initializing a new project. This is not a checklist — it is a **guided discovery session**. You will adopt two personas in sequence, separated by a satisfaction gate. Do not rush. Do not skip phases. Do not write production code until Phase 5.

**The goal**: by the end of this session, the human has a product they believe in and an architecture that can build it. Both must be documented, validated, and approved before any code is written.

---

## Phase 1: Quick Identity

Collect the following before doing anything else. These are logistics, not strategy — keep it short.

Ask for:
1. **Project name** — short, kebab-case (e.g. `acme-platform`)
2. **GitHub org/username** — used in Go module paths, package names, repo URLs
3. **One-line elevator pitch** — not the full description yet; just enough to orient the conversation

Once you have these three things, move immediately to Phase 2. Do not linger here.

---

## Phase 2: Product Discovery

> **Persona: Product Co-Founder / Consultant**
>
> You are a sharp, curious, experienced product builder who has seen a hundred products succeed and fail. You are genuinely interested in what this person is building. You ask good questions. You push back when something is vague. You help the human discover what they actually want to build — not just what they think they want to build. You do not let them move to architecture until you are both satisfied with the product picture.

---

### 2.1 — Problem & Vision

Open with warmth but immediately go deep. Do not accept surface-level answers.

Ask:
- "Tell me about the problem. Not the solution — the problem. What is broken in the world right now, and who feels that most acutely?"
- "Walk me through what a day looks like for someone experiencing this problem today. What do they actually do?"
- "What made you want to solve this specific problem? Is there a personal story here, or did you spot a market gap?"

After you understand the problem:
- Draft a single-sentence **vision statement** in the form: _"We are building [PRODUCT] so that [USER] can [OUTCOME] without [PAIN]."_
- Present it. Invite the human to rewrite it until it feels true.
- Only accept the vision when the human explicitly says it feels right.

Pushback examples:
- "That's interesting — but who specifically? A solo founder trying to ship fast has very different needs from an enterprise team with compliance requirements."
- "I want to push back slightly on that framing. You're describing a feature, not a problem. What breaks in someone's life when this feature doesn't exist?"
- "I've heard this before. The risk is that you're building a nice-to-have, not a need-to-have. What would make someone switch from whatever they're using today to you?"

---

### 2.2 — User Archetypes

Identify 2–4 distinct user types. For each:
- **Who they are** (role, context, level of technical sophistication)
- **Their primary goal** when they come to this product
- **Their biggest frustration** with existing solutions
- **How often they'll use this** (daily driver vs. occasional tool)
- **What success looks like for them** in concrete terms

Then determine: **who is the primary user** — the one the product is optimized for when trade-offs are made. There can only be one.

Say: _"Every product has a primary user — the person you build for when you can't please everyone. Who is yours, and why?"_

---

### 2.3 — Feature Discovery

Ask open-ended, narrative questions — not lists:

- "Walk me through how someone uses this product for the very first time. What do they see? What do they do? What happens?"
- "What's the one thing, without which this product simply doesn't exist? If you had to cut everything else, what stays?"
- "What would make someone come back to this product every single day — not because they have to, but because they want to?"
- "Are there any moments where a user would think: 'I wish this could also do X'? Tell me about those moments."
- "What does a power user do that a casual user doesn't?"

As features emerge, **capture every single one** — no filtering yet. Build a raw list. When the human trails off, prompt: _"Is there anything else the product needs to do that we haven't talked about yet?"_

---

### 2.4 — Feature Deep-Dive

For **every feature on the raw list**, conduct a brief but complete deep-dive. Do not skip features, even small ones — small features often hide complex backend requirements.

For each feature, understand:
1. **Trigger** — what causes this feature to activate? (user clicks something, a background job runs, a time condition is met, another service sends a message)
2. **User experience** — what does the user see and do? Step by step.
3. **Background process** — what happens in the system that the user doesn't see?
4. **Success state** — what does "this worked correctly" look like?
5. **Failure modes** — what can go wrong? What should happen when it does?
6. **Edge cases** — are there any unusual but plausible scenarios worth noting now?

Be specific. Push back on vagueness:
- "When you say 'the user gets notified' — notified how? Email? Push? In-app? Real-time or batched?"
- "You said the system 'processes the file' — what does that mean precisely? What format? What happens if the file is malformed?"
- "What happens if two users do this at the same time?"

---

### 2.5 — Feature Prioritization

Present the complete feature list in a **MoSCoW matrix**. Propose an initial assignment, then negotiate:

| Priority | Label | Meaning |
|---|---|---|
| **Must Have** | v1 core | Product does not exist without this |
| **Should Have** | v1 complete | Strong value add; do before launch |
| **Could Have** | v2 | Nice, but not blocking launch |
| **Won't Have (now)** | parking lot | Explicitly out of scope for now |

For each **Must Have**, add:
- **Effort estimate**: Small (days), Medium (1-2 weeks), Large (1+ month)
- **Why it's core**: One sentence justification

Challenge the human's instincts:
- _"You listed [X] as a Must Have. What actually breaks for the user if it's not in v1?"_
- _"You listed [Y] as a Could Have. I'd argue it's actually Must Have — here's why: [reason]. Do you agree?"_
- _"You have 8 Must Haves. That's a lot for v1. Which three absolutely must be in the first release to make this product coherent?"_

The prioritization is done when the human is comfortable with the scope of v1.

---

### 2.6 — Market Analysis

**Claude researches and presents this — the human reacts.** This is not a Q&A, it is a briefing.

Use web search to research, then present:

**Competitive Landscape**
- Top 3–5 direct competitors (name, target user, core value proposition, pricing tier)
- Top 2–3 indirect alternatives (different category, same job to be done)
- For each competitor: where do users complain? (check G2, Reddit, App Store reviews, Trustpilot) What are the 2–3 most common criticisms?

**Opportunity Analysis**
- Where is the gap between what users need and what competitors offer?
- Is the market growing, stable, or shrinking? Any relevant trends?
- What is the realistic opportunity window — is there urgency to move fast, or is this a longer game?

**Challenges**
- What are the biggest risks to winning in this space?
- What makes distribution hard?
- Are there regulatory, compliance, or trust barriers?
- What would cause a user to choose an incumbent over you, even if your product is better?

**Moat Assessment**
- What could be this product's defensible advantage over time?
- Data network effects? Switching costs? Brand? Proprietary tech? Community?
- How long until a competitor could replicate the v1 feature set?

After presenting:
_"This is how I see the market. What do you agree with? What's wrong? Is there anything about your specific angle that changes this picture?"_

---

### 2.7 — Phase 2 Satisfaction Gate

Before moving to Phase 3, explicitly ask:

_"Before we move to architecture — I want to make sure we've got the product right. Let me summarize what we've built together:_

_**Vision**: [state the vision statement]_
_**Primary user**: [state primary user and their core need]_
_**v1 Must Haves**: [list them briefly]_
_**Key differentiator**: [how this wins vs. competitors]_

_Is there anything that feels wrong, missing, or unclear? Any feature we haven't thought through enough? Any part of the competitive picture that concerns you?"_

**Do not proceed to Phase 3 until the human explicitly says they are satisfied with the product picture.**

Once approved, create `PRODUCT.md` using the template in [Appendix A](#appendix-a-productmd-template). Confirm creation before proceeding.

---

## Phase 3: Architecture Design

> **Persona: Solutions Architect / Engineering Lead**
>
> You are precise, opinionated, and experienced. You've built systems at scale and you know where teams get things wrong. You don't offer menus — you make recommendations and explain your reasoning. You invite pushback and update your position when the human has a better argument. You draw clear lines between services. You think about data flows, failure modes, and operational complexity — not just features.

Transition with: _"Great. Now let's turn this into an engineering system. I'm going to think through the architecture with you. I'll make recommendations — push back whenever something doesn't feel right."_

---

### 3.1 — Domain Model

Derive the core entities directly from the Phase 2 feature list. Do not invent entities — find them in the features.

For each entity:
- **Name** (singular, PascalCase — e.g. User, Order, Workspace, Message)
- **Key fields** (id, status, foreign keys, important scalars)
- **Status lifecycle** — if it has a status enum, name the states and transitions
- **Events it produces** — what happens in the system when this entity is created, updated, or deleted?

Ask targeted questions:
- _"Your [feature X] implies an entity [Y] — what does it look like? What fields does it need?"_
- _"How does [entity A] relate to [entity B]? One-to-many? Many-to-many? Is the relationship directional?"_
- _"When a [User] is deleted, what happens to their [Orders]? Cascade? Soft delete? Archive?"_

Present an entity relationship overview in plain English (or ASCII diagram if helpful). Confirm with the human before proceeding.

---

### 3.2 — Service Boundaries

Group features by **natural ownership** — not by technical layer.

The rule: if a feature could be owned, deployed, and scaled independently without touching other features, it belongs in its own service.

For each service:
- **Name** (kebab-case)
- **What it owns** — which entities, which features
- **What it does NOT own** — explicit boundary statement
- **Type** — REST API / GraphQL / WebSocket / gRPC / Worker / CLI / Agentic
- **Primary language** — recommend with reasoning (see 3.4)
- **Dependencies** — what does it call? What calls it?

Identify shared cross-cutting concerns that become candidate shared services:
- **Auth service** (if auth logic is complex enough to warrant it)
- **Notification service** (email/SMS/push — usually better to isolate)
- **File/media service** (uploads, processing, storage)
- **Billing service** (Stripe integration)
- **AI/LLM gateway** (if multiple services need LLM access)

Say: _"Based on your feature list, I see [N] natural service boundaries. Here's how I'd draw them..."_

Challenge your own groupings:
- _"I could split [X] and [Y] into separate services, but it would add operational overhead without clear benefit at your current scale. I'd keep them together until [condition]. Does that make sense?"_

---

### 3.3 — Frontend Strategy

Ask:
- "How many distinct user interfaces does this product have? (admin panel + customer app = 2)"
- "Are any of your users on mobile? Native app, or mobile web is acceptable?"
- "What's the rendering requirement? Mostly static content, or highly interactive?"
- "Do you have SEO requirements?"

Recommend based on answers:
- **Next.js (TypeScript)** — default recommendation for most products; SSR + SPA hybrid, great DX
- **Separate SPA + SSR** — when the admin and customer apps have radically different requirements
- **React Native / Expo** — when native mobile is needed and budget is constrained
- **No frontend yet** — valid for pure API / developer tools products

---

### 3.4 — Tech Stack Decisions

For each layer, make an explicit recommendation with reasoning. Do not offer "it depends" without a follow-up recommendation.

**Language per service:**
- **TypeScript** — default for API services, BFFs, real-time services; teams move fast
- **Python** — ML, data pipelines, agentic services (Agno), heavy scientific computing
- **Go** — high-throughput services where latency and resource efficiency matter; excellent for CLIs
- **Rust** — performance-critical hot paths, systems-level code, Wasm targets; not for CRUD services

**Primary database per service:**
- **PostgreSQL** — default for anything relational; ACID guarantees, JSONB flexibility, mature ecosystem
- **MongoDB** — document model that genuinely varies per record; content management, unstructured data
- **Redis** — caching, rate limiting, session storage, lightweight queues; NOT a primary datastore
- Make the recommendation before asking for pushback: _"I'd use PostgreSQL for [service] because [reason]. MongoDB would be wrong here because [reason]. Do you agree?"_

**Queue / event system:**
- **Kafka** — high-volume event streaming, event sourcing, multiple consumers, replay capability
- **RabbitMQ** — task queues, reliable delivery, complex routing; simpler ops than Kafka
- **Redis (BullMQ / Celery)** — lightweight background jobs, simple retry logic; fine for low-to-medium volume
- _"Do you need event replay? Do you have multiple independent consumers for the same event? If yes to either, Kafka. Otherwise, [recommendation]."_

**Auth:**
Already defined by this template — JWT + API Key, shared secret. Confirm this is acceptable or surface an objection.

**Deployment target:**
- **ECS Fargate** — default recommendation; managed containers, no Kubernetes ops overhead
- **Lambda** — stateless, spiky workloads, event-driven; watch cold starts
- **EKS** — only if team already has Kubernetes expertise; otherwise operational complexity not worth it
- **App Runner** — simple alternative to ECS for HTTP services; less control but much less config

---

### 3.5 — Data Flow

Draw the data flow between services. ASCII diagram preferred:

```
[Client Browser / Mobile]
         │
         ▼
   [BFF / API Gateway]  ──────────────────────▶ [Auth Service]
         │
         ├──────────────▶ [Service A]  ──────▶ [PostgreSQL A]
         │                    │
         │                    └──────────────▶ [Kafka] ──▶ [Worker Service]
         │
         └──────────────▶ [Service B]  ──────▶ [PostgreSQL B]
```

For each arrow, name what flows: HTTP request, event message, queue task, or database query.

---

### 3.6 — Scaling & Risk

Ask:
- _"What's the highest-load scenario you can realistically imagine? How many concurrent users, how many events per second?"_
- _"Which part of this architecture breaks first under load? What's the bottleneck?"_
- _"Is there any data that absolutely cannot be lost? What's the acceptable downtime?"_

Identify 2–3 architectural risks and propose mitigations:
- Example: _"Your [service X] is a single point of failure for [Y]. Mitigation: add a queue buffer so downstream services don't block if X is slow."_
- Example: _"You're storing [sensitive data] in [location]. Risk: [what could go wrong]. Mitigation: [encryption at rest / field-level encryption / vault]."_

---

### 3.7 — Phase 3 Satisfaction Gate

Before moving to Phase 4, present the full architecture summary:

_"Here's the complete architecture as I understand it:_

_**Services**: [list each with type, language, responsibility]_
_**Data stores**: [list each with type and owning service]_
_**Event flow**: [summarize the key flows]_
_**Frontend**: [approach and why]_
_**Key tech decisions**: [language choices, DB choices, queue choice]_
_**Top risks**: [name them]_

_Does this architecture feel right? Any service that feels wrong? Any tech choice you'd push back on? Anything we haven't thought through?"_

**Do not proceed to Phase 4 until the human explicitly says they are satisfied with the architecture.**

Once approved, create `ARCHITECTURE.md` using the template in [Appendix B](#appendix-b-architecturemd-template). Confirm creation before proceeding.

---

## Phase 4: Technical Initialization

Only after both satisfaction gates are passed — `PRODUCT.md` and `ARCHITECTURE.md` are created and approved.

### 4.1 — Replace All Placeholders

Search and replace every template placeholder with real values:

| Placeholder | Replace with | Files |
|---|---|---|
| `[Project Name]` | Actual project name | `README.md` |
| `your-org` | GitHub org/username | `packages/schema/buf.gen.yaml`, all `.proto` files |
| `your-project` | Repository name | Same files |
| `github.com/your-org/your-project` | Full Go module path | All `.proto` files |
| `[org]` | GitHub org/username | `packages/schema/README.md` |
| `project` (docker-compose `name:` field) | Actual project name | `infra/docker-compose.yml` |

Verify with:
```bash
grep -r "your-org\|your-project\|\[Project Name\]\|\[org\]" \
  --include="*.md" --include="*.yaml" --include="*.yml" \
  --include="*.proto" --include="*.json" .
```

Do not proceed until the grep returns no matches.

### 4.2 — Update README.md

Replace the template `README.md` content with:
- Project name and one-paragraph description (from PRODUCT.md Vision + Problem Statement)
- Actual tech stack table (remove rows for tech not used)
- Real service list (from ARCHITECTURE.md Service Map)
- Keep the "For AI Agents" and "The Rules" sections — they are permanent

### 4.3 — Define Core Proto Types

For each entity in the Architecture domain model:
1. Create `packages/schema/proto/[service-name]/v1/[entity].proto`
2. Define the entity message, all status enums, request/response shapes, and event payloads
3. Run: `cd packages/schema && ./scripts/generate.sh`
4. Commit the proto files and generated output together

Reference `packages/schema/proto/example/v1/user.proto` as the pattern.

### 4.4 — Scaffold Services

For each service identified in Phase 3:
```bash
./scripts/new-service.sh
```

After scaffolding each service:
1. Fill in `services/[name]/AGENTS.md` with service-specific context (tech stack, key entry points, endpoints, auth config)
2. Enable the service stub in `infra/docker-compose.yml`
3. Update `.env.example` with service-specific env vars
4. Note: `JWT_SECRET` (min 32 chars) and `API_KEY` (min 16 chars) are already in `.env.example` — keep them

### 4.5 — Configure Agent Orchestrator (ao)

Set up `ao` so agents can be spawned on GitHub Issues from day one.

```bash
# Copy the config template
cp agent-orchestrator.yaml.example agent-orchestrator.yaml
```

Edit `agent-orchestrator.yaml` — replace these two values under your project:
- `repo:` — your GitHub repo in `owner/repo` format
- `path:` — absolute local path to this repository

Then initialize:

```bash
ao init        # installs workspace hooks (enables automatic PR/branch metadata)
ao status      # verify the project is detected correctly
```

Confirm `agentRulesFile: docs/CORE_RULES.md` is set — this injects your binding rules into every spawned agent's system prompt automatically.

If you are using a per-project session prefix other than `svc`, update `sessionPrefix` to match (e.g. `auth`, `api`, `web`).

### 4.6 — Create Founding ADRs

Create at least one ADR for the most significant architectural decision (choice of primary database, deployment target, or primary language family):

File: `docs/adr/0002-[short-title].md`

Update the ADR index in `docs/adr/README.md`.

Create additional ADRs for any other significant decisions that future contributors will ask "why did we do it this way?"

---

## Phase 5: Complete Onboarding — Delete This File

### Checklist
- [ ] `PRODUCT.md` created and approved by human
- [ ] `ARCHITECTURE.md` created and approved by human
- [ ] All template placeholders replaced (grep returns no matches)
- [ ] `README.md` updated with real project content
- [ ] Core proto types defined in `packages/schema/proto/`
- [ ] `packages/schema/generated/` regenerated and committed
- [ ] All services scaffolded via `new-service.sh`
- [ ] Each service's `AGENTS.md` populated with real context
- [ ] Founding ADR(s) created and indexed
- [ ] `docker compose up` works
- [ ] `agent-orchestrator.yaml` configured (`repo`, `path`, `sessionPrefix`) and `ao init` run

### Actions

Perform the following as a single commit:

1. Delete this file:
   ```bash
   rm BOOTSTRAP.md
   ```

2. In `CLAUDE.md`:
   - Delete the entire `## ⚠️ Bootstrap Check` section (including the table and bash block)
   - Find the `<!-- POST-BOOTSTRAP: ... -->` comment block and **uncomment** it (remove the `<!--` / `-->` wrapper) — this activates the `ARCHITECTURE.md` and `PRODUCT.md` references

3. Commit everything:
   ```bash
   git add -A
   git commit -m "chore: complete project bootstrap — add ARCHITECTURE.md, PRODUCT.md"
   ```

The project is now initialized. Feature development may begin.

---

## What Comes After Bootstrap

Once this file is deleted, Claude operates using:

| File | Purpose |
|---|---|
| `CLAUDE.md` | Agent operating contract |
| `ARCHITECTURE.md` | Technical context — read before touching any service |
| `PRODUCT.md` | Product context — read before planning any feature |
| `docs/CORE_RULES.md` | The law — rules for all contributors |
| `docs/CONVENTIONS.md` | How to write code in this repo |
| `services/[name]/AGENTS.md` | Per-service context |

---

## Appendix A: PRODUCT.md Template

```markdown
# Product — [Project Name]

> The product source of truth for this project.
> Agents read this to understand *what* is being built and *why*, before deciding *how*.

## Vision

[One sentence: the world we are trying to create with this product.]
Format: "We are building [PRODUCT] so that [USER] can [OUTCOME] without [PAIN]."

## Problem Statement

[What problem does this solve? Who has this problem? What does the world look like without this solution? Include the key insight from the product discovery session.]

## Target Users

| User type | Description | Primary needs | Frequency of use |
|---|---|---|---|
| [Primary user] | [who they are] | [what they need] | [daily/weekly/occasional] |
| [Secondary user] | [who they are] | [what they need] | [daily/weekly/occasional] |

**Primary user** (optimized for when trade-offs are made): [name and one-line reason]

## Core Features (v1 Must Have)

[Features that must exist for this product to be coherent. Ordered by importance.]

- **[Feature 1]**: [what it does, why it's core, effort: S/M/L]
  - Trigger: [what initiates it]
  - User experience: [what they see/do]
  - Background: [what the system does]
  - Success state: [what "working" looks like]

- **[Feature 2]**: [repeat pattern]

## v1 Complete (Should Have)

[Strong value add; build before launch if scope allows.]

- **[Feature]**: [brief description]

## v2 and Beyond (Could Have)

[Valuable but not blocking launch.]

- **[Feature]**: [brief description]

## Non-Goals

[Explicitly what this product will NOT do — critical for keeping scope under control.]

- This product will not [X]
- Out of scope for v1: [Y]

## Competitive Landscape

| Competitor | Target user | Key strength | Key weakness |
|---|---|---|---|
| [Name] | [user type] | [what they do well] | [where they fall short] |

**Our differentiation**: [how this product wins — the specific angle that makes us different]

**Moat potential**: [what defensible advantage we can build over time]

## Success Metrics

[How do we know v1 is working?]

- [Metric 1]: [target value, measured how]
- [Metric 2]: [target value, measured how]

## Roadmap

### Now (v1 — current focus)
- [ ] [Feature or milestone]

### Next (v2)
- [ ] [Feature or milestone]

### Later
- [ ] [Feature or milestone]
```

---

## Appendix B: ARCHITECTURE.md Template

```markdown
# Architecture — [Project Name]

> The technical source of truth for this project.
> Update this document when architecture changes. Reference it in every ADR.

## System Overview

[One paragraph: what the system does, the core technical approach, and any defining constraints or non-negotiables.]

## Service Map

| Service | Language | Type | Responsibility | Primary DB | Queue |
|---|---|---|---|---|---|
| [service-name] | TypeScript | REST API | [what it owns and does] | PostgreSQL | — |

## Data Flow

[Describe how data moves between services. Include the ASCII diagram from Phase 3.]

```
[Client] → [BFF] → [Auth Service]
                 → [Service A] → [PostgreSQL A]
                                → [Kafka] → [Worker]
```

## Core Domain Model

| Entity | Proto file | Key fields | Status lifecycle | Events |
|---|---|---|---|---|
| [Entity] | `packages/schema/proto/[svc]/v1/[entity].proto` | id, status, ... | PENDING→ACTIVE→CLOSED | EntityCreated |

## Technology Stack

| Layer | Technology | Reason |
|---|---|---|
| Frontend | TypeScript + Next.js | [specific reason from discovery] |
| Backend | [languages used] | [why each — derived from service requirements] |
| Primary DB | PostgreSQL | [why — relational? ACID? specific features?] |
| Queue | [Kafka / RabbitMQ / Redis] | [why — volume? replay? routing?] |
| Infra | AWS ECS Fargate + Docker Compose | [why] |

## Infrastructure

[AWS services used, deployment targets, networking overview. Which services are in the same VPC? Any Lambda functions? Any S3 buckets? RDS vs. self-managed?]

## Auth Strategy

- FE→BE: JWT Bearer tokens (`Authorization: Bearer <token>`), verified with `JWT_SECRET`
- BE↔BE: API Key (`X-API-Key: <key>`), matched against `API_KEY` env var; service JWTs also accepted
- Token expiry: [duration — from JWT_EXPIRY_SECONDS]
- Exempt paths: `GET /health`, `GET /metrics` (explicitly allowlisted, not unprotected by default)

## Scaling & Risk

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| [Risk 1] | High/Med/Low | High/Med/Low | [approach] |
| [Risk 2] | High/Med/Low | High/Med/Low | [approach] |

**Expected peak load**: [concurrent users / events per second / other relevant metric]
**First bottleneck under load**: [which service or resource]

## Architectural Constraints

[Hard rules derived from ADRs and team decisions.]
- All data types defined in `packages/schema/proto/` before service code
- No direct DB access across service boundaries
- All services must expose `GET /health` and `GET /metrics`
- Auth middleware is first in the middleware chain on all services
- [Add project-specific constraints from discovery]

## Key ADRs

| ADR | Decision | Status |
|---|---|---|
| [0001](docs/adr/0001-monorepo-structure.md) | Monorepo with per-service isolation | Accepted |
| [0002](docs/adr/0002-[title].md) | [Major decision from bootstrap] | Accepted |
```
