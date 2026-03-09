# SkillBridge Design System

> The visual and interaction source of truth for the SkillBridge frontend.
> All UI agents must reference this document when building pages or components.

---

## Brand Identity

- **Name**: SkillBridge
- **Personality**: Professional, trustworthy, modern, tech-forward but human
- **Tone**: Clear, direct, empowering — no jargon, no hype
- **Logo treatment**: "Skill" in semibold, "Bridge" in bold, primary blue. No gradients in the wordmark.

---

## Color Palette

### Brand Colors

| Token         | Hex       | Usage                         |
| ------------- | --------- | ----------------------------- |
| `primary-50`  | `#EFF6FF` | Primary tint backgrounds      |
| `primary-100` | `#DBEAFE` | Hover backgrounds             |
| `primary-200` | `#BFDBFE` | Borders, dividers             |
| `primary-300` | `#93C5FD` | Icons (inactive)              |
| `primary-400` | `#60A5FA` | Focus rings                   |
| `primary-500` | `#3B82F6` | **Primary actions, links**    |
| `primary-600` | `#2563EB` | **Primary button default**    |
| `primary-700` | `#1D4ED8` | Primary button hover          |
| `primary-800` | `#1E40AF` | Primary button active/pressed |
| `primary-900` | `#1E3A8A` | Dark headings on primary bg   |

### Secondary (Accent — Amber)

| Token           | Hex       | Usage                             |
| --------------- | --------- | --------------------------------- |
| `secondary-50`  | `#FFFBEB` | Accent tint                       |
| `secondary-100` | `#FEF3C7` | Highlight bg                      |
| `secondary-400` | `#FBBF24` | Accent icons, stars               |
| `secondary-500` | `#F59E0B` | **Secondary actions, highlights** |
| `secondary-600` | `#D97706` | Secondary button default          |
| `secondary-700` | `#B45309` | Secondary button hover            |

### Web3 Accent (Violet)

| Token      | Hex       | Usage                                   |
| ---------- | --------- | --------------------------------------- |
| `web3-50`  | `#F5F3FF` | On-chain action tint bg                 |
| `web3-100` | `#EDE9FE` | Chain badge bg                          |
| `web3-400` | `#A78BFA` | On-chain indicator, icons               |
| `web3-500` | `#8B5CF6` | **Web3 action buttons, wallet connect** |
| `web3-600` | `#7C3AED` | Web3 button hover                       |
| `web3-700` | `#6D28D9` | Web3 button active                      |

### Semantic Colors

| Token         | Hex       | Usage                           |
| ------------- | --------- | ------------------------------- |
| `success-50`  | `#F0FDF4` | Success bg                      |
| `success-500` | `#22C55E` | Success text, icons             |
| `success-600` | `#16A34A` | Success badge, buttons          |
| `error-50`    | `#FEF2F2` | Error bg                        |
| `error-500`   | `#EF4444` | Error text, icons               |
| `error-600`   | `#DC2626` | Error badge, destructive button |
| `warning-50`  | `#FFFBEB` | Warning bg                      |
| `warning-500` | `#F59E0B` | Warning text, icons             |
| `warning-600` | `#D97706` | Warning badge                   |
| `info-50`     | `#EFF6FF` | Info bg                         |
| `info-500`    | `#3B82F6` | Info text, icons                |
| `info-600`    | `#2563EB` | Info badge                      |

### Neutrals

| Token         | Hex       | Usage                      |
| ------------- | --------- | -------------------------- |
| `neutral-50`  | `#F9FAFB` | Page background            |
| `neutral-100` | `#F3F4F6` | Card background (elevated) |
| `neutral-200` | `#E5E7EB` | Borders, dividers          |
| `neutral-300` | `#D1D5DB` | Disabled borders           |
| `neutral-400` | `#9CA3AF` | Placeholder text           |
| `neutral-500` | `#6B7280` | Secondary/muted text       |
| `neutral-600` | `#4B5563` | Body text                  |
| `neutral-700` | `#374151` | Strong body text           |
| `neutral-800` | `#1F2937` | Headings                   |
| `neutral-900` | `#111827` | Primary text               |
| `neutral-950` | `#030712` | Maximum contrast text      |

### Surface & Background Tokens

