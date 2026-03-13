# Product — SkillBridge

> The product source of truth for this project.
> Agents read this to understand _what_ is being built and _why_, before deciding _how_.

## Vision

We are building SkillBridge so that freelancers and clients can transact with confidence — payment guaranteed by smart contracts, quality verified by AI — without platform lock-in, broken dispute systems, or 20% fees.

## Problem Statement

The $582B gig economy runs on distrust. 71% of freelancers have experienced payment issues; 48% of clients have had contractors underdeliver. Existing platforms paper over this with centralized escrow and human arbitrators — but Upwork's dispute resolution costs $337.50 to trigger, takes weeks, and is widely described as useless. Fiverr's 20% fee and gameable star ratings create a race to the bottom with no objective quality signal. Neither the freelancer nor the client has a trustworthy, automated way to verify: "was the work actually done to spec?"

SkillBridge locks funds in smart contracts and uses AI to verify deliverable quality — making trust automatic, not platform-dependent.

## Target Users

| User type                | Description                                                               | Primary needs                                                 | Frequency of use                  |
| ------------------------ | ------------------------------------------------------------------------- | ------------------------------------------------------------- | --------------------------------- |
| **Technical Freelancer** | Developers, designers, data scientists doing project-based work           | Guaranteed payment for verified work; portable reputation     | Daily/Weekly (active engagements) |
| **Startup Client**       | Founders and small teams hiring contractors for MVPs, audits, design work | Confidence that deliverables match requirements before paying | Weekly/Occasional                 |

**Balanced marketplace**: Neither user is "primary" — one cannot exist without the other. When trade-offs are made, optimize for the transaction being trustworthy, not for either actor's convenience.

## Core Features (v1 Must Have)

- **User Authentication** — wallet + email sign-in: effort S
  - Trigger: User visits signup/login page
  - User experience: Connect wallet (Phantom/Solflare/Backpack) or email; unified identity
  - Background: Link wallet address to user record; issue JWT
  - Success state: User lands on dashboard with wallet connected

- **Freelancer Portfolio** — showcase past work, linked to verified on-chain completions: effort M
  - Trigger: Freelancer adds portfolio item from profile page
  - User experience: Upload title, description, files/links; completed gigs show "Verified Delivery" badge automatically
  - Background: Store portfolio items in DB; join with on-chain completion records for badge eligibility
  - Success state: Profile page shows portfolio with verified badge on items linked to completed escrow contracts
  - Why it's core: Freelancers can't get hired without showcasing work; verified badges are the differentiation from any other portfolio

- **Gig Creation with Milestones** — client posts project with milestones and acceptance criteria: effort M
  - Trigger: Client clicks "Post a Gig"
  - User experience: Fill title, description, milestones (each with amount + acceptance criteria doc); set total budget
  - Background: Create Gig + Milestone records; generate escrow contract address
  - Success state: Gig visible on board; smart contract address assigned

- **Smart Contract Escrow** — funds locked on Solana until milestone conditions met: effort L
  - Trigger: Client funds the gig after creation
  - User experience: Client deposits total budget via wallet; sees confirmation with escrow account on Solana Explorer
  - Background: Initialize gig_escrow PDA; lock funds; emit EscrowFunded event to API
  - Success state: Funds visible in escrow account on Solana Explorer; freelancer sees "Funded" badge on gig
  - Why it's core: Without trustless escrow, SkillBridge is just another Upwork with a different fee

- **Work Submission** — freelancer submits deliverable for a milestone: effort S
  - Trigger: Freelancer clicks "Submit" on active milestone
  - User experience: Paste repo URL or upload files; add notes
  - Background: Create Submission record; store files to S3; notify client
  - Success state: Submission visible to client; milestone status = SUBMITTED

- **Milestone Approval + Auto Fund Release** — client approves; smart contract releases funds: effort M
  - Trigger: Client clicks "Approve" on a submission, or AI review passes
  - User experience: Client reviews work, approves; funds arrive in freelancer wallet automatically
  - Background: API calls smart contract `completeMilestone()`; funds transfer on-chain; update DB records
  - Success state: Freelancer wallet balance increases; milestone marked PAID on both dashboards

## Also v1 (Must Have, builds on core flow)

- **Gig Discovery Board** — searchable/filterable list of open funded gigs for freelancers to browse and apply
- **Application Flow** — freelancer submits proposal with timeline; client accepts one applicant to begin work
- **AI Code Review** — automated verification that submission meets acceptance criteria (Claude Sonnet 4.6); AI verdict as payment-release trigger
- **Dispute Resolution** — AI evidence summary → 3-day discussion → community arbitration → on-chain vote
- **On-Chain Reputation Contract** — aggregated AI quality scores, completion history, earnings proof; portable across platforms
- **Ratings & Reviews** — mutual rating after gig completion
- **Notifications** — in-app + email: submission received, approval, fund release, new applicant

## Later (post-launch)

- Mobile-native app
- DAO governance for platform parameters

## Non-Goals

- This product will not be an employer of record (EOR) or handle payroll compliance (that's Deel's domain)
- Out of scope: native mobile app at launch (mobile web is acceptable)
- Out of scope: community governance / DAO mechanics at launch

## Competitive Landscape

| Competitor      | Target user                                | Key strength                   | Key weakness                                                        |
| --------------- | ------------------------------------------ | ------------------------------ | ------------------------------------------------------------------- |
| **Upwork**      | Mid-senior professionals                   | Largest talent pool            | $337.50 arbitration, broken dispute resolution, account suspensions |
| **Fiverr**      | Buyers wanting packaged gigs               | Fast discovery                 | 20% fee, gameable ratings, revenue -4% YoY                          |
| **Deel**        | Companies hiring international contractors | Global compliance              | Not a talent marketplace; payroll errors; expensive                 |
| **Braintrust**  | Senior tech freelancers                    | 0% fee for freelancers         | Never solved work verification; limited job volume                  |
| **LaborX**      | Crypto-native freelancers                  | Smart contract escrow (5% fee) | Crypto niche only; no AI verification layer                         |
| **Midcontract** | Remote workers wanting crypto/fiat flex    | 3.6% fee, 130+ payment methods | Pure payment layer; no quality signal                               |

**Our differentiation**: The only platform combining smart contract escrow + AI work verification. No current competitor at commercial scale has all three: large talent pool, trustless escrow, and objective AI quality verification.

**Moat potential**: Verified on-chain completion history is portable and cannot be faked — over time this becomes a stronger hiring signal than any platform's internal rating. Network effects: more verified completions → stronger reputation data → better matching → more gigs.

## Success Metrics

- Gigs completed end-to-end (post → fund → submit → approve → release): 50+ in first 3 months
- Time to payment after milestone approval: < 5 minutes (vs. days on Upwork)
- Dispute rate: < 10% of milestones
- Portfolio verified badge adoption: > 60% of active freelancers link at least one past gig

## Roadmap

### v1 (current focus — full product)

- [ ] User auth (wallet + email)
- [ ] Freelancer portfolio with verified delivery badges
- [ ] Gig creation with milestones + acceptance criteria
- [ ] Smart contract escrow on Solana
- [ ] Work submission (repo URL + file upload)
- [ ] Milestone approval + automatic fund release (manual OR AI verdict)
- [ ] Gig discovery board + application flow
- [ ] AI code review agent (Claude Sonnet 4.6) as payment-release trigger
- [ ] Dispute resolution with AI evidence + community arbitration
- [ ] On-chain reputation contract
- [ ] Ratings & reviews
- [ ] Notifications (in-app + email)

### Later

- [ ] Mobile-native app
- [ ] DAO governance for platform parameters
