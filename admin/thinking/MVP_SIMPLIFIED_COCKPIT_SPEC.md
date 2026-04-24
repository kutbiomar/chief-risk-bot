# MVP Simplification — Cockpit Revision

_Date: 2026-04-15_

## Decision

ChiefRiskBot's active MVP should stop presenting the macro overlay as a user-facing feature.
The overlay may remain in the backend as internal analytics infrastructure, but it is no longer
part of the MVP product story, MVP navigation, or MVP cockpit.

## Updated MVP Product Scope

The MVP is a private-markets workflow for three user jobs:

- Get portfolio data into the system quickly.
- Understand risk and liquidity at a glance.
- Produce a clean weekly briefing for the investment committee.

## Removed From MVP UI

- Macro Overlay page
- AUM triangulation in the cockpit
- Regime labels in the cockpit
- Factor-scoring tables in the cockpit
- Overlay refresh action in the cockpit
- Overlay-specific vocabulary in primary user-facing copy

## Simplified Cockpit Spec

The cockpit should answer four questions immediately:

1. What is the portfolio worth?
2. How much could it lose on a bad normal day?
3. Has risk worsened or improved since the last read?
4. What needs attention right now?

### Cockpit Structure

- Portfolio snapshot
- Liquidity summary
- Portfolio mix
- Risk at a glance
- Active risk register

### Risk At A Glance Card

This card replaces the dense VaR contributor panel and all overlay content.

It should contain:

- A plain-English headline using 95% 1-day VaR
- A compact visual showing:
  - bad normal day (`VaR 95%`)
  - more severe day (`VaR 99%`)
  - worst modeled day
- A short comparison sentence:
  - what the severe case looks like
  - what the worst modeled day was
- Top 3 drivers phrased as positions pushing current downside

### Copy Rules

- Prefer "bad normal day" over pure quant jargon
- Keep technical labels secondary, not primary
- Avoid "overlay", "triangulation", and "regime" in MVP UI
- Every major metric should have a plain-language interpretation

## MVP Navigation

- Onboarding
- Risk Cockpit
- Liquidity
- Briefings
- Settings
- Positions
- Documents

## Implementation Plan

### Phase 1 — UX simplification

- Remove Overlay from active sidebar navigation
- Remove overlay section from cockpit
- Remove overlay action buttons from cockpit
- Rewrite cockpit hero copy in plain English

### Phase 2 — VaR simplification

- Replace VaR metric toggles with a single "Risk at a glance" panel
- Add a compact visual bar chart for 95%, 99%, and worst modeled loss
- Add plain-English summary copy
- Show only the top three downside contributors

### Phase 3 — Doc alignment

- Record the simplified MVP scope in repo docs
- Update frontend audit/status docs where they describe overlay as part of the active MVP

## Non-goals

- Removing overlay code from the backend
- Rewriting the risk engine
- Changing existing data contracts unless needed for clarity
- Redesigning the ideal platform artifacts in `frontend-design-ideal/`