| Token                 | Value                   | Usage                      |
| --------------------- | ----------------------- | -------------------------- |
| `bg-page`             | `neutral-50` (#F9FAFB)  | Page background            |
| `bg-surface`          | `#FFFFFF`               | Cards, modals, dropdowns   |
| `bg-surface-elevated` | `#FFFFFF` + shadow      | Elevated cards, popovers   |
| `bg-surface-sunken`   | `neutral-100` (#F3F4F6) | Inset regions, code blocks |
| `border-default`      | `neutral-200` (#E5E7EB) | Default borders            |
| `border-strong`       | `neutral-300` (#D1D5DB) | Emphasized borders         |
| `text-primary`        | `neutral-900` (#111827) | Headings, primary text     |
| `text-secondary`      | `neutral-500` (#6B7280) | Descriptions, help text    |
| `text-disabled`       | `neutral-400` (#9CA3AF) | Disabled state text        |
| `text-on-primary`     | `#FFFFFF`               | Text on primary bg         |
| `text-link`           | `primary-600` (#2563EB) | Links                      |
| `text-link-hover`     | `primary-700` (#1D4ED8) | Link hover                 |

---

## Typography

### Font

**Inter** (Google Fonts) — variable weight, professional, excellent screen readability.

```
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
```

**Monospace** (for code, addresses, hashes):

```
font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
```

### Type Scale

| Token       | Size            | Line Height | Letter Spacing | Usage                                    |
| ----------- | --------------- | ----------- | -------------- | ---------------------------------------- |
| `text-xs`   | 12px / 0.75rem  | 16px (1.33) | +0.02em        | Captions, badges, timestamps             |
| `text-sm`   | 14px / 0.875rem | 20px (1.43) | +0.01em        | Help text, table cells, secondary labels |
| `text-base` | 16px / 1rem     | 24px (1.5)  | 0              | Body text, form inputs                   |
| `text-lg`   | 18px / 1.125rem | 28px (1.56) | -0.01em        | Card titles, section leads               |
| `text-xl`   | 20px / 1.25rem  | 28px (1.4)  | -0.01em        | Section headings                         |
| `text-2xl`  | 24px / 1.5rem   | 32px (1.33) | -0.02em        | Page headings                            |
| `text-3xl`  | 30px / 1.875rem | 36px (1.2)  | -0.02em        | Hero subheading                          |
| `text-4xl`  | 36px / 2.25rem  | 40px (1.11) | -0.02em        | Hero heading, landing page               |

### Font Weights

| Token           | Weight | Usage                                      |
| --------------- | ------ | ------------------------------------------ |
| `font-normal`   | 400    | Body text, descriptions                    |
| `font-medium`   | 500    | Labels, table headers, navigation          |
| `font-semibold` | 600    | Card titles, section headings, button text |
| `font-bold`     | 700    | Page headings, hero text, emphasis         |

---

## Spacing & Layout

### Base Grid

4px base unit. All spacing values are multiples of 4.

| Token       | Value | Common Usage                              |
| ----------- | ----- | ----------------------------------------- |
| `space-0`   | 0px   | —                                         |
| `space-0.5` | 2px   | Tight icon gaps                           |
| `space-1`   | 4px   | Inline icon-to-text gap                   |
| `space-1.5` | 6px   | Badge internal padding                    |
| `space-2`   | 8px   | Tight padding (badge, chip)               |
| `space-3`   | 12px  | Input internal padding, button sm padding |
| `space-4`   | 16px  | Card padding (sm), form field gap         |
| `space-5`   | 20px  | Button md padding-x                       |
| `space-6`   | 24px  | Card padding (md), section sub-gap        |
| `space-8`   | 32px  | Section gap within a page                 |
| `space-10`  | 40px  | Card padding (lg)                         |
| `space-12`  | 48px  | Section vertical padding                  |
| `space-16`  | 64px  | Page section vertical spacing             |
| `space-20`  | 80px  | Hero section vertical padding             |
| `space-24`  | 96px  | Major layout spacing                      |

### Container Max-Widths

| Token          | Width  | Usage                               |
| -------------- | ------ | ----------------------------------- |
| `container-sm` | 640px  | Narrow content (auth forms, modals) |
| `container-md` | 768px  | Medium content (settings pages)     |
| `container-lg` | 1024px | Main content (dashboards)           |
| `container-xl` | 1280px | Wide content (gig boards, tables)   |

All containers are horizontally centered with `px-4` (16px) side padding on mobile, `px-6` (24px) on tablet+.

### Border Radius

| Token          | Value  | Usage                      |
| -------------- | ------ | -------------------------- |
| `rounded-sm`   | 4px    | Badges, chips              |
| `rounded-md`   | 6px    | Buttons, inputs            |
| `rounded-lg`   | 8px    | Cards, modals              |
| `rounded-xl`   | 12px   | Large cards, hero sections |
| `rounded-full` | 9999px | Avatars, pills             |

### Shadows

| Token       | Value                                                               | Usage                              |
| ----------- | ------------------------------------------------------------------- | ---------------------------------- |
| `shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)`                                        | Subtle elevation (inputs on focus) |
| `shadow-md` | `0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)`    | Cards, dropdowns                   |
| `shadow-lg` | `0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)`  | Modals, elevated panels            |
| `shadow-xl` | `0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)` | Popovers, toast stack              |

---

## Components

### Button

| Variant         | Default BG      | Hover BG            | Active BG           | Text Color    | Border            |
| --------------- | --------------- | ------------------- | ------------------- | ------------- | ----------------- |
| **primary**     | `primary-600`   | `primary-700`       | `primary-800`       | white         | none              |
| **secondary**   | `secondary-500` | `secondary-600`     | `secondary-700`     | white         | none              |
| **outline**     | transparent     | `neutral-50`        | `neutral-100`       | `neutral-700` | 1px `neutral-300` |
| **ghost**       | transparent     | `neutral-100`       | `neutral-200`       | `neutral-700` | none              |
| **destructive** | `error-600`     | `#B91C1C` (red-700) | `#991B1B` (red-800) | white         | none              |
| **web3**        | `web3-500`      | `web3-600`          | `web3-700`          | white         | none              |

**Sizes**:

| Size | Height | Padding X | Font Size          | Border Radius |
| ---- | ------ | --------- | ------------------ | ------------- |
| `sm` | 32px   | 12px      | `text-sm` (14px)   | `rounded-md`  |
| `md` | 40px   | 20px      | `text-sm` (14px)   | `rounded-md`  |
| `lg` | 48px   | 24px      | `text-base` (16px) | `rounded-md`  |

**States**:

- **Disabled**: opacity 0.5, cursor not-allowed
- **Focus**: 2px ring offset-2, ring color matches variant (primary-400 for primary, web3-400 for web3, etc.)
- **Loading**: spinner replaces icon (or appears left of text), text remains visible, pointer-events none

All buttons use `font-semibold` (600).

### Input / Textarea / Select

| Property              | Value                                                    |
| --------------------- | -------------------------------------------------------- |
| Height (Input/Select) | 40px                                                     |
| Padding               | 12px horizontal, 8px vertical                            |
| Border                | 1px `neutral-300`                                        |
| Border Radius         | `rounded-md` (6px)                                       |
| Font Size             | `text-base` (16px)                                       |
| Placeholder Color     | `neutral-400`                                            |
| Focus                 | border `primary-500`, ring 1px `primary-500`             |
| Error                 | border `error-500`, ring 1px `error-500`                 |
| Disabled              | bg `neutral-100`, text `neutral-400`, cursor not-allowed |

**Label**: `text-sm`, `font-medium`, `neutral-700`, margin-bottom 6px.
**Helper text**: `text-sm`, `neutral-500`, margin-top 6px.
**Error text**: `text-sm`, `error-500`, margin-top 6px.

Textarea: min-height 120px, resize-y.

### Badge / Status Chip

Compact, inline indicators for status and metadata.

| Property       | Value                                     |
| -------------- | ----------------------------------------- |
| Padding        | 2px 8px                                   |
| Border Radius  | `rounded-full` (9999px)                   |
| Font Size      | `text-xs` (12px)                          |
| Font Weight    | `font-medium` (500)                       |
| Text Transform | uppercase for status, normal for metadata |

### Card

| Variant      | Background   | Border            | Shadow      | Radius       |
| ------------ | ------------ | ----------------- | ----------- | ------------ |
| **flat**     | `bg-surface` | 1px `neutral-200` | none        | `rounded-lg` |
| **elevated** | `bg-surface` | none              | `shadow-md` | `rounded-lg` |
| **bordered** | `bg-surface` | 1px `neutral-200` | `shadow-sm` | `rounded-lg` |

**Internal padding**: `space-6` (24px) on desktop, `space-4` (16px) on mobile.
**Card header**: bottom border 1px `neutral-200`, padding-bottom `space-4`.
**Card footer**: top border 1px `neutral-200`, padding-top `space-4`.

Hover (for clickable cards): `shadow-lg` transition, border-color `primary-200`.

### Modal

| Property      | Value                                      |
| ------------- | ------------------------------------------ |
| Backdrop      | `rgba(0,0,0,0.5)` with blur(4px)           |
| Background    | `bg-surface` (white)                       |
| Width         | `container-sm` max (640px), 90vw on mobile |
| Padding       | `space-6` (24px)                           |
| Border Radius | `rounded-xl` (12px)                        |
| Shadow        | `shadow-xl`                                |

**Header**: `text-xl` `font-semibold`, close button (X icon) top-right.
**Footer**: right-aligned action buttons, gap `space-3`.
Close on Escape key and backdrop click.

### Toast Notifications

| Type        | Icon          | Left Border Color | Background   |
| ----------- | ------------- | ----------------- | ------------ |
| **success** | CheckCircle   | `success-500`     | `bg-surface` |
| **error**   | XCircle       | `error-500`       | `bg-surface` |
| **warning** | AlertTriangle | `warning-500`     | `bg-surface` |
| **info**    | Info          | `info-500`        | `bg-surface` |

Position: top-right, stacked with 8px gap. Auto-dismiss: 5s (info/success), persistent (error/warning until dismissed). Width: 400px max. Shadow: `shadow-lg`. Border-radius: `rounded-lg`.

### Navigation

**Top Nav (Desktop)**:

- Height: 64px
- Background: white, border-bottom 1px `neutral-200`
- Logo left, nav links center, wallet/avatar right
- Nav links: `text-sm` `font-medium`, `neutral-600`, hover `neutral-900`, active `primary-600` with 2px bottom border
- Sticky top, z-50

**Sidebar (Dashboard)**:

- Width: 256px (collapsed: 64px)
- Background: `neutral-900`
- Text: `neutral-400`, hover `neutral-100`, active white with `primary-600` left border (3px)
- Icons: 20px, text `text-sm`
- Sections separated by 1px `neutral-700` divider

**Mobile Bottom Nav**:

- Height: 64px + safe-area-inset-bottom
- Background: white, border-top 1px `neutral-200`
- 5 items max, icon + label stacked
- Active: `primary-600` icon + text; inactive: `neutral-400`
- Fixed bottom, z-50

### Avatar

| Size | Dimensions | Font Size (fallback) |
| ---- | ---------- | -------------------- |
| `xs` | 24px       | 10px                 |
| `sm` | 32px       | 12px                 |
| `md` | 40px       | 14px                 |
| `lg` | 56px       | 20px                 |
| `xl` | 80px       | 28px                 |

- Shape: `rounded-full`
- Border: 2px white (for overlapping groups)
- Fallback: first letter of display name, or blockie-style identicon generated from wallet address
- Background (fallback): `primary-100`, text `primary-700`

### Web3-Specific Components

**AddressChip**:

- Display: truncated address `0x1234...abcd` (first 6 + last 4 chars)
- Font: monospace, `text-xs`
- Background: `web3-50`
- Border: 1px `web3-200` (#DDD6FE)
- Radius: `rounded-full`
- Padding: 2px 8px
- Copy button on hover (clipboard icon)
- Links to Base block explorer on click

**ChainBadge**:

- Shows network name + icon (Base logo)
- Background: `web3-50`
- Border: 1px `web3-200`
- Radius: `rounded-full`
- Font: `text-xs`, `font-medium`
- Used next to contract addresses and transaction hashes

**TxPending Spinner**:

- Circular spinner, 20px, stroke `web3-500`
- Text: "Transaction pending..." in `text-sm`, `neutral-500`
- Pulsing dot animation variant for inline use
- Shows estimated wait time when available

**TxSuccess State**:

- CheckCircle icon in `success-500`
- Text: "Transaction confirmed" in `text-sm`, `success-600`
- Link to block explorer (underlined, `text-link`)
- Auto-dismiss after 8 seconds or manual close

**TxFailed State**:

- XCircle icon in `error-500`
- Text: error message in `text-sm`, `error-600`
- "Try Again" button (outline variant)
- Common error messages: "Insufficient funds", "User rejected transaction", "Network error"

---

## Milestone & Status Color Coding

Every status has a defined background, text color, and border for use in badges and indicators.

| Status               | BG                     | Text                    | Border                  | Dot Color               | Usage                           |
| -------------------- | ---------------------- | ----------------------- | ----------------------- | ----------------------- | ------------------------------- |
| `DRAFT`              | `neutral-100`          | `neutral-600`           | `neutral-300`           | `neutral-400`           | Gig not yet published           |
| `OPEN`               | `primary-50`           | `primary-700`           | `primary-200`           | `primary-500`           | Gig accepting proposals         |
| `PENDING`            | `neutral-100`          | `neutral-600`           | `neutral-300`           | `neutral-400`           | Milestone not yet started       |
| `SUBMITTED`          | `primary-50`           | `primary-700`           | `primary-200`           | `primary-500`           | Work submitted, awaiting review |
| `UNDER_REVIEW`       | `warning-50`           | `#92400E` (amber-800)   | `#FDE68A` (amber-200)   | `warning-500`           | AI or human review in progress  |
| `APPROVED`           | `success-50`           | `#166534` (green-800)   | `#BBF7D0` (green-200)   | `success-500`           | Milestone approved              |
| `PAID`               | `#ECFDF5` (emerald-50) | `#065F46` (emerald-800) | `#A7F3D0` (emerald-200) | `#10B981` (emerald-500) | Funds released to freelancer    |
| `REVISION_REQUESTED` | `#FFF7ED` (orange-50)  | `#9A3412` (orange-800)  | `#FED7AA` (orange-200)  | `#F97316` (orange-500)  | Needs rework                    |
| `DISPUTED`           | `error-50`             | `#991B1B` (red-800)     | `#FECACA` (red-200)     | `error-500`             | Under dispute resolution        |
| `IN_PROGRESS`        | `primary-50`           | `primary-700`           | `primary-200`           | `primary-500`           | Gig actively being worked on    |
| `COMPLETED`          | `success-50`           | `#166534` (green-800)   | `#BBF7D0` (green-200)   | `success-500`           | Gig fully completed             |
| `CANCELLED`          | `neutral-100`          | `neutral-500`           | `neutral-300`           | `neutral-400`           | Gig cancelled                   |

### Proposal Statuses

| Status      | BG            | Text          | Border        |
| ----------- | ------------- | ------------- | ------------- |
| `PENDING`   | `neutral-100` | `neutral-600` | `neutral-300` |
| `ACCEPTED`  | `success-50`  | `#166534`     | `#BBF7D0`     |
| `REJECTED`  | `error-50`    | `#991B1B`     | `#FECACA`     |
| `WITHDRAWN` | `neutral-100` | `neutral-500` | `neutral-300` |

### Dispute Statuses

| Status        | BG           | Text                   | Border                 |
| ------------- | ------------ | ---------------------- | ---------------------- |
| `OPEN`        | `error-50`   | `#991B1B`              | `#FECACA`              |
| `DISCUSSION`  | `warning-50` | `#92400E`              | `#FDE68A`              |
| `ARBITRATION` | `web3-50`    | `#5B21B6` (violet-800) | `#DDD6FE` (violet-200) |
| `RESOLVED`    | `success-50` | `#166534`              | `#BBF7D0`              |

### AI Review Verdict

| Verdict            | BG            | Text          | Icon        |
| ------------------ | ------------- | ------------- | ----------- |
| `PASS`             | `success-50`  | `success-600` | ShieldCheck |
| `FAIL`             | `error-50`    | `error-600`   | ShieldX     |
| `PENDING` (review) | `neutral-100` | `neutral-500` | Loader      |

---

## Page Layout Patterns

### Public Page Layout

```
┌──────────────────────────────────────────┐
│  Top Nav (64px)                           │
│  Logo | Home | Browse Gigs | About | Auth │
├──────────────────────────────────────────┤
│                                          │
│  Main Content (container-xl, centered)    │
│                                          │
├──────────────────────────────────────────┤
│  Footer                                  │
│  Links | Socials | Copyright             │
└──────────────────────────────────────────┘
```

- Top nav is sticky.
- Footer sticks to bottom (min-h-screen flexbox column on main).
- Content area: `py-16` desktop, `py-8` mobile.

### Dashboard Layout

```
┌────────────────────────────────────────────────┐
│  Top Nav (64px, full width)                     │
├──────────┬─────────────────────────────────────┤
│          │                                     │
│ Sidebar  │  Main Content                       │
│ (256px)  │  (flex-1, max container-xl)         │
│          │                                     │
│ Nav      │  Page Header                        │
│ items    │  ─────────────────                  │
│          │  Content area                       │
│          │                                     │
└──────────┴─────────────────────────────────────┘
```

- Sidebar collapses to bottom nav on mobile (< 768px).
- Main content: `p-6` desktop, `p-4` mobile.
- Page header: `text-2xl` `font-bold`, with optional subtitle and action buttons.

### Wizard / Stepper Layout

```
┌────��─────────────────────────────────────┐
│  Top Nav                                 │
├──────────────────────────────────────────┤
│  Step indicator (horizontal bar)          │
│  [1. Details] → [2. Milestones] → [3. Fund] │
├──────────────────────────────────────────┤
│                                          │
│  Step Content (container-md, centered)    │
│                                          │
├──────────────────────────────────────────┤
│  Footer: [Back] [Continue / Submit]      │
└──────────────────────────────────────────┘
```

- Step indicator: numbered circles connected by lines. Active: `primary-600` fill. Completed: `success-500` with check. Upcoming: `neutral-300` border.
- Footer actions right-aligned, `Back` as ghost button, `Continue` as primary.
- Max width: `container-md` (768px) for form content.

### Detail Page Layout

```
┌──────────────────────────────────────────┐
│  Top Nav                                 │
├──────────────────────────────────────────┤
│  Page Header                             │
│  Title | Status Badge | Actions          │
├──────────────────────────────────────────┤
│  Tab Bar                                 │
│  [Overview] [Milestones] [Submissions]   │
├──────────────────────────────────────────┤
│                                          │
│  Tab Content                             │
│                                          │
└──────────────────────────────────────────┘
```

- Tab bar: underline style, `text-sm` `font-medium`, active tab `primary-600` with 2px bottom border.
- Use within dashboard layout (sidebar + detail).

---

## Responsive Breakpoints

| Token | Min Width | Target                   |
| ----- | --------- | ------------------------ |
| `sm`  | 640px     | Large phones (landscape) |
| `md`  | 768px     | Tablets                  |
| `lg`  | 1024px    | Small laptops            |
| `xl`  | 1280px    | Desktops                 |

Mobile-first: base styles target mobile, breakpoints add desktop overrides.

---

## Iconography

Use **Lucide React** icons throughout. 20px default size, 16px for small contexts (badges, inline), 24px for navigation.

Stroke width: 1.75 (default lucide). Color inherits from text color.

---

## Motion & Transitions

| Property                  | Duration | Easing                                   |
| ------------------------- | -------- | ---------------------------------------- |
| Color, background, border | 150ms    | ease-in-out                              |
| Shadow, transform         | 200ms    | ease-out                                 |
| Modal enter               | 200ms    | ease-out (scale 0.95 → 1, opacity 0 → 1) |
| Modal exit                | 150ms    | ease-in (reverse)                        |
| Toast enter               | 300ms    | ease-out (slide from right)              |
| Toast exit                | 200ms    | ease-in (fade out)                       |
| Sidebar collapse          | 200ms    | ease-in-out                              |

No motion when `prefers-reduced-motion: reduce`.

---

## Accessibility

- **Contrast**: All text/background pairs meet WCAG AA (4.5:1 for normal text, 3:1 for large text). The color pairings above are pre-validated.
- **Focus indicators**: Visible focus rings (2px, offset 2px) on all interactive elements. Never remove outline.
- **Keyboard navigation**: All interactive elements reachable via Tab. Modals trap focus. Escape closes overlays.
- **Screen readers**: All icons paired with text or `aria-label`. Status badges use `role="status"`. Form errors use `aria-describedby`. Toast announcements use `role="alert"` with `aria-live="polite"`.
- **Touch targets**: Minimum 44x44px for mobile tap targets.

---

## Dark Mode (Future)

Not implemented in v1. Design tokens are structured to support a future dark theme by swapping the `bg-*` and `text-*` token values. When implemented:

- `bg-page` → `neutral-950`
- `bg-surface` → `neutral-900`
- `text-primary` → `neutral-50`
- Borders → `neutral-700`
- Primary colors remain the same (500-level works on both light and dark)

---

## Tailwind CSS Configuration Notes

All tokens above map directly to Tailwind's default scale where possible. Custom additions to `tailwind.config.ts`:

- Extend `colors` with `primary`, `secondary`, `web3`, `success`, `error`, `warning`, `info` scales
- Set `fontFamily.sans` to Inter
- Set `fontFamily.mono` to JetBrains Mono
- Container max-widths configured via `screens`
- Use CSS custom properties for semantic tokens (`--color-bg-page`, etc.) to enable future dark mode
