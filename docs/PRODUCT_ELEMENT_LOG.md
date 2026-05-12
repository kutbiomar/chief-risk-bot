# ChiefRiskBot — Product element log

**Scope:** Live app at `https://app.chiefriskbot.com` (production build `_api.js?v=2`, `_shell.js?v=2`, `_app.js?v=2`), cross-checked with this repository’s design intent (`frontend-design-ideal/DESIGN.md`) and automated smoke coverage (Playwright, 2026).

**Legend — functionality**

| Status | Meaning |
|--------|---------|
| OK | Behaves as expected in normal use |
| Partial | Works for primary path; gaps, noise, or missing polish |
| Risk | Intermittent, unclear, or depends on environment |
| N/A | Not applicable or not exposed on prod |

**Legend — design**

| Status | Meaning |
|--------|---------|
| On-spec | Matches DESIGN.md direction (cream paper, Fraunces + Inter Tight + JetBrains Mono, navy accent `#1B2B5E`, restrained institutional) |
| Drift | Minor deviation from ideal system |
| Unknown | Not verified with pixel-level audit |

---

## 1. Platform and delivery

| Element / feature | Functionality (current) | Design (current) | End state (intended) | Failures / causes |
|-------------------|-------------------------|------------------|----------------------|-------------------|
| HTTPS / hosting | OK — site loads, redirects canonical paths | On-spec overall | Stable TLS, fast TTFB | None observed |
| URL routing | Partial — mix of clean paths (`/cockpit`) and legacy files (`/scenarios.html`, `/access.html`) | N/A | Single consistent scheme (prefer clean paths everywhere) | **Cause:** incremental deploy; old links coexist with rewrites |
| Static asset versioning (`?v=2`) | OK — cache bust on JS | N/A | Versioned bundles | None |
| Content-Security-Policy | Partial — blocks Cloudflare Insights | N/A | Either allow beacon host or remove snippet | **Cause:** `script-src 'self'` rejects `static.cloudflareinsights.com` → console noise, no analytics |
| Optional `fetch` 401 | Risk — at least one request returns 401 in session | N/A | No spurious unauthorized calls | **Cause:** not traced in smoke (likely optional endpoint, expired secondary token, or probe without auth); needs Network tab on failing URL |
| Demo data vs API naming | Partial — UI after login aligns with API (“Whitmore Family Office”); older static copy elsewhere may say “Aldridge” | Drift if both appear | Single canonical demo narrative | **Cause:** static HTML not regenerated when demo tenant renamed |

---

## 2. Authentication and session

| Element / feature | Functionality (current) | Design (current) | End state (intended) | Failures / causes |
|-------------------|-------------------------|------------------|----------------------|-------------------|
| API `POST /api/auth/login` | OK — 200 + JWT for demo CIO | N/A | Secure, rate-limited login | None for demo creds |
| Login page `/login` / `login.html` | OK — email/password, tabs (Sign in / Create workspace), forgot panel | On-spec (card, tabs, typography) | Frictionless sign-in, clear errors | **Partial:** register/forgot paths not exhaustively tested |
| Token storage (`crb_token`, `crb_logged_in`) | OK — matches `_api.js` | N/A | Session + optional “remember” | **Cause of prior automation confusion:** open-source repo MVP used different keys (`crb.auth_token.session`); not a prod bug |
| Post-login redirect | OK — to `/` | N/A | Landing on home or last route | None observed |
| `/auth/me` hydration of sidebar pill | OK — replaces shell placeholders with real user | On-spec | Accurate identity always | **Partial before hydration:** static “CIO” placeholder flashes until `/auth/me` completes |
| Logout (if present in UI) | Unknown in eight-page shell | N/A | Clear session everywhere | Not clicked in last prod pass; confirm on settings or profile when added |

---

## 3. Application shell (all authenticated pages)

