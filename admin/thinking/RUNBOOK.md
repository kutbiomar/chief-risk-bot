# ChiefRiskBot Operations Runbook

_Last updated: 2026-04-17_

## Restart backend

1. Confirm current release SHA in deployment logs.
2. Restart Fly app machine:
   - `flyctl machine restart <machine-id> --app chiefriskbot-api`
3. Verify:
   - `GET /api/health`
   - Login flow
   - One protected endpoint (`/api/cockpit`)

## Run migrations

1. Ensure deploy is paused.
2. Run:
   - `scripts/migrate.sh`
3. If migration fails, stop rollout and restore previous release.

## Reseed demo workspace

1. Confirm the intended target before running any mutating command.
2. Run a dry run first. Local example:
   - `DATABASE_URL=sqlite:///./backend/runtime/chiefriskbot.db AUTH_MODE=local .venv/bin/python admin/demo/seed_demo.py --target local --confirm-target sqlite --dry-run`
3. If the dry run points at the expected database, run the seed. Local example:
   - `DATABASE_URL=sqlite:///./backend/runtime/chiefriskbot.db AUTH_MODE=local .venv/bin/python admin/demo/seed_demo.py --target local --confirm-target sqlite`
4. For staging, set staging `DATABASE_URL`/`AUTH_MODE` explicitly and confirm the staging DB host:
   - `.venv/bin/python admin/demo/seed_demo.py --target staging --confirm-target <staging-db-host> --dry-run`
   - `.venv/bin/python admin/demo/seed_demo.py --target staging --confirm-target <staging-db-host>`
5. Production reseeding is blocked unless the command includes both:
   - `--target production --confirm-target <production-db-host>`
   - `--confirm-production-seed seed-production-demo`
6. Verify demo login and seeded documents/briefings.

## Rotate secrets

1. Rotate upstream provider credentials (Supabase, Anthropic, FRED).
2. Update Fly and Cloudflare secret stores.
3. Redeploy backend/frontend.
4. Run `scripts/qa_sweep.sh`.

## Restore from backup

1. Trigger Supabase PITR restore to a scratch project.
2. Run migrations on restored DB.
3. Point staging backend to restored DB for smoke tests.
4. Promote restore path only after QA sign-off.

## Incident response

1. Open incident channel and assign incident commander.
2. Freeze deploys.
3. Capture:
   - error logs
   - recent deploy SHA
   - `/api/health` output
4. Mitigate (rollback or hotfix).
5. Publish incident summary and follow-up actions.

## Support contacts (pointers only)

- Supabase support: project dashboard support panel
- Anthropic support: account support portal
- Fly support: org support channel
- Cloudflare support: account support center

## Credentials location policy

- Production secrets: Fly/Cloudflare secret stores
- Local development secrets: repo `.env` (non-production only)
- Never store raw production secrets in git-tracked files
