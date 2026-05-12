# ChiefRiskBot — Environments and frontend surfaces

Status: Active for the product-remediation pass  
Last updated: 2026-05-12

This repository currently contains more than one frontend tree. Until the remediation plan says otherwise, use the following ownership model.

## Frontend surfaces

| Path | Role | Change policy |
|------|------|---------------|
| `frontend-mvp/` | Active runtime surface for the current rollout and remediation pass. | Product fixes, smoke coverage, and UI remediation should land here first. |
| `frontend-design-ideal/` | Design-system reference and target aesthetic. | Read before visual changes; do not treat as runtime code. |
| `frontend/` | Legacy/reference surface. | Do not add new remediation work here unless the plan explicitly calls for migration or archival. |

## Auth storage keys

`frontend-mvp/` is the active auth implementation for this pass.

| Key | Storage | Purpose |
|-----|---------|---------|
| `crb.auth_token` | `localStorage` | Persistent auth token when the user chooses a persistent session. |
| `crb.auth_token.session` | `sessionStorage` | Session-only auth token. |
| `crb.auth_storage` | `localStorage` | Remembers whether the active token is persistent or session-only. |
| `crb.user` | `sessionStorage` | Cached user/session display data. |
| `crb.api_base_override` | `localStorage` | Local/staging API override. This is intentionally preserved by logout. |

The legacy `frontend/` tree uses `crb_token`; do not copy that key into new `frontend-mvp/` work without an explicit migration plan.

## Logout invariant

Logout must clear active auth/session keys and workspace-local state while preserving `crb.api_base_override` so local and staging smoke runs can return to the same API target.