| Element / feature | Functionality (current) | Design (current) | End state (intended) | Failures / causes |
|-------------------|-------------------------|------------------|----------------------|-------------------|
| Sidebar brand (“R” + ChiefRiskBot) | OK — static | On-spec serif mark | Premium, calm brand block | None |
| Sidebar nav (8 links) | OK — each loads correct route; mobile closes drawer on navigate | On-spec | Predictable IA | **Drift:** `href` still `*.html` while browser shows clean URLs — cosmetic inconsistency in markup |
| Sidebar user block (`.who` / `.role`) | OK after `/auth/me` | On-spec | Live workspace + role | See hydration flash above |
| Top bar — hamburger | OK at ≤~600px — opens `.sidebar.open` | On-spec | Mobile-first nav | None observed |
| Top bar — Notifications | Partial — click no visible panel in headless run | On-spec chrome | Inbox or “coming soon” toast | **Cause:** no handler / stub UI; or panel outside asserted selectors |
| Top bar — Help | Partial — same as notifications | On-spec chrome | Docs or modal | Same as notifications |
| Top bar inside `main .content` on some templates | OK functionally | **Drift vs ideal IA** — toolbar reads as “content” not global chrome | Top bar outside scroll region or clearly separated | **Cause:** HTML structure nests `.top` inside `main`; automation first hit “Notifications” as “first content control” |

---

## 4. Home (`/`)

| Element / feature | Functionality (current) | Design (current) | End state (intended) | Failures / causes |
|-------------------|-------------------------|------------------|----------------------|-------------------|
| Greeting / date strip | OK — static demo copy | On-spec editorial | Dynamic date + personalization from API | **Partial:** copy may not match live tenant name everywhere |
| KPI / risk summary strip | OK — static numbers | On-spec numerics | Live portfolio aggregates | **Partial:** demo static until wired to same API as cockpit |
| Latest briefing / events table | OK — table renders | On-spec | Live briefing + cash events | Same static vs live gap |
| CTA “View cockpit” (and similar links) | OK — navigates to `/cockpit` | On-spec accent link | Deep links to freshest risk view | None |

---

## 5. Risk Cockpit (`/cockpit`)

| Element / feature | Functionality (current) | Design (current) | End state (intended) | Failures / causes |
|-------------------|-------------------------|------------------|----------------------|-------------------|
| Page hero + “as of” date | OK | On-spec | As-of tied to data refresh | None |
| Refresh button | OK — same URL after click in smoke | On-spec | Triggers data reload + loading state | **Partial:** not verified that numbers change without backend |
| KPI strip (AUM, P&amp;L, VaR, runway) | OK display | On-spec mono | Live risk engine output | Static demo risk |
| Composition card — segment control (Asset / Sector / Geo) | OK — toggles in place | On-spec | Donut + legend update from API | **Partial:** SVG is present; segment swap not asserted against new data |
| Composition donut (SVG) | OK — visible chart | On-spec | Accessible + keyboard focus if interactive | SVG segments not separate `<button>`s in sample — “click each arc” N/A for basic HTML |
| Risk register / stress table | OK — table layout | On-spec | Sortable, linked to detail | Row drill-down not verified |

---

## 6. Assets (`/assets`)

| Element / feature | Functionality (current) | Design (current) | End state (intended) | Failures / causes |
|-------------------|-------------------------|------------------|----------------------|-------------------|
| Segment toggles (Asset / Sector / Geo) | OK | On-spec | Same as cockpit composition semantics | None |
| Donut / legend | OK | On-spec | Live weights | Static demo |
| “Add position” | Partial — click registered | On-spec CTA | Modal or navigate to editor | **Risk:** full create flow not validated end-to-end in smoke |

---

## 7. Positions / table (`/table`)

| Element / feature | Functionality (current) | Design (current) | End state (intended) | Failures / causes |
|-------------------|-------------------------|------------------|----------------------|-------------------|
| Data grid + numerics | OK | On-spec tabular | Supabase-style editor, validation | Many row links (`~35` in one snapshot) not individually clicked — **coverage gap**, not a failure |
| Upload document | Partial | On-spec | File picker + ingest pipeline | Upload success not asserted (no file attached in headless) |
| Add row / Save / close | Partial — modal path opened in smoke | On-spec | Persisted rows, optimistic UI | **Risk:** save without edit may no-op or error — not asserted |
| Row-level links | Unknown each | On-spec | Custodian / security detail | **Cause of “unknown”:** exhaustive per-row not run |

---

## 8. Briefings (`/briefings`)

| Element / feature | Functionality (current) | Design (current) | End state (intended) | Failures / causes |
|-------------------|-------------------------|------------------|----------------------|-------------------|
| Scope filters (Full / Risk / Assets / Liquidity) | OK — in-place | On-spec pills | Filter list + generator scope | None in smoke |
| Generate | Partial — enters “Generating…” busy state | On-spec | Async job + completion + link to reader | **Risk:** completion, error toast, and timeout UX not fully verified |
| History / list rows | Partial | On-spec | Click row → `/briefing` reader | Depends on data |

