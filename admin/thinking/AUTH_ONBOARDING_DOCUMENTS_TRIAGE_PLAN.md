# Auth, Onboarding, and Documents Triage Plan

_Created: 2026-04-15_

## Audit Summary

Fresh-workspace testing against the live local app (`localhost:8000` + Supabase-backed backend) shows that the main production path is mostly functional:

- `Create workspace`: works
- `Log in`: works
- `Onboarding CSV upload`: works
- `Onboarding document upload`: works
- `Documents page upload`: works
- `Forgot password request`: works

The confirmed broken flow is:

- `Password reset completion` in `AUTH_MODE=supabase`

Observed behavior:

- `POST /api/auth/reset-password` returns `200`
- logging in with the new password fails with `401 Invalid credentials`
- logging in with the old password still succeeds

Root cause:

- `backend/routers/auth.py` updates `user.password_hash` in the app database
- Supabase-mode login authenticates against Supabase Auth, not the app-local hash
- therefore reset completion currently mutates the wrong credential source

## Product Interpretation

The user-reported document visibility issue does not reproduce as a general upload/storage failure on new workspaces. Uploads are creating:

- a document row in Postgres
- a `supabase://documents/...` storage path in the row
- a visible record in `/api/documents`

The remaining user risk is trust and observability:

- users cannot easily tell which workspace the Documents page is rendering
- uploads from onboarding are now visible, but diagnostics were needed to prove workspace alignment
- password reset currently provides a false-positive success path

## Remediation Plan

### 1. Fix password reset for Supabase auth

Goal:

- make password reset mutate the real credential source when `AUTH_MODE=supabase`

Changes:

- add a backend helper in `backend/services/auth/supabase.py` to update a Supabase Auth user's password through the admin API
- change `backend/routers/auth.py` `reset_password()` to:
  - resolve the app user
  - if auth mode is Supabase and the user has an `auth_subject`, update the password in Supabase first
  - only mark the reset token used after the Supabase password update succeeds
  - keep session revocation in app tables
- preserve the current local-hash path only for `AUTH_MODE=local`

Verification:

- request reset
- complete reset
- old password fails
- new password succeeds
- bearer `/api/auth/session` still resolves the same workspace

### 2. Add explicit post-auth landing feedback

Goal:

- reduce confusion when successful login lands on onboarding instead of cockpit

Changes:

- add a short notice on onboarding for first-run workspaces:
  - `Signed in successfully. Finish setup to unlock the cockpit.`
- keep `resolveAuthenticatedLanding()` behavior, but make the reason obvious in the UI

Verification:

- fresh account sign-in lands on onboarding with visible explanation
- completed account sign-in lands on cockpit

### 3. Keep lightweight workspace diagnostics until auth stabilizes

Goal:

- make workspace mismatches obvious during triage

Changes:

- keep the temporary debug strip on `documents.html` for now
- once auth/reset is stable, downgrade it into:
  - a compact internal diagnostics mode
  - or a hidden `?debug=1` view

Verification:

- Documents page always exposes the currently rendered workspace during triage

### 4. Tighten documents success feedback

Goal:

- make uploads unambiguous without relying on debug UI

Changes:

- keep:
  - `Latest upload` summary card
  - `Open` / `Recent` row badges
  - explicit upload timestamps
- add one stronger success line after upload from the Documents page:
  - `Uploaded to <workspace name> · <filename>`

Verification:

- after upload, the success state names both workspace and file

### 5. Add regression coverage for Supabase auth flows

Goal:

- prevent reintroducing auth drift between app DB and Supabase Auth

Changes:

- add backend tests for:
  - Supabase password reset success path
  - token-use ordering when Supabase update fails
  - old-password invalidation after successful reset
- add browser smoke coverage for:
  - create workspace
  - login
  - onboarding upload
  - documents upload

Verification:

- CI covers the currently observed broken path

## Priority Order

1. Fix Supabase password reset completion
2. Add regression tests for reset behavior
3. Keep workspace diagnostics visible during triage
4. Improve login/onboarding landing messaging
5. Reduce diagnostics back down after auth stabilizes
