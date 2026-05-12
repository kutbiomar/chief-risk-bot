# Continuous Improvement Loop

_Created: 2026-05-12_

Use this loop for repeated agent passes that review and improve the product while keeping the codebase minimal, functional, and readable.

## Operating principles

1. **Fully functional beats decorative.** Every change should move a real user flow, API contract, operational gate, or testable invariant forward.
2. **Smallest coherent slice.** Ship one logical improvement at a time with focused tests and no opportunistic rewrites.
3. **Minimal and elegant.** Prefer existing helpers, schemas, routers, CSS tokens, and patterns. Add abstractions only when they remove real duplication or clarify ownership.
4. **Evidence before confidence.** Use tests, smoke scripts, route checks, screenshots, or logs before declaring a slice done.
5. **Docs stay close to reality.** If behavior or priority changes, update the smallest relevant status doc in the same PR.

## The loop

1. **Review**
   - Read `README.md`, `admin/status/FUNCTIONALITY_ROADMAP.md`, and the files touched by the last PR.
   - Check current branch state with `git status --short --branch`.
   - Look for bugs, stubs, drift, dead code, missing tests, and user-flow gaps.

2. **Select**
   - Pick the highest-value slice that can be completed cleanly.
   - Default priority:
     1. security/trust bugs
     2. broken user flows
     3. production-readiness blockers
     4. missing product capability
     5. maintainability cleanup
   - Keep the slice narrow enough to review by file path and test output.

3. **Plan**
   - State the target behavior, affected files, and validation commands.
   - If a UI change is involved, read `frontend-design-ideal/DESIGN.md` first.
   - If the frontend is involved, resolve whether the change belongs in `frontend/`, `frontend-mvp/`, or both.

4. **Build**
   - Reuse existing patterns and helper APIs.
   - Avoid broad refactors unless they are required for the selected slice.
   - Add comments only where they reduce future search or explain a non-obvious invariant.

5. **Verify**
   - Run the smallest useful checks during development.
   - Before handoff, prefer:
     ```bash
     git diff --check
     node --check frontend/_api.js frontend/_app.js frontend/_shell.js
     python3 -m pytest backend/tests -q
     python3 scripts/check_destructive_migrations.py
     ```
   - Use `scripts/release_check.sh` for release branches or cross-cutting backend/frontend changes.

6. **Record**
   - Commit one logical change.
   - Push the branch.
   - Create or update the PR.
   - Update `FUNCTIONALITY_ROADMAP.md`, `PRODUCTION_READINESS_CHECKLIST.md`, or `STATUS.md` only when the source of truth changed.

## Agent prompt for the next pass

Copy/paste this when you want another improvement cycle:

> Review the repo using `README.md`, `admin/status/FUNCTIONALITY_ROADMAP.md`, and `admin/status/IMPROVEMENT_LOOP.md`. Pick the highest-value small slice that makes ChiefRiskBot more fully functional while keeping code minimal and elegant. Implement it end-to-end, add or update focused tests, run the relevant validation checks, commit, push, and update the PR. Do not start broad refactors; prefer existing patterns and update status docs only if behavior or priorities change.

The same prompt is stored at `admin/status/IMPROVEMENT_LOOP_PROMPT.md` for automation.

## Optional automation wrapper

`admin/agent_improvement_loop.sh` runs the prompt on a fixed interval with a lock so a tick is skipped if a previous task is still running. The script lives under `admin/` so normal app code changes are less likely to touch it.

After each successful agent task, the wrapper requires a clean worktree, pushes the working branch to GitHub, merges that branch into `main`, pushes `main`, and returns to the working branch. If push/merge fails, it asks the agent to review the failure output, implement the smallest safe fix, validate, commit, and retry. If integration still cannot complete within 15 minutes, the wrapper restores the working branch to the commit recorded at the start of that loop iteration, commits a failure log under `admin/status/loop_failures/`, and moves on so the same failed code is not retried blindly.

Example:

```bash
AGENT_LOOP_COMMAND='cursor-agent run --autonomous' \
  admin/agent_improvement_loop.sh
```

Defaults:

- interval: 600 seconds
- max runtime: 259200 seconds (3 days), after which the loop exits and must be invoked again
- post-success git integration: enabled (`AGENT_LOOP_MERGE_TO_MAIN=1`)
- push/merge recovery window: 900 seconds (`AGENT_LOOP_PUSH_RETRY_SECONDS`)
- remote/base: `origin` / `main`
- failure logs: `admin/status/loop_failures/`
- prompt file: `admin/status/IMPROVEMENT_LOOP_PROMPT.md`
- lock directory: `.git/agent-improvement-loop.lock`

Context clearing is runtime-specific. If the agent runtime exposes token-count and clear/compact commands, configure:

```bash
AGENT_CONTEXT_TOKENS_COMMAND='your-token-count-command' \
AGENT_CONTEXT_CLEAR_COMMAND='your-context-clear-command' \
AGENT_CONTEXT_TOKEN_THRESHOLD=200000 \
AGENT_LOOP_COMMAND='cursor-agent run --autonomous' \
  admin/agent_improvement_loop.sh
```

## Definition of done

- The selected behavior works or the documented gap is more truthful than before.
- Tests or smoke checks cover the risky path.
- No generated artifacts or unrelated edits are left in the worktree.
- The PR body lists validation output.
- The next slice remains easy to identify from `FUNCTIONALITY_ROADMAP.md`.
