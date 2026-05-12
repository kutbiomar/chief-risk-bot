# ChiefRiskBot — Settings field matrix

Status: Active for product remediation  
Last updated: 2026-05-12  
Runtime surface: `frontend-mvp/settings.html`

This matrix removes ambiguity around which Settings controls are editable, which API field they map to, and how persistence should be verified.

## Editable controls

| UI section | Control | Element ID | API field | Type | Verification |
|------------|---------|------------|-----------|------|--------------|
| Workspace / General | Reporting currency | `settings-reporting-currency` | `reporting_currency` | enum: `CHF`, `USD`, `EUR`, `GBP` | Save, reload, selected currency persists and overview card updates. |
| Workspace / General | Briefing day | `settings-briefing-day` | `briefing_day` | enum weekday | Save, reload, selected day persists and cadence overview updates. |
| Workspace / General | Briefing time | `settings-briefing-time` | `briefing_time` | `HH:MM` time string | Save, reload, selected time persists and cadence overview updates. |
| Workspace / General | Recipients | `settings-briefing-recipients` | `briefing_recipients` | comma-separated string | Save, reload, value persists and cadence overview references recipients. |
| Workspace / General | Auto-publish briefings | `settings-auto-publish` | `briefing_auto_publish` | boolean | Save, reload, checkbox persists. |
| Workspace / General | Send PDF attachment | `settings-send-pdf` | `briefing_send_pdf` | boolean | Save, reload, checkbox persists. |
| Workspace / General | Include audit footer | `settings-audit-footer` | `briefing_include_audit_footer` | boolean | Save, reload, checkbox persists. |
| AI / Generation defaults | Model | `settings-ai-model` | `ai_model` | enum: `claude-opus-4-6`, `claude-sonnet-4-5` | Save, reload, selected model persists and AI profile overview updates. |
| AI / Generation defaults | Risk tone | `settings-ai-risk-tone` | `ai_risk_tone` | enum: `conservative`, `balanced`, `aggressive` | Save, reload, selected tone persists and AI profile overview updates. |
| AI / Generation defaults | Custom instructions | `settings-ai-custom-instructions` | `ai_custom_instructions` | string | Save, reload, textarea persists. |
| AI / Generation defaults | Allow draft trade actions | `settings-ai-allow-trade-actions` | `ai_allow_trade_actions` | boolean | Save, reload, checkbox persists and AI profile overview updates. |

## Read-only / support-managed controls

| UI section | Control | Element | Reason |
|------------|---------|---------|--------|
| Support | Contact support | `mailto:support@chiefriskbot.com` | Workspace changes outside the listed editable fields are design-partner assisted in v1. |

## Hash sections

The settings page exposes stable section anchors for smoke tests and support links:

- `#settings-section-workspace`
- `#settings-section-ai`
- `#settings-section-support`

## Persistence contract

The frontend must:

1. Load current values from `GET /settings`.
2. Save the complete editable matrix with `PATCH /settings`.
3. Re-render the returned response from `PATCH /settings`.
4. Preserve hash navigation to the section anchors above.