---

## 9. Documents (`/documents`)

| Element / feature | Functionality (current) | Design (current) | End state (intended) | Failures / causes |
|-------------------|-------------------------|------------------|----------------------|-------------------|
| Upload | Partial — click OK | On-spec | Queue + status | File pipeline not asserted |
| Review | Partial | On-spec | Opens review UI | Post-click screen not captured in log |
| Table of documents | OK structure | On-spec | Status columns accurate | None |

---

## 10. Liquidity (`/liquidity`)

| Element / feature | Functionality (current) | Design (current) | End state (intended) | Failures / causes |
|-------------------|-------------------------|------------------|----------------------|-------------------|
| Cash / ladder / chart (SVG) | OK — renders | On-spec | Live liquidity model | **Partial:** no extra in-content buttons in smoke — may be read-only demo |
| Tables | OK | On-spec | Drill-down | None |

---

## 11. Settings (`/settings`)

| Element / feature | Functionality (current) | Design (current) | End state (intended) | Failures / causes |
|-------------------|-------------------------|------------------|----------------------|-------------------|
| In-page anchors (`#workspace`, etc.) | OK — URL updates to `/settings#workspace` | On-spec | Section scroll / focus | None |
| Full settings form matrix | Unknown | On-spec dense forms | All prefs persisted | **Cause:** many controls; smoke stopped after first hash link navigation by design |

---

## 12. Extra surfaces (not in main eight-nav shell)

| Element / feature | Functionality (current) | Design (current) | End state (intended) | Failures / causes |
|-------------------|-------------------------|------------------|----------------------|-------------------|
| Scenarios (`/scenarios.html`) | Partial — static page + “View cockpit” works | On-spec | Integrated into nav or removed | **Drift:** filename URL vs clean paths; not linked from primary shell |
| Access (`/access.html`) | Partial — same pattern | On-spec | RBAC management in-product | Same routing drift |
| Briefing reader (`/briefing`) | Partial — “All briefings” returns to list | On-spec reading layout | Deep link from briefings list | **Partial:** reader content depends on `?id` or similar — not fully matrix-tested |

---

## 13. Design system compliance (cross-cutting)

| Element / feature | Functionality (current) | Design (current) | End state (intended) | Failures / causes |
|-------------------|-------------------------|------------------|----------------------|-------------------|
| Typography stack | OK — Fraunces / Inter Tight / JetBrains Mono loaded on sampled pages | On-spec | Same stack everywhere | Material Symbols variant may differ from repo MVP (`Material+Symbols+Outlined` vs outlined opsz) — **minor drift** |
| Color — navy accent | OK on links/CTAs | On-spec | Single accent discipline | None |
| Severity colors for risk | OK where used | On-spec | Only for risk states | None verified as misuse |
| Dark mode | N/A (absent) | On-spec per DESIGN v1 | None | By design |
| Accessibility | Unknown — no axe run in last pass | Target AA | Full keyboard + contrast audit | **Cause:** gap in QA process, not a confirmed violation |

---

## 14. Causes of failure — quick reference

| Symptom | Likely cause | Severity |
|---------|--------------|----------|
| Stuck on login after “success” | Wrong token keys or cleared storage | High — user blocked |
| Console CSP errors | Third-party script blocked by CSP | Low — noise |
| Console 401 | Call without bearer, wrong path, or optional feature | Medium until traced |
| “Aldridge” vs “Whitmore” copy | Static HTML / marketing not synced with demo tenant | Low — trust |
| Notifications / Help appear inert | Stub handlers or missing UI | Medium — perceived broken |
| `.html` vs clean URLs | Routing migration incomplete | Low — SEO/bookmarks |

---

## 15. Maintenance

| Action | Owner |
|--------|--------|
| Re-run automated smoke after each deploy | Engineering |
| Trace 401 in Network + fix or silence | Engineering |
| Unify URL scheme; add e2e for all shell links | Engineering |
| Full accessibility pass (axe + keyboard) | Design / Eng |
| Align all demo copy with live tenant | Product / Content |

*Last updated: automated prod smoke + manual synthesis. Update this file when features ship or regress.*
