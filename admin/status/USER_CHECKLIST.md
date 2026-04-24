# User Checklist — Phase K Execution Unblockers

_Last updated: 2026-04-21_

These are items **only you can do** (accounts, credentials, billing, legal sign-off). Claude/Codex handles the code and CLI work in parallel. Do these in any order unless marked BLOCKING — those gate Claude's next step.

When you finish an item, drop the values into a local scratch file (do NOT commit) and let Claude know. Claude will pull them, apply via CLI, then delete the scratch file.

---

## 1. Domain + DNS  (BLOCKING EX5)

- [ ] Confirm which registrar holds `chiefriskbot.com` (Cloudflare Registrar / Namecheap / GoDaddy / etc.)
- [ ] Record the login location in 1Password (or equivalent) — tell Claude the 1Password item name so it can be referenced in `RUNBOOK.md`
- [ ] If nameservers are **not** already pointing at Cloudflare, move them now (registrar → Cloudflare nameservers). Takes up to 24h to propagate — start early.
- [ ] Confirm renewal auto-renew is ON and expiry is >12 months out

## 2. Fly.io  (BLOCKING EX2)

- [ ] Create Fly.io account at https://fly.io (if not already)
- [ ] Add a payment method (required even for free tier — Fly wants a card on file)
- [ ] Create an organization if you want this separate from personal (optional)
- [ ] Generate a Fly API token: `flyctl auth token` after login, OR via https://fly.io/user/personal_access_tokens
- [ ] Hand Claude:
  - Fly account email
  - Org name (or "personal")
  - `FLY_API_TOKEN`

## 3. Cloudflare  (BLOCKING EX3, EX5)

- [ ] Create Cloudflare account (if not already)
- [ ] Add the `chiefriskbot.com` zone to Cloudflare
- [ ] Generate an API token at https://dash.cloudflare.com/profile/api-tokens with scopes:
  - Account → Cloudflare Pages: Edit
  - Zone → DNS: Edit (scoped to `chiefriskbot.com`)
  - Zone → Zone: Read
- [ ] Find your Account ID (right sidebar on any zone page in the dashboard)
- [ ] Hand Claude:
  - `CLOUDFLARE_API_TOKEN`
  - `CLOUDFLARE_ACCOUNT_ID`

## 4. Supabase  (BLOCKING EX4)

- [ ] Confirm the single production Supabase project name/region
- [ ] From Project Settings → API, grab:
  - `SUPABASE_URL` (Project URL)
  - `SUPABASE_ANON_KEY` (anon public key)
  - `SUPABASE_SERVICE_ROLE_KEY` (service role — keep private)
  - `SUPABASE_JWT_SECRET` (JWT Secret)
- [ ] From Project Settings → Database, grab the **pooled** connection string (port 6543, not 5432) — this becomes `DATABASE_URL`. Append `?sslmode=require`.
- [ ] Confirm Storage bucket `documents` exists and is **private** (no public access toggle)
- [ ] Hand Claude all five values above

## 5. Production API keys  (BLOCKING EX4)

These should be NEW keys dedicated to prod (not your dev keys):

- [ ] **Anthropic**: create a new API key at https://console.anthropic.com/settings/keys, label it `chiefriskbot-prod`. Confirm billing is active and a monthly spend cap is set (recommend $50–100 for initial partner usage).
- [ ] **FRED**: if your existing key is personal, that's fine — FRED is keyed per user and has no rate tiers worth isolating. Just confirm you have one at https://fred.stlouisfed.org/docs/api/api_key.html
- [ ] Hand Claude both values

## 6. GitHub repo secrets  (BLOCKING EX7)

Once Fly + Cloudflare + Supabase values exist, you'll need to add them as GH Actions secrets so `.github/workflows/ci-cd.yml` can deploy:

