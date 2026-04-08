# ChiefRiskBot — Full MVP Architecture
*April 2026. Single-tenant family office SaaS. Demo-first build order.*

---

## Why This Architecture

The product has one demo moment: a CIO uploads their portfolio, watches Claude score
their risks in plain language, and sees their VaR computed from their own positions.
The architecture is designed to make that moment work first, then expand outward.

The core constraint is trust. Family offices do not give write access to custodian
accounts to software they don't trust. Every architectural decision — immutable audit
log, single-tenant model, BYOK path, hash-chained events — exists to earn that trust.

---

## Repository Layout

```
chiefrisktbot/
├── backend/
│   ├── main.py                        # FastAPI app, router registration, CORS, lifespan
│   ├── config.py                      # pydantic-settings: all env vars in one place
│   ├── database.py                    # SQLAlchemy engine, session factory, Base
│   ├── deps.py                        # FastAPI dependency injection (get_db, get_current_user)
│   │
│   ├── models/                        # SQLAlchemy ORM (one file per domain)
│   │   ├── workspace.py               # Workspace, ApiKey
│   │   ├── user.py                    # User, Session, Invite
│   │   ├── portfolio.py               # PortfolioSnapshot, Position
│   │   ├── enrichment.py              # PriceCache, MacroCache
│   │   ├── risk.py                    # RiskScore, RiskFlag
│   │   ├── var.py                     # VarResult
│   │   ├── briefing.py                # BriefingRun
│   │   ├── document.py                # Document, ExtractionResult
│   │   ├── source.py                  # DataSource, SyncRun
│   │   └── audit.py                   # AuditEvent
│   │
│   ├── schemas/                       # Pydantic request/response models
│   │   ├── auth.py
│   │   ├── portfolio.py
│   │   ├── risk.py
│   │   ├── var.py
│   │   ├── briefing.py
│   │   ├── document.py
│   │   ├── source.py
│   │   ├── market.py
│   │   ├── members.py
│   │   ├── settings.py
│   │   └── audit.py
│   │
│   ├── routers/                       # FastAPI routers (one per domain)
│   │   ├── auth.py                    # Login, logout, SSO, password reset
│   │   ├── ingest.py                  # CSV upload, document upload
│   │   ├── portfolio.py               # Positions CRUD, summary aggregation
│   │   ├── risk.py                    # Risk scores, flags, run analysis
│   │   ├── var.py                     # VaR computation, history
│   │   ├── cockpit.py                 # Cockpit composite endpoint
│   │   ├── briefing.py                # Generate, list, detail, publish
│   │   ├── documents.py               # Document management, parse, tag
│   │   ├── sources.py                 # Source CRUD, OAuth, sync
│   │   ├── markets.py                 # Prices, sectors, events, movers
│   │   ├── members.py                 # Team management, invites, roles
│   │   ├── settings.py                # Workspace settings, AI config, billing
│   │   ├── audit.py                   # Audit log query, export
│   │   └── onboarding.py             # Onboarding wizard state
│   │
│   ├── services/
│   │   ├── ingest/
│   │   │   ├── csv_parser.py          # CSV → normalized Position list
│   │   │   └── doc_parser.py          # PDF/DOCX → positions via Claude extraction
│   │   ├── enrichment/
│   │   │   ├── market_data.py         # yfinance: prices, returns, 1Y history
│   │   │   ├── macro_data.py          # FRED: rates, VIX, spreads, DXY
│   │   │   └── classifier.py          # Ticker → geo/sector/market_segment
│   │   ├── analytics/
│   │   │   ├── aggregator.py          # AUM by asset class, geo, sector, segment
│   │   │   ├── var_engine.py          # Historical simulation VaR/CVaR
│   │   │   └── concentration.py       # HHI, single-name flags, rules engine
│   │   ├── agents/
│   │   │   ├── base_analyst.py        # Shared scaffolding: prompt, schema, call
│   │   │   ├── concentration_analyst.py
│   │   │   ├── geo_analyst.py
│   │   │   ├── credit_analyst.py
│   │   │   ├── liquidity_analyst.py
│   │   │   └── macro_analyst.py
│   │   ├── briefing/
│   │   │   ├── generator.py           # Orchestrates agents → briefing narrative
│   │   │   └── pdf_export.py          # WeasyPrint server-side PDF
│   │   ├── auth/
│   │   │   ├── password.py            # bcrypt hash/verify
│   │   │   ├── jwt.py                 # Token issue/verify
│   │   │   ├── google_oauth.py        # Google Workspace flow
│   │   │   └── saml.py                # SAML assertion parsing (python3-saml)
│   │   ├── notifications/
│   │   │   └── email.py               # SendGrid/SMTP briefing delivery, invites
│   │   └── audit/
│   │       └── logger.py              # Append AuditEvent + SHA-256 hash chain
│   │
│   ├── workers/                       # Background tasks
│   │   ├── scheduler.py               # APScheduler: weekly briefing cron
│   │   ├── sync_worker.py             # Source sync job
│   │   └── enrichment_worker.py       # Async price/macro refresh
│   │
│   ├── migrations/                    # Alembic migrations
│   │   └── versions/
│   │
│   └── tests/
│       ├── test_ingest.py
│       ├── test_var.py
│       ├── test_agents.py
│       └── test_auth.py
│
├── app/
│   └── static/                        # Existing frontend HTML/CSS/JS (unchanged)
│
├── alembic.ini
├── pyproject.toml
├── .env.example
└── run.sh
```

