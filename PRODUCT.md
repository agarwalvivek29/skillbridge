# Product — SkillBridge

> The product source of truth for this project.
> Agents read this to understand _what_ is being built and _why_, before deciding _how_.

## Vision

We are building SkillBridge so that freelancers and clients can collaborate, deliver, and get paid with confidence, without trusting centralized intermediaries or facing opaque dispute resolution.

## Problem Statement

Freelance platforms today suffer from three core failures: trust (clients fear non-delivery; freelancers fear non-payment), opacity (dispute resolution is a black box), and extractive fees. Web3-native freelancers have no platform that combines a large talent pool, smart contract escrow, and AI quality verification. SkillBridge solves all three by anchoring payments to smart contract escrow on Base L2 and using an AI code review agent as an objective quality gate before funds release.

## Target Users

| User type            | Description                                                                       | Primary needs                                                   | Frequency of use |
| -------------------- | --------------------------------------------------------------------------------- | --------------------------------------------------------------- | ---------------- |
| Freelancer           | Technical professional (developer, designer, data scientist) with a crypto wallet | Get paid reliably for delivered work; build on-chain reputation | Daily            |
| Client               | Individual or startup hiring technical talent                                     | Find vetted freelancers; ensure delivery before payment         | Weekly           |
| Admin / Platform Ops | Internal team member                                                              | Monitor disputes, manage platform health                        | Occasional       |

**Primary user** (optimized for when trade-offs are made): Freelancer — the platform only works if talented people choose to list their skills here; everything is designed to reduce friction and increase trust for them.

## Core Features (v1 Must Have)

- **User Auth (wallet SIWE + email/JWT)**: Dual authentication — connect wallet via SIWE or register with email/password; both issue a JWT for API access. Wallet address and email linked to the same User record.
  - Trigger: User visits sign-in page
  - User experience: Connect MetaMask/Coinbase → sign nonce → JWT issued; or register email/password → JWT issued
  - Background: Nonce generated server-side; SIWE signature verified with eth_account; JWT signed with HS256
  - Success state: User receives JWT; both auth methods link to the same User record

- **Freelancer Portfolio with On-Chain Verified Badges**: Freelancers build a profile showcasing skills and completed gigs, with "Verified Delivery" NFT badges minted on Base L2 for each approved milestone.
  - Effort: Medium
  - Why core: Differentiation — on-chain verifiable reputation is the core trust signal

- **Gig Creation with Milestones**: Clients post gigs with acceptance criteria and milestone structure; freelancers apply; client selects and contract activates.
  - Effort: Medium

- **Smart Contract Escrow on Base L2**: Funds locked in escrow contract on Base L2 when gig activates; released per milestone on approval.
  - Effort: Large
  - Why core: The trust mechanism that makes both sides willing to transact

- **Work Submission (repo URL + S3 file upload)**: Freelancers submit deliverables linked to a milestone; supports GitHub URLs and file uploads.
  - Effort: Small

- **Milestone Approval + Auto Fund Release (manual OR AI verdict)**: Client approves milestone → escrow releases funds. Optionally: AI code review verdict triggers auto-release.
  - Effort: Medium

- **Gig Discovery Board + Application Flow**: Browse gigs, filter by category/budget/skill; apply with proposal.
  - Effort: Small

- **AI Code Review Agent (Claude Sonnet 4.6)**: Analyzes submitted code against acceptance criteria; produces a structured review report; verdict can trigger auto fund release.
  - Effort: Large
  - Why core: The differentiating AI quality verification layer

- **Dispute Resolution with AI Evidence + Community Arbitration**: Either party can open a dispute; AI summarizes evidence; community arbitrators vote.
  - Effort: Large

- **On-Chain Reputation Contract**: Aggregates milestone approvals into a score stored on Base L2; used as a trust signal in discovery.
  - Effort: Medium

- **Ratings & Reviews**: Client and freelancer rate each other after gig completion.
  - Effort: Small

- **Notifications (in-app + email)**: Real-time and email notifications for key events (application received, milestone submitted, funds released, dispute opened).
  - Effort: Small

## v1 Complete (Should Have)

- **Advanced search and filtering** on the gig discovery board
- **Analytics dashboard** for freelancers (earnings, acceptance rate, review score)
- **Two-factor authentication** for email users

## v2 and Beyond (Could Have)

- Mobile app (React Native)
- Team accounts (multiple freelancers on one gig)
- Token-gated gigs (requires holding a specific NFT or token to apply)
- DAO governance for platform fee parameters

## Non-Goals

- This product will not build its own fiat payment rails (Stripe, etc.) in v1
- Out of scope for v1: native mobile app
- Out of scope for v1: multi-chain support (Base L2 only)

## Competitive Landscape

| Competitor | Target user                   | Key strength                     | Key weakness                                                |
| ---------- | ----------------------------- | -------------------------------- | ----------------------------------------------------------- |
| Upwork     | General freelancers/clients   | Largest talent pool, brand trust | High fees (20%), opaque disputes, centralized escrow        |
| Fiverr     | Creative/service freelancers  | Gig discovery UX, ease of use    | Not suited for technical/code work, no quality verification |
| Braintrust | Technical freelancers         | Token-based, lower fees          | No smart contract escrow, no AI verification                |
| Gitcoin    | Web3 open-source contributors | On-chain reputation, grants      | Not a general freelance marketplace                         |

**Our differentiation**: The only platform combining: (1) large talent pool with wallet-native onboarding, (2) smart contract escrow on Base L2 eliminating payment trust, (3) AI code review as an objective quality gate before fund release.

**Moat potential**: On-chain reputation data (unique, portable, immutable); AI review quality improves with more submissions (data network effect); verified badge NFTs create switching cost for freelancers who have built reputation.

## Success Metrics

- Freelancers onboarded (v1 target): 500 within 60 days of launch
- Gigs completed with successful fund release: 80% of activated gigs
- Dispute rate: < 5% of gigs
- AI review used as fund release trigger: > 30% of milestone approvals

## Roadmap

### Now (v1 — current focus)

- [x] Project bootstrap and architecture
- [ ] User authentication (wallet SIWE + email/JWT) — Issue #1
- [ ] Freelancer portfolio
- [ ] Gig creation and milestones
- [ ] Smart contract escrow (Base L2)
- [ ] Work submission
- [ ] Milestone approval + fund release
- [ ] Gig discovery board
- [ ] AI code review agent
- [ ] Dispute resolution
- [ ] On-chain reputation
- [ ] Ratings and reviews
- [ ] Notifications

### Next (v2)

- [ ] Advanced search
- [ ] Analytics dashboard
- [ ] 2FA

### Later

- [ ] Mobile app
- [ ] Team accounts
- [ ] Token-gated gigs