- [ ] Go to repo → Settings → Secrets and variables → Actions
- [ ] Add these secrets (Claude will give you the values from the CLI work):
  - `FLY_API_TOKEN`
  - `CLOUDFLARE_API_TOKEN`
  - `CLOUDFLARE_ACCOUNT_ID`
  - `SUPABASE_DB_URL` (same pooled connection string as above)
- [ ] Save. Confirm each appears in the list (values will show as hidden).

_Claude can't add GH secrets for you without a PAT with admin scope. Easiest path is you paste them into the GH UI directly._

## 7. Backup storage — Cloudflare R2  (BLOCKING EX8)

Since you're staying on Supabase free tier, we need a target for nightly `pg_dump`:

- [ ] In Cloudflare dashboard → R2 → enable R2 (free tier: 10GB storage, Class B ops free)
- [ ] Create bucket `chiefriskbot-backups` (private)
- [ ] Create an R2 API token (R2 → Manage API Tokens → Create API Token, scope to the bucket)
- [ ] Hand Claude:
  - `R2_ACCOUNT_ID` (same as Cloudflare account ID)
  - `R2_ACCESS_KEY_ID`
  - `R2_SECRET_ACCESS_KEY`
  - bucket name: `chiefriskbot-backups`

## 8. Support inbox + alerting email  (K19, K10)

- [ ] Create `support@chiefriskbot.com` — options:
  - Google Workspace (simplest, ~$6/user/mo)
  - Cloudflare Email Routing → forward to your personal inbox (free, good for v1)
- [ ] Create `alerts@chiefriskbot.com` similarly (or route to same inbox)
- [ ] Set up an auto-ack on `support@` ("We've received your message, we'll respond within 1 business day")
- [ ] Tell Claude the routing setup so it goes into `RUNBOOK.md`

## 9. Legal — your review  (not blocking, but do before first partner)

- [ ] Read `admin/business/legal/privacy-policy.md`
- [ ] Read `admin/business/legal/terms-of-service.md`
- [ ] Read `admin/business/legal/data-handling-summary.md`
- [ ] Flag anything that needs a lawyer's eye. These are Claude-drafted starting points, not lawyer-approved. For first design partner + CTO: probably fine. For paying customers: get a lawyer.

## 10. Onboarding collateral  (not blocking, parallel)

- [ ] Read `admin/business/onboarding/getting-started.md`
- [ ] Decide if you want to record the 3-minute Loom walkthrough yourself (recommended — founder-voiced) or have Claude script it for you to read

---

## What Claude does while you're doing the above

In parallel, with no dependencies on your inputs:

1. Install `flyctl`, `wrangler`, `supabase` CLI locally if missing
2. Dry-run `alembic upgrade --sql` against the current DB to catch any destructive migration before prod touches it
3. Write `.github/workflows/backup.yml` (nightly `pg_dump` → R2) — ready to activate when #7 is done
4. Tighten `backend/config.py` prod assertions: `SECRET_KEY != "replace-me"`, `ENV=production` requires `ALLOWED_ORIGINS` to be set, fail-fast on missing Supabase envs
5. Add a production smoke-check script (`scripts/prod_smoke.sh`) the CI runs post-deploy
6. Draft the prod secrets population script (no values, just the shape) so population is a one-shot `bash scripts/set_fly_secrets.sh < scratch.env` when your values land
7. Pre-provision a "first design partner" workspace seed script variant (`admin/demo/seed_partner.py`) so onboarding is one command when the partner is named

---

## Fast path (what to do FIRST if you only have 30 minutes today)

1. Section 2 (Fly token) — 5 min
2. Section 3 (Cloudflare token + account ID) — 5 min
3. Section 4 (Supabase keys) — 5 min
4. Section 5 (Anthropic prod key, spend cap) — 5 min
5. Drop all values into a scratch file, tell Claude
6. Claude runs EX2 → EX4 in one session

Sections 1, 7, 8 can wait a day. Sections 9, 10 wait until first partner is named.
