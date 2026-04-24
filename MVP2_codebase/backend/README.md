# Backend Scaffold

This backend is intended to replace the legacy portfolio-risk domain with a private-markets data model.

## Priority Modules

- `models/`: new domain entities with explicit currency and workspace ownership
- `routers/`: CRUD and summary endpoints for the new private-markets workflows
- `services/extraction/`: document classification and extraction
- `services/portfolio/`: aggregation logic
- `migrations/`: schema creation and RLS-aware evolution

## Key Rules

- Every tenant-owned record must have `workspace_id`.
- Every money field must keep original currency context.
- Liquidity logic must account for deal pipeline and recallable distributions.

## Demo Runtime

- Protected API routes now require a real session cookie or API key by default.
- In development, a demo workspace and admin user are seeded automatically on app startup.
- Workspace settings drive deterministic demo outputs for:
  - `base_currency`
  - `reporting_timezone`
  - `liquidity_buffer_default`
