# Design System — ChiefRiskBot

## Product Context
- **What this is:** AI-powered risk briefing and monitoring platform. CIOs upload portfolio positions, ChiefRiskBot fetches live market data, and Claude generates a structured weekly briefing with prioritized risks, talking points, and mitigation actions. The MVP centers on a 4-quadrant risk cockpit, a briefing generator, a data sources / document ingestion screen, and a Supabase-style table editor for manual position data.
- **Who it's for:** Family office CIOs managing $100M–$2B AUM across multiple custodians. Secondary: fund managers ($50M–$500M AUM) without a dedicated risk officer. The buyer is preparing for a weekly investment committee, surrounded by physical artifacts of premium wealth (Patek catalogs, private bank statements on heavy paper, FT weekend edition).
- **Space/industry:** Institutional risk management / wealth tech. Peers: Addepar, Masttro, Arta Finance, Aladdin, Bloomberg AIM. Anti-peers: Robinhood, Coinbase, Wealthfront, Betterment.
- **Project type:** Web application (FastAPI backend, vanilla JS frontend). Single tenant per client. Read in daylight, used 2–4 times per week, often shared on screen with the family principal looking over the CIO's shoulder.

## Aesthetic Direction
- **Direction:** Editorial / Refined-Institutional. A hybrid of *editorial magazine* (serif headlines, considered hierarchy, generous whitespace) and *industrial-utilitarian* (dense data tables, monospace numerics, hairline gridlines).
- **Decoration level:** Minimal. Typography and data carry the design. No background gradients, no decorative blobs, no glassmorphism, no icons-in-colored-circles, no AI slop patterns.
- **Mood:** A private bank reading room rendered in software. The CIO should feel like they are holding a quarterly report from Pictet, not staring at a Bloomberg terminal. Calm beats loud. Density earned through hierarchy, not chrome.
- **Reference sites:** Addepar, Masttro, Arta Finance, Stripe Dashboard, Linear, FT.com, Sotheby's, McKinsey Quarterly. Explicitly NOT: Bloomberg Terminal, Coinbase Pro, Robinhood.

## Typography
- **Display / Hero:** **Fraunces** (Google Fonts, free) — high-contrast variable serif with personality. Used for page titles, quadrant titles, briefing headlines, KPI section headers. Weights 700–900. Slight optical-size adjustment at large sizes. Premium commercial alternative: **GT Super Display**.
- **Body / UI:** **Inter Tight** — geometric sans with slightly condensed letter spacing that reads as institutional rather than SaaS-default. Used for nav, labels, table cells, paragraph copy, buttons. Weights 400/500/600/700. Premium alternative: **Söhne**. Free alternative: **Geist**.
- **Data / Numerics:** **JetBrains Mono** with `font-feature-settings: "tnum"` enabled everywhere numbers appear. Tabular figures are non-negotiable. Every dollar amount, percentage, ratio, date, and timestamp in the entire app uses this face. Weights 400/500/600.
- **Code:** Same as numerics — JetBrains Mono.
- **Loading:**
  ```html
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,700;9..144,900&family=Inter+Tight:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
  ```
- **Type scale (modular, ~1.2 ratio):**
  | Token | Size | Weight | Tracking | Usage |
  |---|---|---|---|---|
  | display-lg | 32px | 900 | -0.025em | Page heroes, briefing headlines |
  | display | 28px | 700 | -0.02em | Page titles ("Good morning, Omar.") |
  | h2 | 16px | 700 | -0.01em | Quadrant titles, section headers |
  | h3 | 14px | 600 | -0.005em | Card subheads |
  | body | 13px | 500 | 0 | Table cells, paragraphs |
  | label | 11px | 600 | 0 | Form labels, button text |
  | uplabel | 10px | 700 | 0.12em | Uppercase eyebrow labels |
  | mono-lg | 20px | 700 | -0.01em | KPI strip numbers |
  | mono-md | 13px | 600 | 0 | Table numerics |
  | mono-sm | 10px | 500 | 0 | Timestamps, footnotes, audit trails |

## Color
- **Approach:** Restrained. One warm neutral palette + one accent + four severity colors. Color is rare and meaningful — when you see it, it carries information.