---

## Database Schema

**Engine:** SQLite for demo/dev. Postgres for production. SQLAlchemy abstracts both.
Change `DATABASE_URL` in `.env` — zero code changes required.

---

### workspaces

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | TEXT | "Aldridge Family Office" |
| slug | TEXT UNIQUE | "aldridge-fo" |
| reporting_currency | TEXT | "USD" |
| timezone | TEXT | "Europe/London" |
| address | TEXT | |
| plan | TEXT | starter \| family_office \| enterprise |
| seat_limit | INT | |
| created_at | TIMESTAMP | |
| deleted_at | TIMESTAMP NULL | soft delete |

---

### users

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| workspace_id | UUID FK → workspaces | |
| email | TEXT UNIQUE | |
| display_name | TEXT | |
| password_hash | TEXT NULL | null if SSO-only |
| role | TEXT | owner \| cio \| analyst \| principal \| auditor \| ops |
| scope | TEXT | "All clients" or specific client name |
| totp_secret | TEXT NULL | for 2FA |
| totp_enabled | BOOL | |
| last_active_at | TIMESTAMP NULL | |
| created_at | TIMESTAMP | |
| disabled_at | TIMESTAMP NULL | |

---

### user_sessions

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| session_family_id | UUID | groups session rotations for logout-all / security events |
| token_hash | TEXT | SHA-256 of session token |
| csrf_secret | TEXT | random secret used for double-submit CSRF token validation |
| device_info | TEXT | user agent / IP |
| last_seen_at | TIMESTAMP NULL | rolling activity timestamp |
| expires_at | TIMESTAMP | |
| created_at | TIMESTAMP | |
| revoked_at | TIMESTAMP NULL | |

---

### invites

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| workspace_id | UUID FK → workspaces | |
| invited_by | UUID FK → users | |
| email | TEXT | |
| role | TEXT | |
| token_hash | TEXT | |
| expires_at | TIMESTAMP | 7 days |
| accepted_at | TIMESTAMP NULL | |
| created_at | TIMESTAMP | |

---

### api_keys

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| workspace_id | UUID FK → workspaces | |
| label | TEXT | "Production", "Read-only" |
| key_type | TEXT | live \| read_only \| webhook |
| key_prefix | TEXT | "crb_live_8e2f" — shown to user |
| lookup_hash | TEXT UNIQUE | SHA-256 of full key for indexed lookup |
| key_hash | TEXT | bcrypt/Argon2id of full key for slow verify after lookup |
| last_used_at | TIMESTAMP NULL | |
| rotated_at | TIMESTAMP NULL | |
| created_at | TIMESTAMP | |
| revoked_at | TIMESTAMP NULL | |

---

### password_reset_tokens

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| token_hash | TEXT | SHA-256 of emailed reset token |
| expires_at | TIMESTAMP | 1 hour |
| used_at | TIMESTAMP NULL | single-use guarantee |
| invalidated_at | TIMESTAMP NULL | set on password change, new reset issuance, or user disable |
| requested_ip | TEXT NULL | abuse/audit signal |
| created_at | TIMESTAMP | |

---

### auth_challenges

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| challenge_type | TEXT | totp \| password_reset_confirm |
| token_hash | TEXT | SHA-256 of opaque challenge token returned to client |
| attempt_count | INT | increment on failed verify |
| max_attempts | INT | default 5 |
| expires_at | TIMESTAMP | default 5 minutes |
| consumed_at | TIMESTAMP NULL | single-use guarantee |
| created_at | TIMESTAMP | |

---

### portfolio_snapshots

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| workspace_id | UUID FK → workspaces | |
| parent_snapshot_id | UUID NULL FK → portfolio_snapshots | prior snapshot when created from manual edit/delete/bulk adjustment |
| uploaded_by | UUID FK → users | |
| source | TEXT | csv \| document \| api_sync |
| source_ref | TEXT NULL | document_id or source_id |
| raw_bytes | BLOB NULL | original file for audit |
| position_count | INT | |
| total_aum_usd | FLOAT | computed at ingest |
| enriched_at | TIMESTAMP NULL | when prices were fetched |
| created_at | TIMESTAMP | |
| is_current | BOOL | only one current per workspace |

---

`portfolio_snapshots` are immutable. Every ingest creates a new snapshot, and every manual
position create/edit/delete against the "current portfolio" materializes a successor snapshot
with `parent_snapshot_id` pointing at the prior current snapshot. Historical analytics always
read by `snapshot_id`; UI edit flows operate on the latest snapshot alias.

---

