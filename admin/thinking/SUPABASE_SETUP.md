# Supabase Setup

_Last updated: 2026-04-15_

## Where To Put Credentials

Place Supabase credentials in the repo-root `.env` file:

- `/Users/omarkutbi/Documents/Claude/Projects/Chief risk bot/.env`

The backend reads this file through `backend/config.py`.

Required entries for Supabase mode:

```env
AUTH_MODE=supabase
DATABASE_URL=postgresql+psycopg://postgres:[YOUR_DB_PASSWORD]@[YOUR_PROJECT_REF].supabase.co:5432/postgres
SUPABASE_URL=https://[YOUR_PROJECT_REF].supabase.co
SUPABASE_ANON_KEY=[YOUR_SUPABASE_ANON_KEY]
SUPABASE_SERVICE_ROLE_KEY=[YOUR_SUPABASE_SERVICE_ROLE_KEY]
SUPABASE_STORAGE_BUCKET=documents
ALLOWED_ORIGINS=http://localhost:8000,http://localhost:3000,http://localhost:8080
```

Notes:

- `DATABASE_URL` should point to the Supabase Postgres instance when you want the app database on Supabase.
- The frontend currently does not need separate Supabase env vars because auth still flows through FastAPI.
- Keep `SUPABASE_SERVICE_ROLE_KEY` backend-only. Do not expose it in frontend code.

## Where To Find Each Value In Supabase

### 1. Project URL and API keys

Supabase dashboard:

- `Project Settings` -> `API`

Copy:

- `Project URL` -> `SUPABASE_URL`
- `anon public` key -> `SUPABASE_ANON_KEY`
- `service_role` key -> `SUPABASE_SERVICE_ROLE_KEY`

### 2. Database URL

Supabase dashboard:

- `Project Settings` -> `Database`

Use the connection string for direct Postgres access. Format it into:

```env
DATABASE_URL=postgresql+psycopg://postgres:[PASSWORD]@[HOST]:5432/postgres
```

If Supabase gives you a URI with `postgresql://`, keep the same host, database, username, and password but use the SQLAlchemy driver form above if needed by the runtime.

### 3. Storage bucket

Supabase dashboard:

- `Storage`

Create a bucket named:

- `documents`

Or set `SUPABASE_STORAGE_BUCKET` to a different bucket name in `.env`.

## Minimum Supabase Checklist

- Create the Supabase project
- Create the `documents` bucket
- Enable email/password auth
- Create the demo auth user:
  - `cio@demo.chiefriskbot.com`
  - `DemoPass2026!`
- Put the credentials into repo-root `.env`
- Point `DATABASE_URL` to Supabase Postgres
- Run migrations
- Reseed the demo workspace

## Local Bring-Up After Credentials Are In Place

From the repo root:

```bash
.venv/bin/alembic -c backend/alembic.ini upgrade head
.venv/bin/python admin/demo/seed_demo.py
.venv/bin/uvicorn backend.main:app --port 8001 --reload
node .claude/serve.js
```

Then sign in at:

- `http://localhost:8000/login.html`

With:

- `cio@demo.chiefriskbot.com`
- `DemoPass2026!`

## What Still Needs Manual Supabase Work

- Provision the auth user in Supabase Auth
- confirm the Postgres connection string
- confirm the storage bucket exists
- later: migrate existing local users/workspaces into Supabase-backed production data
