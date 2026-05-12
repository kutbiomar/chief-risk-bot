# Frontend Usability Sweep - 2026-05-12

Target frontend: local `frontend-mvp` served at runtime
API proxy target: `https://api.chiefriskbot.com`
Viewports: desktop-1440 (1440x1000), tablet-768 (768x1024), mobile-390 (390x844), mobile-375 (375x812), mobile-430 (430x932)

---

## Summary

- Pages checked: 10
- Viewport/page combinations: 50
- Blocking usability failures: 0
- Warnings: 0
- Console warnings/errors: 4
- 5xx network responses: 4
- **UX/UI issues found via screenshot analysis: 13** (5 high, 4 medium, 4 low)

---

## Automated Results

| Viewport | Page | Status | Findings |
|---|---|---|---|
| desktop-1440 | home | PASS | No automated blockers |
| desktop-1440 | assets | PASS | No automated blockers |
| desktop-1440 | cockpit | PASS | No automated blockers |
| desktop-1440 | liquidity | PASS | No automated blockers |
| desktop-1440 | briefings | PASS | No automated blockers |
| desktop-1440 | documents | PASS | No automated blockers |
| desktop-1440 | positions | PASS | No automated blockers |
| desktop-1440 | settings | PASS | No automated blockers |
| desktop-1440 | access | PASS | No automated blockers |
| desktop-1440 | scenarios | PASS | No automated blockers |
| tablet-768 | home | PASS | No automated blockers |
| tablet-768 | assets | PASS | No automated blockers |
| tablet-768 | cockpit | PASS | No automated blockers |
| tablet-768 | liquidity | PASS | No automated blockers |
| tablet-768 | briefings | PASS | No automated blockers |
| tablet-768 | documents | PASS | No automated blockers |
| tablet-768 | positions | PASS | No automated blockers |
| tablet-768 | settings | PASS | No automated blockers |
| tablet-768 | access | PASS | No automated blockers |
| tablet-768 | scenarios | PASS | No automated blockers |
| mobile-390 | home | PASS | No automated blockers |
| mobile-390 | assets | PASS | No automated blockers |
| mobile-390 | cockpit | PASS | No automated blockers |
| mobile-390 | liquidity | PASS | No automated blockers |
| mobile-390 | briefings | PASS | No automated blockers |
| mobile-390 | documents | PASS | No automated blockers |
| mobile-390 | positions | PASS | No automated blockers |
| mobile-390 | settings | PASS | No automated blockers |
| mobile-390 | access | PASS | No automated blockers |
| mobile-390 | scenarios | PASS | No automated blockers |
| mobile-375 | home | PASS | No automated blockers |
| mobile-375 | assets | PASS | No automated blockers |
| mobile-375 | cockpit | PASS | No automated blockers |
| mobile-375 | liquidity | PASS | No automated blockers |
| mobile-375 | briefings | PASS | No automated blockers |
| mobile-375 | documents | PASS | No automated blockers |
| mobile-375 | positions | PASS | No automated blockers |
| mobile-375 | settings | PASS | No automated blockers |
| mobile-375 | access | PASS | No automated blockers |
| mobile-375 | scenarios | PASS | No automated blockers |
| mobile-430 | home | PASS | No automated blockers |
| mobile-430 | assets | PASS | No automated blockers |
| mobile-430 | cockpit | PASS | No automated blockers |
| mobile-430 | liquidity | PASS | No automated blockers |
| mobile-430 | briefings | PASS | No automated blockers |
| mobile-430 | documents | PASS | No automated blockers |
| mobile-430 | positions | PASS | No automated blockers |
| mobile-430 | settings | PASS | No automated blockers |
| mobile-430 | access | PASS | No automated blockers |
| mobile-430 | scenarios | PASS | No automated blockers |

---

## Console observations

- desktop-1440: console error Failed to load resource: the server responded with a status of 500 (Internal Server Error)
- desktop-1440: console error Failed to load resource: the server responded with a status of 500 (Internal Server Error)
- tablet-768: console error Failed to load resource: the server responded with a status of 500 (Internal Server Error)
- mobile-375: console error Failed to load resource: the server responded with a status of 500 (Internal Server Error)

## 5xx network responses

- desktop-1440: 500 http://127.0.0.1:44365/api/overlay/aum-triangulation
- desktop-1440: 500 http://127.0.0.1:44365/api/overlay/stress
- tablet-768: 500 http://127.0.0.1:44365/api/overlay/factors
- mobile-375: 500 http://127.0.0.1:44365/api/overlay/factors

