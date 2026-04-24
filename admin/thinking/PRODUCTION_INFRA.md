# ChiefRiskBot Production Infrastructure

_Last updated: 2026-04-17_

## 1) Hosting Decision (K3)

- **Backend**: Fly.io (`chiefriskbot-api`) in **EU AMS** (`primary_region = ams`)
- **Frontend**: Cloudflare Pages (`chiefriskbot-app`) with static assets from `frontend-mvp/`
- **Data plane**: Supabase (Postgres + Auth + Storage) in EU region aligned with initial partner base

### Why this stack

- Supabase is already the MVP data/auth/storage backbone, minimizing migration risk.
- Fly provides simple container deployment for FastAPI + WeasyPrint system libs.
- Cloudflare Pages provides low-latency static delivery and native security headers via `_headers`.

### Initial sizing

- Fly app VM: 1 shared CPU / 1024MB RAM / min 1 machine
- Supabase DB tier: start with 2 vCPU equivalent + PITR enabled
- Supabase storage: documents bucket with private ACL and monitored growth

## 2) Secrets & Rotation (K4)

### Source of truth

- Production secrets live in Fly and Cloudflare secret stores only.
- Repo `.env` is local-dev only and must not hold production values.

### Required secrets

- `SECRET_KEY`
- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`
- `ANTHROPIC_API_KEY`
- `FRED_API_KEY`

### Rotation policy

- Rotate high-impact keys (`SECRET_KEY`, Supabase service role, DB credentials) every 90 days.
- Immediate rotation after any suspected leak.
- After rotation: run `scripts/qa_sweep.sh` and confirm `/api/health` is `ok`/`degraded` (no `fail`).

## 3) Domains, TLS, and Edge Security (K5)

- Frontend domain: `app.chiefriskbot.com`
- Backend domain: `api.chiefriskbot.com`
- TLS terminated at host edge (Cloudflare + Fly certs)
- Enforce HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`
- Production CORS allowlist must include only trusted origins (`https://app.chiefriskbot.com`)

## 4) Backup & Restore Drill (K8)

### Baseline policy

- Enable Supabase PITR (point-in-time recovery).
- Daily backup validation required.
- Target **RPO**: 15 minutes
- Target **RTO**: 60 minutes

### Drill template

- Restore latest backup into scratch project.
- Run migrations against scratch.
- Execute `scripts/qa_sweep.sh` against scratch API URL.
- Validate sample login + document upload + briefing PDF export.

### Drill log

| Date | Executor | Restore target | Result | Notes |
|---|---|---|---|---|
| _Pending_ | _TBD_ | Supabase scratch project | _Pending_ | Run before first external partner onboarding |

## 5) Alerting Targets (K10)

- 5xx rate > 1% over 5 minutes
- `/api/health` `fail` for 2 consecutive probes
- Scheduler failures
- Audit logger write failures

Primary channels:

- Ops email distribution list
- On-call channel (Slack/Teams)