### positions

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| snapshot_id | UUID FK → portfolio_snapshots | |
| workspace_id | UUID FK → workspaces | (denormalized for query perf) |
| security_id | TEXT NULL | canonical identifier (FIGI / ISIN / CUSIP / internal) |
| ticker | TEXT | |
| name | TEXT NULL | full name from yfinance |
| position_currency | TEXT | original holding currency, e.g. USD / EUR / CHF |
| quantity | FLOAT | |
| price_local | FLOAT NULL | latest price in `position_currency` |
| price_usd | FLOAT NULL | |
| market_value_local | FLOAT NULL | |
| market_value_usd | FLOAT NULL | |
| asset_class | TEXT | controlled vocab |
| geo_region | TEXT NULL | US \| Europe \| EM_Asia \| etc. |
| sector | TEXT NULL | GICS level-1 |
| market_segment | TEXT NULL | Large Cap \| HY Credit \| etc. |
| custodian | TEXT NULL | |
| price_source | TEXT | yfinance \| manual \| document |
| beta_vs_spy | FLOAT NULL | rolling 252-day |
| daily_return | FLOAT NULL | |
| notes | TEXT NULL | |
| override_value | FLOAT NULL | manual override |
| override_by | UUID NULL FK → users | |
| override_at | TIMESTAMP NULL | |
| created_at | TIMESTAMP | |

---

Rows in `positions` are immutable once written because they belong to a specific snapshot.
`POST/PATCH/DELETE /api/portfolio/positions...` mutate the current workspace portfolio by
creating a replacement current snapshot, copying unaffected rows forward, applying the delta,
and flipping `is_current` inside the same transaction.

---

### price_cache

| Column | Type | Notes |
|---|---|---|
| ticker | TEXT PK | |
| currency | TEXT | native quote currency |
| price_local | FLOAT | latest price in native currency |
| price_usd | FLOAT | |
| daily_return_local | FLOAT | native-currency 1D return |
| daily_return_usd | FLOAT | native return translated to workspace reporting currency |
| weekly_return_usd | FLOAT | |
| history_json | TEXT | JSON array of {date, close_local, fx_to_usd, close_usd} for 252 days |
| fetched_at | TIMESTAMP | |
| ttl_hours | INT | default 4 |

---

### fx_cache

| Column | Type | Notes |
|---|---|---|
| pair | TEXT PK | e.g. EURUSD, CHFUSD |
| base_currency | TEXT | |
| quote_currency | TEXT | |
| spot_rate | FLOAT | latest FX rate |
| history_json | TEXT | JSON array of {date, rate} for 252 days |
| fetched_at | TIMESTAMP | |
| ttl_hours | INT | default 4 |

---

### macro_cache

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| workspace_id | UUID FK → workspaces | |
| payload_json | TEXT | full macro context dict |
| fetched_at | TIMESTAMP | |

---

### risk_scores

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| snapshot_id | UUID FK → portfolio_snapshots | |
| workspace_id | UUID FK → workspaces | |
| async_job_id | UUID FK → async_jobs | risk run that produced this row |
| agent | TEXT | concentration \| geo \| credit \| liquidity \| macro |
| dimension | TEXT | same as agent |
| status | TEXT | succeeded \| failed \| timed_out \| skipped |
| score | INT | 1–10 |
| severity | TEXT | watch \| elevated \| priority |
| headline | TEXT | |
| reasoning | TEXT | full paragraph |
| evidence_json | TEXT | JSON array of bullet strings |
| conversation_prompt | TEXT | |
| data_sources_json | TEXT | |
| model | TEXT | claude model used |
| prompt_version | TEXT | prompt template version identifier |
| input_tokens | INT | |
| output_tokens | INT | |
| latency_ms | INT NULL | end-to-end model latency |
| error_message | TEXT NULL | validation/model/runtime failure summary |
| created_at | TIMESTAMP | |

---

### risk_flags

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| snapshot_id | UUID FK → portfolio_snapshots | |
| workspace_id | UUID FK → workspaces | |
| rule | TEXT | e.g. "single_name_concentration" |
| severity | TEXT | watch \| elevated \| priority |
| ticker | TEXT NULL | affected position |
| value | FLOAT | actual value that tripped rule |
| threshold | FLOAT | configured threshold |
| description | TEXT | human-readable |
| created_at | TIMESTAMP | |

---

### var_results

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| snapshot_id | UUID FK → portfolio_snapshots | |
| workspace_id | UUID FK → workspaces | |
| var_1d_95 | FLOAT | |
| var_1d_99 | FLOAT | |
| cvar_1d_95 | FLOAT | |
| cvar_1d_99 | FLOAT | |
| max_drawdown_1y | FLOAT | |
| worst_scenario_date | DATE | |
| worst_scenario_loss | FLOAT | |
| lookback_days | INT | default 252 |
| effective_lookback_days | INT | common overlapping history actually used |
| methodology | TEXT | historical_simulation |
| model_coverage_pct | FLOAT | % of portfolio market value represented by modeled positions |
| unmodeled_value_usd | FLOAT | assets excluded or proxied due to insufficient history |
| position_contributions_json | TEXT | [{ticker, security_id, contribution_pct, contribution_usd, method}] |
| assumptions_json | TEXT | proxy mappings, exclusions, FX assumptions, coverage warnings |
| computed_at | TIMESTAMP | |

---

### briefing_runs

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| workspace_id | UUID FK → workspaces | |
| snapshot_id | UUID FK → portfolio_snapshots | |
| var_result_id | UUID FK → var_results | |
| generated_by | UUID FK → users NULL | null = scheduled job |
| version | INT | incremented on regenerate |
| status | TEXT | draft \| published \| archived |
| week_label | TEXT | "week-14-2026" |
| output_json | TEXT | full briefing JSON |
| model | TEXT | |
| input_tokens | INT | |
| output_tokens | INT | |
| published_at | TIMESTAMP NULL | |
| published_by | UUID NULL FK → users | |
| pdf_path | TEXT NULL | local or S3 path |
| created_at | TIMESTAMP | |

