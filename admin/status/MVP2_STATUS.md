# MVP2 Status — ARCHIVED

_Last updated: 2026-04-09_  
_Archived: 2026-04-13_

**See `STATUS.md` for current project status.**

This file is kept for historical reference only.
Phases E–J have been completed since 2026-04-09.
All blocking issues listed below are now fixed and tested.

---

## Archived: Phase G blocking issues (NOW FIXED)

These 9 items were blocking on 2026-04-09 but are now resolved:

- ✅ G1: TOTP bypass — disabled, tests added
- ✅ G2: Default `SECRET_KEY` — validation added
- ✅ G3: CSRF missing — enforced on all mutating routes + regression tests
- ✅ G4: Snapshot race — atomic unique-current guard + DB constraint
- ✅ G5: API key resolution — resolves to key owner via `user_id` FK
- ✅ G6: N+1 queries — batch fetch on hot paths
- ✅ G7: Workspace isolation — cross-workspace tests added
- ✅ G8: No unauthenticated tests — 401 regression tests added
- ✅ G9: Asyncio crash — pipeline moved to async background jobs

**See `codex_log` Phase G Closeout (2026-04-10) for verification.**

---

## What happened since 2026-04-09

- **Phase H:** Demo QA, CSS path fix, operational validation
- **Phase I:** Liquidity backend/frontend (24-month cashflow chart, stress scenarios)
- **Phase J:** Demo mode switch (offline fixtures, toggle in nav, no backend required)
- **Phase G follow-ups:** Audit log retry logic, briefing quality gate, design polish
- **2026-04-15 functionalization:** frontend fixture runtime removed, Supabase auth/storage bridge added, Supabase Postgres migrations applied, and the real demo account/workspace seeded and verified

**Result:** This file remains historical. The project has since moved beyond the offline demo posture and is now being cut over to a functional Supabase-backed MVP. See `STATUS.md` for the live state.
