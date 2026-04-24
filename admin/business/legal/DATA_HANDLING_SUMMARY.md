# ChiefRiskBot Data Handling Summary

_Last updated: 2026-04-17_

## What is stored

- User/workspace records
- Portfolio positions and snapshots
- Uploaded source documents and extraction artifacts
- Briefings, risk outputs, and audit logs

## Where it is stored

- Supabase Postgres (application data)
- Supabase Storage private buckets (documents and generated artifacts)
- Host logs/metrics in deployment platforms

## Who can access it

- Authorized users within the same workspace
- Internal operators with production access for support/incident handling
- Subprocessors strictly for infrastructure/runtime needs

## Retention baseline

- Active workspace data retained while service is active
- Deleted/terminated workspace data removed according to contractual retention windows

## Security baseline

- TLS for data in transit
- Private storage buckets
- Session/bearer auth, CSRF protection on mutating cookie-auth routes
- Rate limiting on auth endpoints
- Security headers and strict CORS policy in production
