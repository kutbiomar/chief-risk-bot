# MVP Functionalization Spec

_Last updated: 2026-04-15_

## Functional MVP Scope

The shipped MVP is:

- `login`: real authentication entrypoint
- `onboarding`: first-run portfolio import, optional document upload, risk run, first briefing generation
- `cockpit`: simplified portfolio, downside, liquidity, and active-risk summary
- `liquidity`: 24-month ladder with stress toggle
- `briefings`: list, detail, publish, export
- `positions`: holdings CRUD and portfolio editing
- `documents`: upload, parse, review, approve
- `settings`: workspace, cadence, and AI defaults

The following are not part of the primary MVP story:

- `overlay.html`: internal diagnostics only
- factor-score, regime, and triangulation language on user-facing surfaces
- frontend fixture/demo bypasses

## Architecture Direction

- Frontend stays static vanilla HTML/JS for this phase.
- FastAPI remains the business-logic API.
- Supabase is the target foundation for:
  - Postgres database
  - Auth
  - Storage
- App authorization remains in FastAPI using workspace membership and role checks.

Target auth model:

- Supabase user is the identity source
- app `users` table stores workspace membership, role, and optional Supabase subject linkage
- frontend sends Supabase bearer tokens to FastAPI
- local cookie sessions may remain for development compatibility during transition, but are no longer the target MVP auth story

## Demo Account Policy

- Demo mode is not a separate runtime.
- The demo account signs in through the same auth path as any other user.
- The seeded demo workspace must contain:
  - positions
  - documents
  - liquidity data
  - briefings
  - settings
- Reseeding belongs in admin/dev tooling only.

Demo credentials for local/dev seeding:

- email: `cio@demo.chiefriskbot.com`
- password: `DemoPass2026!`

## Deployment Options

Both frontend hosts remain viable. The frontend must stay host-agnostic, and the backend/API remains a separate deploy from the static frontend.

### Option A: Cloudflare-first

- Frontend: Cloudflare Pages
- Strengths:
  - strong CDN and edge caching
  - low-cost static delivery
  - good fit for a mostly static frontend
- Tradeoffs:
  - env/secrets UX is more platform-specific
  - local parity and previews are slightly less familiar for some teams

### Option B: Netlify-first

- Frontend: Netlify
- Strengths:
  - straightforward preview workflow
  - simpler frontend deployment ergonomics
  - good team UX for marketing-style static sites
- Tradeoffs:
  - fewer edge-native advantages than Cloudflare
  - long-term platform costs can climb as usage grows

### Comparison Criteria

- deploy workflow
- preview ergonomics
- env var and secrets handling
- custom domain and SSL simplicity
- analytics and observability add-ons
- long-term operational simplicity

Current recommendation:

- keep both options open in the decision record
- do not couple the Supabase migration to frontend host choice
- decide frontend host after auth/storage cutover is stable

## Agent Runtime Direction

- Keep FastAPI as the orchestration and authorization layer for all agentic work.
- Keep deterministic math and parsing local:
  - layout parsing
  - VaR
  - liquidity math
  - DB/storage writes
- Target Anthropic Claude Managed Agents for reusable, versioned production agents.
- Expose internal app capabilities to agents through a private MCP layer instead of broad shell/web access.
- Treat `admin/thinking/CLAUDE_AGENT_PLATFORM_SPEC.md` as the working design doc for the agent-platform migration path.
