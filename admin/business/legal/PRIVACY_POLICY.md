# ChiefRiskBot Privacy Policy (MVP Draft)

_Last updated: 2026-04-17_

## 1. Data collected

- Account identity data: email, display name, workspace metadata
- Portfolio data: positions, classifications, values, currencies
- Documents: uploaded PDFs/DOCX/XLSX and extracted metadata
- System telemetry: request logs, error traces, audit metadata

## 2. Data use

We process data to authenticate users, generate risk analytics, support document workflows, and operate/improve service reliability.

## 3. Processors and storage

- Supabase: authentication, database, and object storage
- Anthropic API: model inference for selected risk/document tasks
- Fly.io / Cloudflare: hosting and delivery

## 4. AI processing posture

Anthropic API usage follows provider policy for business API traffic; customer inputs are processed for inference and are not used by us for unrelated model training.

## 5. Access controls

Workspace-level authorization is enforced by FastAPI session/bearer auth with role-bound access.

## 6. Retention

Data is retained for active workspaces unless deletion is requested or contractual retention terms require earlier removal.

## 7. Security controls

TLS in transit, private storage buckets, service-side access controls, and operational monitoring are used to protect data.

## 8. User rights

Design partners may request export, correction, or deletion of their workspace data under contract and applicable law.

## 9. Contact

Privacy requests should be routed through designated support channels in the partner agreement.