### Paper system (warm neutrals — backgrounds and surfaces)
| Token | Hex | Usage |
|---|---|---|
| paper | `#fff8f6` | Base canvas, top bar |
| paper-2 | `#f9f2f0` | Subtle alternation, sidebar |
| paper-3 | `#f4ecea` | Elevated surface, hover states |
| paper-4 | `#eee7e4` | Pressed states, deeper surfaces |
| rule | `#e8ddd6` | Hairline borders |
| rule-strong | `#d3c3bc` | Stronger borders, scrollbars |

### Ink system (text)
| Token | Hex | Usage |
|---|---|---|
| ink | `#1e1b1a` | Primary text, headlines |
| ink-soft | `#4f453f` | Secondary text, body copy |
| ink-mute | `#81756f` | Tertiary, labels, timestamps |

### Brand & accent
| Token | Hex | Usage |
|---|---|---|
| brand | `#72594c` | Warm taupe — sparing, secondary categorical use |
| brand-deep | `#584236` | Hover state for brand |
| accent | `#1B2B5E` | Deep navy — the ONE accent. Active nav, links, CTAs, recommended actions |
| accent-soft | `#3a4a7a` | Hover state for accent |
| gold | `#C9A449` | Institutional accent — private equity category, gold lines |
| teal | `#006972` | Secondary categorical color — real estate, alternatives |

### Severity (the four signals — used ONLY for risk states)
| Level | Foreground | Background |
|---|---|---|
| priority | `#B91C1C` | `#FBE9E7` |
| elevated | `#C2741C` | `#FBF1E2` |
| watch | `#A38108` | `#FAF5DC` |
| good | `#3F7A4F` | `#E8F1EA` |

- **Dark mode:** Out of scope for v1. The product is meant to be read in daylight, the same way a wealth statement is. If a buyer requests it later, dark mode will be a *redesign* of surfaces (deep ink-on-cream inversion), not a flipped palette. We will not ship a navy terminal.
- **Accessibility:** ink-soft `#4f453f` on paper `#fff8f6` passes WCAG AA at 13px+. Never use ink-mute for body copy — only for labels and timestamps.

## Spacing
- **Base unit:** 4px
- **Density:** Comfortable-to-dense. Generous breathing room between sections, tight density within sections.
- **Scale:**
  | Token | px | Usage |
  |---|---|---|
  | 2xs | 2 | Hairline gaps, icon-text spacing |
  | xs | 4 | Tight inline spacing |
  | sm | 8 | Inline gaps, badge padding |
  | md | 12 | Form field internal spacing |
  | lg | 16 | Card internal spacing |
  | xl | 20 | Card padding (vertical) |
  | 2xl | 24 | Grid gutters, page padding |
  | 3xl | 32 | Outer page padding, section breaks |
  | 4xl | 48 | Major section breaks |
  | 5xl | 64 | Hero / empty state spacing |
- **Card padding:** `20px 22px` standard
- **Table row heights:** 44px (risk register, briefings list), 36px (table editor — denser, spreadsheet-grade)

## Layout
- **Approach:** Grid-disciplined for the cockpit and ops surfaces, editorial single-column for briefing output.
- **Sidebar:** 240px fixed, collapsible to 64px
- **Top bar:** 56px fixed
- **Content max-width:** None for dashboard (full-bleed grids). 800px for briefing output (so it prints to one column on letter paper).
- **Grid:** 12-column inside the dashboard. Quadrants use asymmetric splits like `col-span-6 / col-span-6` for the top row and `col-span-7 / col-span-5` for the bottom row, so the four cards never feel symmetric and dead.
- **Border radius:**
  | Token | px | Usage |
  |---|---|---|
  | sm | 4 | Inputs, small buttons |
  | md | 6 | Cards, larger buttons |
  | lg | 8 | Modals, drawers |
  | full | 999 | Pills, severity badges, avatars |
- **No bubbly radii.** This is paper, not jelly.
- **Shadows:** Almost none. `0 1px 0 rgba(114,89,76,0.04), 0 1px 2px rgba(30,27,26,0.03)` for cards. Hairline borders do most of the elevation work.

## Motion
- **Approach:** Minimal-functional. Almost invisible. A CIO opens this 4 times a week — animation that delights on day one annoys on day thirty.
- **Easing:**
  - enter: `cubic-bezier(0.16, 1, 0.3, 1)` (ease-out)
  - exit: `cubic-bezier(0.7, 0, 0.84, 0)` (ease-in)
  - move: `cubic-bezier(0.4, 0, 0.2, 1)` (ease-in-out)