These 500 errors cause the `/overlay/` panels (scenarios exposure map, stress scenarios, factor diagnostics) to render error/empty states on the affected viewports. This is a pre-existing backend issue, not a frontend layout defect.

---

## Screenshot evidence

Screenshots saved under `admin/status/rollout_2026-05-12/usability/screenshots`.

---

## UX / UI Analysis — Screenshot Review

> Methodology: All 30 screenshots (10 pages × desktop-1440, tablet-768, mobile-390) were inspected programmatically via PIL pixel analysis and cross-referenced against `frontend-design-ideal/DESIGN.md` and the CSS source (`_shell.css`, `_mvp.css`). Issues are ordered by severity.

---

### HIGH — Settings: Native Browser Checkboxes

**Affected viewports / pages:** desktop-1440/settings, tablet-768/settings, mobile-390/settings

**Observation:** Three toggle rows on the Settings page ("Auto-publish briefings", "Send PDF attachment", "Include audit footer", "Allow draft trade actions") use `<input type="checkbox">` with no custom styling. In Chromium-based browsers these render as native blue checkboxes. Pixel analysis confirmed 140 off-palette blue pixels (`#3b95ff`, `#55a2fe`, `#6badfe`) on desktop-1440/settings and 67 on tablet-768/settings — in both cases from browser-native checkbox rendering.

**Design spec conflict:** The palette is warm cream + navy `#1B2B5E`. Chromium's checkbox blue (`#3b95ff`) is nowhere in the design system. The anti-pattern "emoji/icon in colored circles" applies in spirit — native platform controls that flash a visually foreign accent color.

**Fix:** Implement custom toggle switches styled with `--accent` / `--paper-3`. A pill-shaped track (`border-radius: 999px`, `background: var(--paper-4)`) with a small circular thumb that slides to `background: var(--accent)` when checked is consistent with the "private bank reading room" aesthetic and adds no distracting chrome.

---

### HIGH — Sidebar Background Uses `var(--paper)` Instead of `var(--paper-2)`

**Affected viewports / pages:** desktop-1440 / all pages

**Observation:** Pixel sampling at the sidebar column (x = 10–230 on the 1440-wide layout) returns `#fdf6f4`–`#fff8f6`, which matches `var(--paper)` (`#fff8f6`), not `var(--paper-2)` (`#f9f2f0`). The only visual boundary between sidebar and content is the 1px `--rule-soft: #efe6e0` hairline border confirmed at x = 255.

**CSS source:** `_shell.css` line 47: `.sidebar { background: var(--paper); }`

**Design spec conflict:** DESIGN.md specifies "Sidebar: paper-2 background". The intended purpose of `paper-2` is precisely to create a subtle, warm-offset tonal distinction between the navigation rail and the working surface — the "private bank reading room" relies on that stratification. Without it, the sidebar and content area merge visually, weakening navigation affordance. The effect is particularly pronounced at desktop where the sidebar occupies 256px (roughly 18% of the screen width) with no background contrast.

**Fix:** Change `.sidebar { background: var(--paper); }` to `.sidebar { background: var(--paper-2); }` in `_shell.css`.

---

### HIGH — `.chart` Component Uses Gradient Background

**Affected viewports / pages:** cockpit, assets, liquidity (wherever `.chart` is used), all viewports

**CSS source:** `_shell.css`:
```css
.chart {
  background: linear-gradient(180deg, var(--paper-2), #fffdfb);
}
```

**Design spec conflict:** DESIGN.md anti-pattern: "No background gradients." This is an unconditional prohibition. The gradient in question is subtle (paper-2 to near-white), but:
1. It is present in the CSS regardless of whether chart content covers it.
2. When a chart fails to load or renders sparse data, the gradient is visible.
3. It sets a precedent that could drift toward decorative gradients elsewhere.

**Fix:** Replace with a flat `background: var(--paper-2)` on `.chart`.

---

### MEDIUM — Sidebar Width Is 256px; Spec Requires 240px

**Affected viewports / pages:** desktop-1440 / all pages