---

### documents

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| workspace_id | UUID FK → workspaces | |
| uploaded_by | UUID FK → users | |
| filename | TEXT | |
| file_type | TEXT | pdf \| csv \| xlsx \| ofx |
| file_size_bytes | INT | |
| sha256 | TEXT | content hash for dedupe/audit |
| storage_path | TEXT | generated server-side path or S3 key; never derived directly from user filename |
| folder | TEXT | custodian_statements \| private_equity \| etc. |
| tag | TEXT NULL | reconciled \| needs_review \| action_required |
| page_count | INT NULL | |
| malware_scan_status | TEXT | pending \| clean \| blocked \| failed |
| extraction_status | TEXT | pending \| processing \| done \| failed |
| extraction_result_id | UUID NULL FK → extraction_results | |
| created_at | TIMESTAMP | |

---

### extraction_results

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| document_id | UUID FK → documents | |
| positions_json | TEXT | extracted positions array |
| raw_text | TEXT | full extracted text |
| confidence_json | TEXT | per-row confidence scores |
| needs_review_count | INT | rows flagged as ambiguous |
| raw_text_truncated | BOOL | true when extraction text exceeded ingest safety cap |
| extracted_row_count | INT | hard-capped parsed row count |
| model | TEXT | |
| input_tokens | INT | |
| output_tokens | INT | |
| created_at | TIMESTAMP | |

---

`extraction_results.positions_json` may contain rows with nullable `ticker`, `security_id`,
`price`, `quantity`, or classification fields until a reviewer approves them. Any response
schema that exposes extracted rows must model those fields as optional plus include confidence
metadata; only approved ingest requests can require a normalized position shape.

Ingest security rules:

- Uploaded files are quarantined until MIME validation, magic-bytes validation, size checks, and malware scan complete.
- `storage_path` is generated from workspace/document ids only; strip path separators and never reuse the raw filename as a filesystem path.
- CSV exports/downloads generated from uploaded content must neutralize spreadsheet formulas for cells beginning with `=`, `+`, `-`, or `@`.
- Document extraction must enforce both raw text size caps and extracted row-count caps before calling the model.
- `raw_text` is stored for audit/debug only and must never be passed verbatim into downstream agent prompts.

---

### data_sources

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| workspace_id | UUID FK → workspaces | |
| name | TEXT | "Charles Schwab" |
| provider | TEXT | schwab \| pershing \| ibkr \| etc. |
| auth_type | TEXT | oauth \| sftp \| upload |
| credential_json | TEXT | encrypted OAuth tokens or SFTP creds |
| last_synced_at | TIMESTAMP NULL | |
| sync_status | TEXT | healthy \| stale \| error \| pending_auth |
| position_count | INT | |
| created_at | TIMESTAMP | |
| revoked_at | TIMESTAMP NULL | |

---

### sync_runs

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| source_id | UUID FK → data_sources | |
| status | TEXT | running \| success \| failed |
| positions_ingested | INT NULL | |
| error_message | TEXT NULL | |
| started_at | TIMESTAMP | |
| completed_at | TIMESTAMP NULL | |

---

### async_jobs

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| workspace_id | UUID FK → workspaces | |
| job_type | TEXT | risk_run \| ingest_enrichment \| document_parse \| source_sync \| workspace_export \| briefing_generate \| audit_export |
| status | TEXT | queued \| running \| succeeded \| failed \| cancelled |
| created_by | UUID NULL FK → users | null = scheduler/system |
| resource_type | TEXT NULL | snapshot \| source \| briefing \| workspace |
| resource_id | UUID NULL | associated object when applicable |
| request_json | TEXT NULL | normalized input payload |
| result_json | TEXT NULL | summary payload or output metadata |
| error_message | TEXT NULL | |
| attempt_count | INT | retry/orchestration attempts |
| started_children | INT NULL | number of parallel sub-tasks launched |
| succeeded_children | INT NULL | completed successful sub-tasks |
| failed_children | INT NULL | completed failed sub-tasks |
| progress_pct | INT NULL | 0-100 for polling UIs |
| started_at | TIMESTAMP NULL | |
| completed_at | TIMESTAMP NULL | |
| created_at | TIMESTAMP | |

---

### audit_exports

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| workspace_id | UUID FK → workspaces | |
| requested_by | UUID NULL FK → users | null = system export |
| async_job_id | UUID FK → async_jobs | |
| storage_path | TEXT | `storage/exports/...` target |
| filter_json | TEXT | filters used for the export |
| expires_at | TIMESTAMP | cleanup deadline |
| created_at | TIMESTAMP | |

---