- **Duration:**
  - micro: 80ms (hover state changes)
  - short: 200ms (drawer open/close, dropdowns)
  - medium: 300ms (KPI count-up on initial load)
  - long: 400ms (donut chart morph between toggle states, spring-eased)
- **Allowed:**
  - KPI numbers count up on initial dashboard load
  - Donut chart morphs when Asset Class / Sector / Geography toggle is changed
  - Drawer slides in from right
  - Hover states change border color or background only
- **Forbidden:**
  - Page transitions
  - Scroll-driven animations
  - Entrance animations on cards or grid items
  - Scale or translate transforms on hover
  - Parallax of any kind

## Iconography
- **Library:** Material Symbols Outlined, weight 400, optical size 20–24px
- **Stroke style:** Outlined by default. Filled variants only for active nav state.
- **Color:** ink-mute by default, ink on hover, accent on active state
- **Never:** colored icon backgrounds, gradient icons, illustrated icons, emoji as UI

## Components
- **Buttons:**
  - Primary: navy `#1B2B5E` background, white text, 6px radius, 12px vertical padding
  - Secondary: paper-3 background, ink text, 1px rule border
  - Ghost: transparent, ink-soft text, hover paper-3
  - Never use gradient buttons. Never use uppercase button text except for compliance footer actions.
- **Pills / badges:** 999px radius, 10px font, 700 weight, 0.04em tracking, uppercase. Severity pills use the foreground/background pairs above.
- **Tables:**
  - Header: paper-2 background, uplabel typography, hairline bottom border
  - Rows: 44px height, hairline divider, hover paper-3
  - Numerics: right-aligned, JetBrains Mono with tabular-nums
  - Severity: leftmost column, 8px dot
- **Cards:** paper background (`#fffdfb` — slightly elevated above paper), 1px rule border, 6px radius, minimal shadow, 20-22px padding. Never nested cards inside cards.
- **Forms:** Labels above inputs, 11px uplabel typography. Inputs 4px radius, paper-3 background, 1px rule border, focus ring `1px accent`.
- **Drawers:** Slide from right, 480px wide, paper background, 1px left border in rule-strong.

## Anti-patterns (NEVER do these)
- Purple/violet gradients as accents
- 3-column feature grid with icons in colored circles
- Centered everything with uniform spacing
- Bubbly border-radius on all elements
- Gradient buttons as primary CTAs
- Generic stock-photo hero sections
- "Built for X" / "Designed for Y" marketing copy
- Glassmorphism / frosted glass surfaces
- Decorative blobs, swooshes, or background patterns
- Emoji in UI chrome (briefings can use them in body copy if Claude generates them)
- Tables without tabular-nums
- Sans-serif headlines on the dashboard (the serif is the entire personality)
- Dark mode as a flipped color palette

## SAFE choices (category baseline)
1. **Severity color system (red/orange/yellow/green)** — every risk product uses this. Breaking it would break trust.
2. **Tabular numerics in monospace** — non-negotiable in finance.
3. **Sidebar + top bar shell** — buyers can navigate it on day one.

## RISKS (deliberate departures from convention)
1. **Serif display headlines on a financial dashboard.** Almost no risk product does this. They default to sans because "serious = sans". The reward: the family principal glances over the CIO's shoulder and sees something that matches their world (Patek catalog, FT weekend, private bank statement). That's the moment we win the deal.
2. **Warm cream `#fff8f6` instead of pure white or dark mode.** Every modern fintech is one or the other. Cream feels expensive in a way pure white doesn't and considered in a way dark mode doesn't.
3. **Navy `#1B2B5E` as the only accent, used sparingly.** Most products use 4–6 accent colors. We use one. When navy appears, it carries real weight.

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-07 | Initial design system created | Created by /design-consultation. Locks in the warm cream "private bank reading room" direction after rejecting a Bloomberg-style dark terminal. Buyer is the family office CIO, not a sell-side trader. |
| 2026-04-07 | Fraunces over GT Super | Fraunces is free, variable, and has the optical-size axis we need for both 32px headlines and 16px section heads. GT Super is the premium upgrade path if a buyer asks. |
| 2026-04-07 | Inter Tight over Inter | Inter Tight's condensed letter spacing reads as institutional rather than SaaS-default. Avoids the blacklist concern about Inter being overused. |
| 2026-04-07 | Dark mode deferred | The product is read in daylight like a wealth statement. Dark mode would be a separate redesign, not a flipped palette. |