**Observation:** Pixel scan of the sidebar right-border returns `--rule-soft` (#efe6e0) consistently at x = 255, confirming the sidebar occupies x = 0–255 (256px). The CSS variable `--sidebar-w: 256px` in `_shell.css` line 42 confirms this.

**Design spec conflict:** DESIGN.md: "Sidebar: 240px fixed, collapsible to 64px." 256px is 16px wider than spec. While visually inconsequential in isolation, it shifts the 12-column content grid 16px to the right and breaks grid math if any downstream tooling or style guide references the 240px spec.

**Fix:** Change `--sidebar-w: 256px` to `--sidebar-w: 240px` in `_shell.css`.

---

### MEDIUM — `essay-section` Entrance Animation Violates Motion Spec

**Affected viewports / pages:** home, cockpit, briefings, scenarios, and any page using `.essay-section` without `.no-reveal`, all viewports

**CSS source:** `_mvp.css`:
```css
.essay-section {
  opacity: 0;
  transform: translateY(16px);
  transition: opacity 600ms ease, transform 600ms ease;
}
.essay-section.is-visible { opacity: 1; transform: none; }
```

**Design spec conflicts:**
1. "Entrance animations on cards or grid items" — explicitly FORBIDDEN.
2. "Scroll-driven animations" — explicitly FORBIDDEN (the `is-visible` class is added by an IntersectionObserver pattern).
3. 600ms duration exceeds the spec's maximum "long" category at 400ms.
4. `translateY` transforms on hover/entrance are also listed under "Scale or translate transforms on hover".

**Mitigating factors:** The cockpit page uses `<article class="essay-body no-reveal">` which disables the animation for that page. `prefers-reduced-motion` is also respected. But the default behavior on home, briefings, and scenarios is the forbidden animation.

**Fix:** Remove `opacity: 0`, `transform: translateY(16px)`, and the `transition` from `.essay-section`. Sections should be immediately visible. If a mild fade-in is considered essential for reading rhythm, cap it at 200ms opacity-only with no transform, and only on initial page load (not scroll).

---

### MEDIUM — Settings Two-Column Grid Collapses at 980px (Above Tablet Breakpoint)

**Affected viewports / pages:** tablet-768/settings

**Observation:** The settings form uses `.mvp-grid.two` which collapses to a single column at ≤980px per `_mvp.css`. At the 768px tablet viewport, both settings cards ("General" and "Generation defaults") stack vertically. This creates an unusually long, single-column settings page at tablet — requiring significant scrolling for a form that fits comfortably in two columns at 768px.

**CSS source:** `_mvp.css`:
```css
@media (max-width: 980px) {
  .mvp-grid.two { grid-template-columns: 1fr; }
}
```

**Fix:** Override the `.mvp-grid.two` collapse threshold specifically for the settings form. The two-column layout fits naturally down to ~600px for this content. Adjust the breakpoint for `.mvp-settings-card` context to ≤640px (matching the mobile off-canvas breakpoint) rather than ≤980px.

---

### MEDIUM — Skeleton Loader Uses Linear Gradient (Against Anti-Pattern)

**Affected viewports / pages:** scenarios, cockpit, any page with loading skeletons, all viewports

**CSS source:** `_mvp.css`:
```css
.mvp-skeleton {
  background: linear-gradient(90deg, var(--paper-3), #fffdfb, var(--paper-3));
  background-size: 220% 100%;
  animation: mvp-skeleton 1300ms ease-in-out infinite;
}
```

**Design spec conflict:** DESIGN.md anti-pattern: "No background gradients." The skeleton shimmer is a gradient.

**Context:** Skeleton shimmer patterns universally use animated gradients for the perceived-loading motion cue. Removing the gradient would require replacing the shimmer with an opacity pulse (`@keyframes opacity: 0.4→1.0`), which is less legible as a "loading" signal. The skeleton color range stays within the paper token family and is never visible to a user who is not actively loading data.

**Recommendation:** Accept the shimmer gradient as a functional animated state (not decorative background), or replace with an opacity pulse if strict no-gradient policy must be maintained.

---

### MEDIUM — Scenarios Page: Off-Palette Cool Blue in Chart Visualizations (Mobile)

**Affected viewports / pages:** mobile-390/scenarios (and likely tablet/desktop at smaller zoom)

**Observation:** Pixel sampling of the scenarios page (mobile-390) bottom section (y = 600–844) detected cool blue pixels: `#2c3e66`, `#8ca2cd`, `#8c94b8`, `#c1dced`. These are steel-blue and sky-blue tones that fall outside the design system's warm neutral + navy + gold + teal palette.

- `#2c3e66` is close to `--accent` (`#1B2B5E`) so may be a dark accent shade in a chart data series.
- `#8ca2cd`, `#8c94b8` are mid-value slate blues with no design system equivalent.
- `#c1dced` is a washed-out sky blue with no design system equivalent.

**Design spec:** The only allowed blues are `--accent: #1B2B5E` and `--accent-soft: #3a4a7a`. Teal (`#006972`) is the closest cool color permitted. The detected colors appear to be SVG chart fill tones that were assigned programmatically without enforcing the design token palette.

**Fix:** Audit the JavaScript that assigns colors to SVG chart series in the overlay/scenarios feature (`_app.js`) and constrain fill colors to the defined palette: navy family, gold `#C9A449`, teal `#006972`, and severity colors.

---

### LOW — `color-mix()` CSS Usage Has No Fallback

**Affected viewports / pages:** All pages (CSS-level concern)

**CSS source:** 6 occurrences of `color-mix(in srgb, ...)` in `_mvp.css` (e.g., hover border colors on dropzone, chart axis strokes).

**Concern:** `color-mix()` baseline support is Chrome 111+ / Firefox 113+ / Safari 16.2+ (released 2023). Older enterprise browsers (e.g., Chrome 100 on a locked-down corporate device) will silently drop these declarations, causing hover borders to appear with `border-color: transparent` or inherit from a parent.

**Current fallback:** None provided.

**Fix:** Either accept the baseline (modern enterprise is likely fine) or add a preceding fallback declaration:
```css
border-color: #c3b4ac; /* rule-strong approximation */
border-color: color-mix(in srgb, var(--accent) 35%, var(--rule-strong));
```

---

### LOW — Mobile Topbar Brand Name Font Size Inconsistency

**Affected viewports / pages:** mobile-390 / all pages

**Observation:** The mobile topbar brand name ("ChiefRiskBot") in `_shell.js` uses an inline style `font-size:15px`, while the sidebar's `.brand-name` class defines `font-size: 16px`. When a user opens the off-canvas drawer on mobile, the brand appears at 16px; in the topbar it is 15px. This is a 1px discrepancy with no semantic justification.

**Fix:** Remove the inline `font-size:15px` from the mobile topbar anchor or align it to the `.brand-name` token (16px).

---

### LOW — URL vs. Navigation Label Mismatch for Positions Page

**Affected viewports / pages:** All viewports, positions page

**Observation:** The positions/table editor is served at `table.html` and has `data-page="table"` in the body attribute, but the sidebar navigation label and page `<h1>` both read "Positions." A CIO sharing a URL or navigating via the browser address bar will see `/table.html`, not `/positions.html`. This is a discoverability friction point and could cause confusion during onboarding (e.g., "I was told to open Positions but I see /table.html in my URL bar").

**Fix:** Rename `table.html` to `positions.html` and update all references (`_shell.js`, `_app.js`, and any links within other pages).

---

## API error impact summary

| Endpoint | Affected pages | Visible impact in screenshot |
|---|---|---|
| `/api/overlay/aum-triangulation` | scenarios (desktop-1440) | Exposure Map card shows error/empty state |
| `/api/overlay/stress` | scenarios (desktop-1440) | Scenario Impacts section shows error/empty state |
| `/api/overlay/factors` | scenarios (tablet-768, mobile-375) | Factor Diagnostics card shows error/empty state |

These are backend failures, not frontend layout defects. The frontend handles the 500 responses gracefully (`.mvp-notice.error` state is rendered), so no blocking UX failure results. However, the scenarios page effectively presents as partially empty on all captured viewports due to these failures. The screenshot evidence for scenarios therefore does not represent the fully-loaded state.

---

---

### HIGH — Non-Interactive and Non-Functional UI Elements

**Affected viewports / pages:** All pages, all viewports

**Observation:** A significant portion of visible UI elements carry interaction affordances (hover states, cursor: pointer, button chrome) but perform no action when clicked, or are rendered purely as CSS dead-code with no corresponding HTML element. These fall into two sub-groups:

**Elements rendered but wired to nothing:**

| Element | Page | Expected behavior | Actual behavior |
|---|---|---|---|
| "Refresh" button (`#assets-refresh`) | assets | Reloads asset data | No click handler registered in `initAssets()` — silently no-ops |
| Workspace / client switcher (`#crb-client-widget`) | All (sidebar) | Opens workspace switcher or context menu | No click handler anywhere in `_app.js`; purely decorative |
| Table column headers (`<th>`) | positions (table.html) | Sort by column | No sort handlers; headers are unsortable static text |
| ToC section links (scroll-spy active state) | assets, cockpit, liquidity, scenarios | Highlight current section as user scrolls | Active-state scroll-spy only wired on the briefing page; static on all other pages |

**CSS / HTML defined but never rendered:**

| Element | CSS location | Missing from HTML |
|---|---|---|
| Desktop/tablet search bar (`.search`, `.search input`, `<kbd>` shortcut hint) | `_shell.css` L169–170 | `_shell.js` never injects a search bar into the desktop or tablet header; CSS is dead code |
| Breadcrumb navigation (`.crumbs`) | `_shell.css` L165–167 | `CRBMvpShell.mount()` accepts but ignores the `crumbs` argument; the desktop topbar is never rendered at all |

**Design impact:** Non-functional affordances break the "things that look interactive should be interactive" contract. For a CIO who clicks "Refresh" on the assets page and sees nothing happen, or who tries to sort the positions table by market value, trust erodes. The missing search bar is particularly notable: the fully-styled `.search` element (including a `<kbd>` shortcut badge) appears in the shell CSS, suggesting it was planned and removed or deferred without cleaning up the CSS.

**Fix priorities:**
- Wire `#assets-refresh` to reload `initAssets()` data.
- Either wire the workspace switcher to a workspace-select flow or remove the dropdown icon affordance from the client widget.
- Add basic click-to-sort on positions table column headers.
- Either implement search or remove `.search` / `.crumbs` from `_shell.css` to avoid dead-style confusion.
- Wire the scroll-spy IntersectionObserver to `essay-toc` links on all pages that use the ToC sidebar.

---

### HIGH — Typography and Style Mismatches Against Design System

**Affected viewports / pages:** All pages (CSS-level; visible across all viewports)

**Observation:** The `.essay-*` namespace in `_mvp.css` contains a parallel type system that departs substantially from the tokens and constraints defined in `DESIGN.md`. These mismatches are visible in the essay-hero header, section headings, body copy, table typography, and data labels across every page.

**Type scale violations:**

| Component | Spec | Actual CSS | Issue |
|---|---|---|---|
| `.essay-heading` | display-lg: 32px / weight 900 | `font-size: 36px; font-weight: 400` | +4px off scale; weight 400 on a display serif reads as thin/unfinished — the opposite of the "private bank" intent |
| `.essay-heading-sm` | h2: 16px/700 or display: 28px/700 | `font-size: 20px; font-weight: 700` | 20px is not in the type scale; sits between h2 and display with no token |
| `.essay-deck` | body/UI copy: Inter Tight 13px/500 | `font-family: 'Fraunces'; font-size: 22px; font-weight: 400` | Fraunces is only spec'd for display at weight 700–900; weight 400 at 22px creates an oversized, light deck that clashes with the bold serif headlines above it |
| `.essay-prose` | body: 13px / `--ink-soft` `#4f453f` | `font-size: 17px; color: #2b2b2b` | 4px over spec body size; `#2b2b2b` is a neutral gray not in the warm-ink palette |
| `.mvp-feature-stat .value` | mono-lg: 20px/700 | `font-size: 22px` | 2px over the mono-lg token |
| `.mvp-overlay-feature-copy` (large stat) | display-lg: 32px/900 max | `font-size: 26px; font-weight: 800` | 26px is off-scale; weight 800 is not a declared weight for either Inter Tight or Fraunces (loaded weights: 400/500/600/700/900) — browser will synthesize it |

**Color / palette violations:**

| Component | Spec | Actual CSS | Issue |
|---|---|---|---|
| `.essay-eyebrow` color | `--ink-mute: #81756f` (warm taupe) | `rgba(27, 43, 94, 0.55)` (semi-transparent navy) | All section eyebrows (e.g. "Risk", "Composition", "Aggregation") render in a blue-tinted tone instead of the warm-taupe uplabel color defined by the system |
| `.essay-table th` color | `--ink-mute: #81756f` | `rgba(27, 43, 94, 0.55)` | Table column headers also use the transparent navy instead of the warm ink-mute; looks visually inconsistent with the `uplabel` style used elsewhere |
| `.essay-table td` color | `--ink: #1e1b1a` or `--ink-soft: #4f453f` | `#2b2b2b` | Neutral dark gray vs the warm primary ink; desaturates the table body from the warm-paper palette |
| `compositionPalette[5]` (assets, cockpit donut) | No purple in palette | `#8f6f9d` (lavender/mauve) | 6th chart series color is a purple that is explicitly listed as an anti-pattern ("Purple/violet gradients as accents"). Visible whenever a portfolio has ≥6 asset classes / sectors |

**Drawer dimension violations:**

| Component | Spec | Actual CSS | Issue |
|---|---|---|---|
| `.essay-drawer` width | 480px | `width: 520px` | 40px wider than spec |
| `.essay-drawer` left border | `1px solid --rule-strong (#d3c3bc)` | `1px solid rgba(27, 43, 94, 0.12)` | Semi-transparent navy border instead of the warm warm stone `--rule-strong` |

**Root cause:** The `.essay-*` namespace appears to have been developed as a separate editorial skin in parallel to the main `_shell.css` / `_mvp.css` token system, without being reconciled against `DESIGN.md`. Token variables (`var(--text-display-lg)`, `var(--ink-mute)`, `var(--rule-strong)`) are available and used correctly in `_shell.css`, but much of the essay namespace uses hardcoded values that diverge from those tokens.

**Fix:** Audit the `.essay-*` block in `_mvp.css` (approximately lines 1937–2600) and replace hardcoded sizes, weights, and colors with the established CSS variables. Priority replacements:
- `rgba(27, 43, 94, 0.55)` → `var(--ink-mute)` (eyebrows, table headers)
- `#2b2b2b` → `var(--ink)` or `var(--ink-soft)` (table cell text, prose)
- `.essay-heading` → `font-size: var(--text-display-lg); font-weight: 900`
- `.essay-deck` → move to Inter Tight body font or use Fraunces at weight 700
- `.essay-prose` → `font-size: var(--text-body); color: var(--ink-soft)`
- `compositionPalette[5]` → replace `#8f6f9d` with `var(--brand)` (`#72594c`) or a permitted categorical color

---

## Issue tracker

| # | Severity | Component | Summary | Fix |
|---|---|---|---|---|
| U-01 | HIGH | `settings.html` | Native browser checkboxes render off-palette blue | Implement custom CSS toggle switch component |
| U-02 | HIGH | `_shell.css` L47 | Sidebar background is `var(--paper)` not `var(--paper-2)` | Change to `background: var(--paper-2)` |
| U-03 | HIGH | `_shell.css` `.chart` | `.chart` uses forbidden `linear-gradient` background | Replace with flat `var(--paper-2)` |
| U-04 | HIGH | Multiple pages / `_app.js` | Non-functional affordances: assets refresh no-ops, workspace switcher dead, no table sort, search bar CSS orphaned | Wire handlers or remove affordances; clean dead CSS |
| U-05 | HIGH | `_mvp.css` `.essay-*` namespace | Typography/color mismatches: off-scale sizes, weight 400/800 violations, wrong ink colors, purple in chart palette | Reconcile `.essay-*` block against design token variables |
| U-06 | MEDIUM | `_shell.css` L42 | `--sidebar-w: 256px` exceeds spec 240px | Set `--sidebar-w: 240px` |
| U-07 | MEDIUM | `_mvp.css` `.essay-section` | Entrance animation (opacity + translateY, 600ms) violates motion spec | Remove animation; sections render immediately |
| U-08 | MEDIUM | `_mvp.css` `@media ≤980px` | `.mvp-grid.two` collapses on tablet, making settings page excessively long | Move settings-specific 2-col breakpoint to ≤640px |
| U-09 | MEDIUM | `_mvp.css` `.mvp-skeleton` | Skeleton shimmer uses `linear-gradient` | Replace with opacity-pulse, or accept as functional state |
| U-10 | MEDIUM | `_app.js` overlay charts | Off-palette cool blues in scenarios chart series (mobile) | Constrain chart colors to design-system palette tokens |
| U-11 | LOW | `_mvp.css` | `color-mix()` has no fallback declarations | Add static-color fallbacks before each `color-mix()` rule |
| U-12 | LOW | `_shell.js` | Mobile topbar brand name 15px vs sidebar 16px | Align to `.brand-name` font-size token (16px) |
| U-13 | LOW | `table.html` / `_shell.js` | URL `/table.html` doesn't match "Positions" nav label | Rename to `positions.html`; update all refs |