### audit_events

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| workspace_id | UUID FK → workspaces | |
| sequence_no | BIGINT | monotonic per workspace; unique with workspace_id |
| actor_user_id | UUID NULL FK → users | null = system/cron |
| actor_type | TEXT | user \| system \| api |
| event_type | TEXT | auth \| data_edit \| briefing \| source \| member \| settings |
| action | TEXT | e.g. "published_briefing", "edited_position" |
| subject_type | TEXT | "briefing", "position", "source", etc. |
| subject_id | TEXT | ID of affected resource |
| detail_json | TEXT | before/after diff, extra metadata |
| ip_address | TEXT NULL | |
| device_info | TEXT NULL | |
| prev_hash | TEXT | SHA-256 of previous event (chain) |
| event_hash | TEXT | SHA-256(id + timestamp + action + prev_hash) |
| created_at | TIMESTAMP | IMMUTABLE — never updated |

---

Audit ordering is `(workspace_id, sequence_no)`, not timestamp order. Any mutating request
writes business data plus its `audit_events` row in one transaction, and the response is only
returned after both commit. `sequence_no` is allocated from the workspace-local tail to avoid
ambiguous ordering when multiple writes share the same timestamp.

---

### workspace_settings

| Column | Type | Notes |
|---|---|---|
| workspace_id | UUID PK FK → workspaces | |
| briefing_day | TEXT | "Monday" |
| briefing_time | TEXT | "06:00" |
| briefing_recipients | TEXT | comma-separated emails |
| briefing_auto_publish | BOOL | |
| briefing_send_pdf | BOOL | |
| briefing_include_audit_footer | BOOL | |
| ai_model | TEXT | "claude-opus-4-6" |
| ai_risk_tone | TEXT | conservative \| balanced \| aggressive |
| ai_custom_instructions | TEXT NULL | |
| ai_allow_trade_actions | BOOL | |
| sso_mode | TEXT | disabled \| google \| saml |
| sso_google_hosted_domain | TEXT NULL | restrict Google login domain |
| saml_entity_id | TEXT NULL | IdP entity ID |
| saml_sso_url | TEXT NULL | IdP SSO URL |
| saml_x509_cert | TEXT NULL | PEM cert for assertion validation |
| saml_sp_entity_id | TEXT NULL | SP issuer / entity ID |
| updated_at | TIMESTAMP | |

---

### onboarding_progress

| Column | Type | Notes |
|---|---|---|
| workspace_id | UUID PK FK → workspaces | one row per workspace |
| current_step | INT | |
| completed_steps_json | TEXT | ordered list of completed step numbers |
| skipped_at | TIMESTAMP NULL | |
| updated_at | TIMESTAMP | |

---

### access_requests

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| email | TEXT | |
| name | TEXT NULL | |
| firm_name | TEXT NULL | |
| message | TEXT NULL | |
| source_page | TEXT NULL | landing page source |
| created_at | TIMESTAMP | |

---

For response schemas, fields backed by nullable columns remain nullable in JSON unless an
endpoint explicitly returns a normalized/approved projection. In particular:

- `GET /api/portfolio/positions` and `GET /api/portfolio/positions/{id}` must expose optional
  values for `price_usd`, `market_value_usd`, `geo_region`, `sector`, `market_segment`,
  `daily_return`, `beta_vs_spy`, `notes`, and override fields.
- `GET /api/documents/{id}` must treat `page_count` and `extraction_result_id` as optional.
- `GET /api/auth/session` should return nullable SSO/config fields through `workspace_settings`
  unless that workspace actually enabled them.

---

## Authentication System

### Session Flow (email/password)

```
POST /api/auth/login
  → validate email/password (bcrypt verify)
  → if 2FA enabled: return {requires_totp: true, session_challenge: token}
  → else: create UserSession, set session + csrf cookies, return {session_token?, user}

POST /api/auth/totp/verify
  → verify TOTP code against totp_secret
  → consume auth challenge, create UserSession, set session + csrf cookies, return {session_token?, user}
```

Session tokens are opaque random bytes (32 bytes, base64url). Stored as SHA-256 hash
in `user_sessions`. Never stored in plaintext.

Cookie: `__crb_session` — HttpOnly, SameSite=Strict, Secure in prod.
For API clients: `Authorization: Bearer <token>` header also accepted.

Cookie-authenticated mutating requests must also pass CSRF validation. Use a double-submit token:
issue a readable `__crb_csrf` cookie derived from `user_sessions.csrf_secret`, and require
`X-CSRF-Token` on `POST/PATCH/DELETE`. Bearer-token API clients are exempt because they do not
rely on ambient cookies.

`GET /api/auth/session` should refresh both session expiry and the CSRF cookie when the session
is still valid. `POST /api/auth/logout` revokes the current session and clears both cookies.

The TOTP challenge is not a session. Persist it in `auth_challenges` with a 5-minute TTL,
single-use semantics, and a max-attempt counter. Successful verification consumes the challenge
and creates a normal `user_sessions` row; failed attempts increment `attempt_count` and lock out
the challenge after `max_attempts`.

### Google Workspace OAuth

```
GET  /api/auth/google/authorize → redirect to Google
GET  /api/auth/google/callback  → exchange code, upsert user, create session
```

Restricted to `hd` (hosted domain) if workspace has SSO domain configured.

### SAML SSO

```
GET  /api/auth/saml/metadata → SP metadata XML
POST /api/auth/saml/acs      → assertion consumer, validate + create session
```

Per-workspace SAML config stored in `workspace_settings` and encrypted at rest where it contains
tenant-specific secrets or certificates. Uses `python3-saml`.

### Role-Based Access Control

FastAPI dependencies enforce roles. A `require_role(minimum_role)` dependency factory:

```python
roles_hierarchy = ["auditor", "ops", "principal", "analyst", "cio", "owner"]
```

Any endpoint that modifies data requires `analyst` or above.
Publish briefing requires `cio` or above.
Member management requires `owner`.

The `scope` field on users restricts which client workspaces a user can see
(relevant for multi-family office deployments).

### API Key Auth

API keys use prefix-based routing: `crb_live_` vs `crb_read_`. Read-only keys
reject any mutating request at the dependency layer.

Do not look up API keys by running bcrypt across every row. Instead:
- hash the presented full key with SHA-256 to match `api_keys.lookup_hash`
- fetch the candidate row by indexed lookup
- then verify the presented key against `key_hash`

This preserves slow-hash storage while keeping request-time lookup tractable.

### Password Reset Guarantees

- `POST /api/auth/forgot-password` invalidates any still-open reset token for that user before issuing a new one
- `POST /api/auth/reset-password` requires a non-expired token with both `used_at IS NULL` and `invalidated_at IS NULL`
- successful reset sets `used_at`, rotates all active sessions for that user, and clears all open auth challenges
- disabling a user or changing a password out-of-band sets `invalidated_at` on outstanding reset tokens

---

## Complete API Surface

All endpoints prefixed `/api`. JSON bodies. Errors return `{detail: string}`.

### Auth

```
POST   /api/auth/login                     email + password → session
POST   /api/auth/totp/verify               TOTP code → session
POST   /api/auth/logout                    revoke session
GET    /api/auth/session                   current user + workspace
POST   /api/auth/logout-all                revoke all sessions in session family
POST   /api/auth/forgot-password           send reset email
POST   /api/auth/reset-password            token + new password
GET    /api/auth/google/authorize          redirect to Google
GET    /api/auth/google/callback           Google callback
GET    /api/auth/saml/metadata             SAML SP metadata
POST   /api/auth/saml/acs                  SAML assertion consumer
```

### Ingest

```
POST   /api/ingest/csv                     multipart CSV → snapshot_id
POST   /api/ingest/document                multipart PDF/DOCX/XLSX → document_id
GET    /api/ingest/status/{job_id}         enrichment/import progress
```

### Portfolio

```
GET    /api/portfolio/snapshot             current snapshot summary
GET    /api/portfolio/summary              AUM by all dimensions (asset class, geo, sector, segment)
GET    /api/portfolio/positions            paginated position list (search, filter, sort)
GET    /api/portfolio/positions/{id}       single position detail
POST   /api/portfolio/positions            create manual position
PATCH  /api/portfolio/positions/{id}       edit position (audited)
DELETE /api/portfolio/positions/{id}       remove position
POST   /api/portfolio/positions/bulk       bulk import from parsed document
GET    /api/portfolio/history              snapshot history list
```

`POST /api/ingest/csv`, `POST /api/ingest/document`, `POST /api/risk/run`,
`POST /api/briefings/generate`, `POST /api/sources/{id}/sync`, and
`POST /api/workspace/export` all create an `async_jobs` row and return `job_id` in addition to
the primary resource id when the operation continues asynchronously.

### Risk

```
POST   /api/risk/run                       trigger all 5 agents (async, returns job_id)
GET    /api/risk/status/{job_id}           poll agent job status
GET    /api/risk/scores                    all agent scores for current snapshot
GET    /api/risk/scores/{agent}            single agent score detail
GET    /api/risk/flags                     rules-based flag list
GET    /api/risk/register                  combined scores + flags, sorted by severity
```

### VaR

```
POST   /api/var/compute                    compute/return cached VaR for current snapshot
GET    /api/var/history                    VaR time series (6 weeks) with event markers
GET    /api/var/contributions              position-level marginal VaR contributions
```

### Cockpit

```
GET    /api/cockpit                        composite: KPIs + top risks + var + portfolio donut
```

Single endpoint the cockpit page calls. Aggregates portfolio summary, risk register,
and VaR into one response. Avoids N frontend calls on page load.

### Briefings

```
POST   /api/briefings/generate             run briefing synthesis (returns briefing_id)
GET    /api/briefings                      list (filter: period, status, search)
GET    /api/briefings/{id}                 full briefing document
PATCH  /api/briefings/{id}                 edit draft (version bump)
POST   /api/briefings/{id}/publish         publish + send to recipients
POST   /api/briefings/{id}/regenerate      re-run generation (new version)
GET    /api/briefings/{id}/export/pdf      server-rendered PDF
DELETE /api/briefings/{id}                 archive
```

`GET /api/briefings/{id}` should include:

- the stored briefing body/output
- `portfolio_snapshot` summary used for the briefing sidebar
- `agents_used` or equivalent analyst/model metadata for transparency

### Documents

```
POST   /api/documents/upload               multipart file → document record
GET    /api/documents                      list (folder, tag, search, type)
GET    /api/documents/{id}                 document metadata + extraction status
GET    /api/documents/{id}/preview         first-page thumbnail (PNG)
POST   /api/documents/{id}/parse           (re)trigger extraction
GET    /api/documents/{id}/extraction      extracted positions + confidence
POST   /api/documents/{id}/tag             update tag
POST   /api/documents/{id}/approve         mark extraction as approved
DELETE /api/documents/{id}                 delete
```

`GET /api/documents` should return both the paginated document list and derived `folder_counts`
for the left-nav tree in `documents.html`.

`POST /api/ingest/csv`, `POST /api/ingest/document`, and `POST /api/documents/upload` must reject:

- files larger than the configured cap (demo default 50MB; lower per-type caps are allowed)
- MIME/magic-byte mismatches
- archive or executable formats outside the explicit allow-list
- document paths or filenames containing traversal semantics after normalization

`POST /api/documents/{id}/approve` is the only step allowed to promote extracted rows into the
portfolio import flow when extraction confidence or safety checks flagged the file for review.

### Sources

```
GET    /api/sources                        list all with status
POST   /api/sources/connect/{provider}     initiate OAuth
GET    /api/sources/callback               OAuth callback handler
POST   /api/sources/{id}/disconnect        revoke credentials
POST   /api/sources/{id}/sync              manual sync trigger
GET    /api/sources/{id}/sync-history      past sync runs
GET    /api/sources/providers              list all supported providers
```

### Markets

```
GET    /api/markets/prices                 benchmark strip (SPY, NDX, UST10Y, DXY, VIX, Gold)
GET    /api/markets/macro                  full macro context (FRED series)
GET    /api/markets/sectors                S&P 500 GICS sector heatmap
GET    /api/markets/volatility             VIX + MOVE history (12 months)
GET    /api/markets/events                 macro calendar (this week)
GET    /api/markets/movers                 your positions sorted by daily P&L
```

`GET /api/markets/movers` derives daily P&L from `positions.market_value_usd * positions.daily_return`;
no separate persisted `daily_pnl` column is required.

### Members

```
GET    /api/members                        list all + pending invites
POST   /api/members/invite                 send invite email
GET    /api/members/invites/accept/{token} accept invite (creates user)
PATCH  /api/members/{id}/role              change role
PATCH  /api/members/{id}/scope             change client scope
DELETE /api/members/{id}                   remove member
POST   /api/members/{id}/resend-invite     resend pending invite
```

### Settings

```
GET    /api/settings                       all workspace settings
PATCH  /api/settings/workspace             name, slug, currency, timezone, address
PATCH  /api/settings/briefing              cadence, recipients, auto-publish config
PATCH  /api/settings/ai                    model, tone, custom instructions
GET    /api/settings/api-keys              list API keys (prefix only, never full key)
POST   /api/settings/api-keys              generate new key (returns full key ONCE)
DELETE /api/settings/api-keys/{id}         revoke key
GET    /api/billing/plan                   current plan + seat usage
GET    /api/billing/invoices               invoice history
POST   /api/workspace/export               trigger full data export job
DELETE /api/workspace                      delete workspace (owner only, requires confirm)
```

### Audit

```
GET    /api/audit                          log with filters (type, member, date_range, search)
POST   /api/audit/export                   create filtered CSV export job
GET    /api/audit/export/{id}              download completed CSV export
POST   /api/audit/verify                   verify hash chain integrity
```

### Onboarding

```
GET    /api/onboarding/state               current step + completion status
POST   /api/onboarding/step/{n}/complete   mark step done
POST   /api/onboarding/skip                skip to next step
```

### Public

```
GET    /api/health                         service health check
GET    /api/stats                          public stats (used by index.html)
POST   /api/contact/request-access        lead capture form
```

`GET /api/stats` is computed from aggregate counts and does not require a dedicated table.
`POST /api/contact/request-access` persists to `access_requests`.

---

## Background Jobs

**Scheduler:** APScheduler with SQLite/Postgres jobstore.

| Job | Schedule | Description |
|---|---|---|
| `weekly_briefing` | Mon 06:00 workspace TZ | Run analysis + generate briefing for all workspaces with auto-publish on |
| `price_refresh` | Every 4 hours | Refresh yfinance cache for all active tickers |
| `macro_refresh` | Daily 05:00 UTC | Refresh FRED macro series |
| `source_sync` | Every 6 hours | Re-sync all healthy OAuth sources |
| `stale_session_cleanup` | Daily 03:00 UTC | Delete expired sessions |
| `audit_export_cleanup` | Daily 04:00 UTC | Remove expired export files |

---

## File Storage

**Demo:** Local filesystem at `./storage/`. Structure:

```
storage/
├── documents/{workspace_id}/{document_id}/{filename}
├── exports/{workspace_id}/{export_id}.zip
├── pdf/{workspace_id}/{briefing_id}_v{n}.pdf
└── previews/{document_id}/page1.png
```

**Production path:** Swap to S3-compatible (AWS S3, Cloudflare R2) by implementing
a `StorageBackend` interface. One abstraction layer, two implementations.

---

## Environment Configuration

```env
# Core
DATABASE_URL=sqlite:///./chiefrisktbot.db
SECRET_KEY=<32-byte random>
ENVIRONMENT=development

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-4-6

# Market Data
FRED_API_KEY=...

# Auth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SESSION_TTL_DAYS=30

# Email (briefing delivery, invites)
SENDGRID_API_KEY=...
FROM_EMAIL=briefings@chiefrisktbot.com

# Storage
STORAGE_BACKEND=local
STORAGE_LOCAL_PATH=./storage

# Feature flags (demo vs prod)
ENABLE_SAML=false
ENABLE_OAUTH_SOURCES=false
ENABLE_SCHEDULED_JOBS=true
```

---

## Error Handling Contract

All errors return:
```json
{
  "detail": "Human-readable message",
  "code": "MACHINE_READABLE_CODE",
  "request_id": "uuid"
}
```

HTTP status codes:
- `400` — validation error (bad input)
- `401` — not authenticated
- `403` — authenticated but not authorized
- `404` — resource not found
- `409` — conflict (duplicate, stale state)
- `422` — unprocessable entity (FastAPI default validation)
- `429` — rate limited
- `500` — internal error (logged with request_id for support)
- `503` — dependency unavailable (yfinance down, FRED down)

---

## Tech Stack

| Component | Library | Version |
|---|---|---|
| Framework | FastAPI | 0.115+ |
| ORM | SQLAlchemy 2.0 | |
| Migrations | Alembic | |
| Validation | Pydantic v2 | |
| Config | pydantic-settings | |
| Auth | python-jose (JWT) + passlib (bcrypt) | |
| SAML | python3-saml | |
| Market data | yfinance | |
| FRED | fredapi | |
| PDF extraction | pdfplumber | |
| DOCX extraction | python-docx | |
| PDF export | WeasyPrint | |
| Data processing | pandas + numpy | |
| Async HTTP | httpx | |
| Background jobs | APScheduler | |
| Email | sendgrid | |
| AI | anthropic SDK | |
| Testing | pytest + httpx | |

---

## Build Sequence

Build in this order. Each phase is independently testable.

```
Week 1
  Phase 1: Auth foundations (login, session, CSRF, password reset, dependency injection)
  Phase 2: Core portfolio ingest + async job scaffolding

Week 2
  Phase 3: Market data enrichment (yfinance + FRED)
  Phase 4: Portfolio aggregation (summary endpoint)

Week 3
  Phase 5: VaR engine
  Phase 6: Audit log foundation (logger, event writes, position history path)

Week 4
  Phase 7: Five analyst agents (parallel)
  Phase 8: Cockpit composite endpoint

Week 5
  Phase 9: Briefing synthesis + storage
  Phase 10: Document ingest (PDF/DOCX extraction)

Week 6
  Phase 11: Settings + API keys
  Phase 12: Members + invites
  Phase 13: PDF export
  Phase 14: Weekly briefing scheduler
```

Dependency corrections behind this order:

- `async_jobs` must exist before risk runs, document parsing, and workspace export polling, so job scaffolding ships with core ingest rather than later.
- `price_cache` / `macro_cache` must exist before VaR, cockpit summaries, and agent runs, so enrichment stays ahead of analytics.
- Audit logging now lands before agents, briefings, and document approval flows so mutating/demo-significant actions do not need to reference a logger that does not exist yet.
- Cockpit follows agents but precedes briefing generation because it only depends on portfolio, risk, and VaR outputs.
- Briefing generation precedes PDF export, and PDF export precedes the weekly scheduler, so scheduled briefing delivery never depends on an export path that has not been built.
- Settings move ahead of the scheduler because `workspace_settings` controls briefing cadence, recipients, audit footer, and PDF-send behavior.

Sources OAuth connectors, SAML, and billing are out of scope for demo MVP.
Stubs are fine — the frontend gracefully shows "Coming soon" for unconnected sources.
`/api/billing/*` endpoints are therefore explicit `501` stubs in the demo build and do not
require billing tables before production scope begins.

---

## MVP vs Post-MVP

### In scope for demo

- Email/password auth (single user, no invites needed for demo)
- CSV ingest
- Document ingest (PDF)
- Portfolio aggregation (all dimensions)
- Market data enrichment
- VaR engine
- Five analyst agents
- Briefing generation + storage
- Briefings list + detail
- Positions table CRUD
- Cockpit composite endpoint
- Markets page (yfinance + FRED)
- Audit log (basic — events for key actions)
- Settings (model config, briefing cadence)

### Out of scope for demo (stub endpoints, return 501)

- Sources OAuth connectors (Schwab, Pershing, etc.)
- Members/invites (single-user demo workspace)
- SAML SSO
- Billing
- PDF export (show button, return 501 with "coming soon")
- Audit hash-chain export
- Scheduled briefing delivery via email
- WebSocket real-time price streaming

---

## Security Notes

1. Credentials (OAuth tokens, SFTP passwords) encrypted at rest using Fernet symmetric
   encryption. Key derived from `SECRET_KEY`. Never stored in plaintext.
2. All file uploads validated: MIME type check + magic bytes check, server-side path generation,
   malware/quarantine gate, and per-type size caps. Demo ceiling: 50MB.
3. Position edit endpoints emit AuditEvent before confirming response.
   For snapshot-based edits, the audit event records `parent_snapshot_id`, `new_snapshot_id`,
   and the affected position delta.
4. Session token never logged. `request_id` is logged instead.
5. Rate limiting on auth endpoints: 5 attempts/15 min per IP (`slowapi`).
6. CORS: allow-list only. In dev: localhost:3000, localhost:8080. In prod: configured domain.
7. CSV values that may later be exported to spreadsheets must be stored/rendered with formula-neutralization rules.
8. Extraction jobs enforce maximum raw-text bytes and maximum extracted row counts before model invocation.
