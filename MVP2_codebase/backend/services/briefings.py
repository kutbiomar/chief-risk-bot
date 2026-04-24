from __future__ import annotations

import html
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.content import WeeklyBriefing
from ..models.deals import Deal
from ..models.reconciliation import ReconciliationFlag
from ..services.alerts import build_alerts
from ..services.bootstrap import get_or_create_workspace_settings
from ..services.liquidity import generate_cash_flow_ladder
from ..services.portfolio.aggregations import summarize_capital_events, summarize_funds, summarize_holdings


class PdfExportUnavailableError(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _week_label(value: datetime) -> str:
    iso = value.isocalendar()
    return f"week-{iso.week}-{iso.year}"


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _build_briefing_payload(workspace_id: str, db: Session) -> dict[str, Any]:
    workspace_settings = get_or_create_workspace_settings(db, workspace_id)
    fund_summary = summarize_funds(workspace_id, db)
    capital_summary = summarize_capital_events(workspace_id, db)
    holdings_summary = summarize_holdings(workspace_id, db)
    alerts = build_alerts(workspace_id, db)
    liquidity = generate_cash_flow_ladder(
        workspace_id,
        db,
        scenario="base",
        base_currency=workspace_settings.base_currency,
    )
    stress_liquidity = generate_cash_flow_ladder(
        workspace_id,
        db,
        scenario="stress",
        base_currency=workspace_settings.base_currency,
    )

    deals = db.scalars(
        select(Deal).where(Deal.workspace_id == workspace_id, Deal.deleted_at.is_(None)).order_by(Deal.created_at.desc())
    ).all()
    open_flags = db.scalars(
        select(ReconciliationFlag).where(
            ReconciliationFlag.workspace_id == workspace_id,
            ReconciliationFlag.status == "open",
        )
    ).all()

    return _json_safe({
        "generated_at": _utc_now().isoformat(),
        "workspace_settings": {
            "base_currency": workspace_settings.base_currency,
            "reporting_timezone": workspace_settings.reporting_timezone,
        },
        "fund_summary": fund_summary,
        "capital_summary": capital_summary,
        "holdings_summary": holdings_summary,
        "alerts": alerts,
        "liquidity": liquidity,
        "stress_liquidity": stress_liquidity,
        "deal_pipeline": [
            {
                "id": deal.id,
                "name": deal.name,
                "stage": deal.stage,
                "target_commitment_base": deal.target_commitment_base,
                "target_close_date": str(deal.target_close_date) if deal.target_close_date else None,
            }
            for deal in deals
        ],
        "open_reconciliation_flags": len(open_flags),
    })


def _build_recommendations(payload: dict[str, Any]) -> list[str]:
    recommendations: list[str] = []
    alerts = payload["alerts"]
    liquidity = payload["liquidity"]
    stress = payload["stress_liquidity"]
    if alerts:
        top = alerts[0]
        recommendations.append(f"Review {top['entity_type']} issue: {top['message']}")
    if liquidity["liquidity_gaps"]:
        first_gap = liquidity["liquidity_gaps"][0]
        recommendations.append(f"Close the base-case liquidity gap projected for {first_gap['month']}.")
    if stress["liquidity_gaps"]:
        recommendations.append("Pressure-test the next 24 months under delayed distributions before the next IC.")
    if payload["open_reconciliation_flags"]:
        recommendations.append("Resolve open reconciliation flags before publishing the weekly pack.")
    if not recommendations:
        recommendations.append("No immediate action items were identified from the current deterministic rules.")
    return recommendations[:4]


def _generate_briefing_output(payload: dict[str, Any]) -> dict[str, Any]:
    fund_summary = payload["fund_summary"]
    capital_summary = payload["capital_summary"]
    holdings_summary = payload["holdings_summary"]
    alerts = payload["alerts"]
    liquidity = payload["liquidity"]

    upcoming_calls = capital_summary["upcoming_calls"][:3]
    top_fund_types = holdings_summary.get("asset_class", [])[:3]
    headline = (
        f"Committed capital totals {fund_summary['total_committed_base']}, with "
        f"{fund_summary['total_uncalled_base']} still unfunded."
    )
    if liquidity["liquidity_gaps"]:
        first_gap = liquidity["liquidity_gaps"][0]
        headline += f" Base-case liquidity falls below target in {first_gap['month']}."
    else:
        headline += " No base-case liquidity gap is currently projected."

    sections = []
    sections.append(
        {
            "title": "Portfolio Posture",
            "body": headline,
        }
    )
    sections.append(
        {
            "title": "Upcoming Capital Flows",
            "body": (
                f"{len(upcoming_calls)} upcoming calls tracked. "
                f"{len(capital_summary['recent_distributions'])} recent distributions recorded."
            ),
        }
    )
    sections.append(
        {
            "title": "Exposure Shape",
            "body": (
                "Top asset buckets: "
                + ", ".join(
                    f"{bucket['label']} ({bucket['pct_of_total'] * 100:.1f}%)"
                    for bucket in top_fund_types
                )
                if top_fund_types
                else "Holdings data is still sparse."
            ),
        }
    )

    return _json_safe({
        "executive_summary": headline,
        "sections": sections,
        "alerts": alerts[:5],
        "recommendations": _build_recommendations(payload),
        "data_caveats": [
            "This briefing uses deterministic placeholder extraction and alert logic where AI workflows are not yet integrated."
        ],
        "source_payload": payload,
    })


def generate_briefing(db: Session, workspace_id: str, user_id: Optional[str]) -> WeeklyBriefing:
    now = _utc_now()
    week_label = _week_label(now)
    current_version = (
        db.scalar(
            select(func.max(WeeklyBriefing.version)).where(
                WeeklyBriefing.workspace_id == workspace_id,
                WeeklyBriefing.week_label == week_label,
            )
        )
        or 0
    )
    payload = _build_briefing_payload(workspace_id, db)
    output = _generate_briefing_output(payload)

    briefing = WeeklyBriefing(
        workspace_id=workspace_id,
        generated_by=user_id,
        version=current_version + 1,
        status="draft",
        week_label=week_label,
        output_json=output,
        model="deterministic-mvp2-briefing",
        input_tokens=0,
        output_tokens=0,
    )
    db.add(briefing)
    db.flush()
    return briefing


def publish_briefing(briefing: WeeklyBriefing, user_id: Optional[str]) -> None:
    briefing.status = "published"
    briefing.published_at = _utc_now()
    briefing.published_by = user_id


def _render_briefing_html(briefing: WeeklyBriefing) -> str:
    output = briefing.output_json or {}
    sections = output.get("sections", [])
    alerts = output.get("alerts", [])
    recommendations = output.get("recommendations", [])
    caveats = output.get("data_caveats", [])

    return f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <title>{html.escape(briefing.week_label)}</title>
        <style>
          body {{ font-family: Georgia, serif; margin: 40px; color: #1b1b1b; }}
          h1, h2 {{ margin-bottom: 0.25rem; }}
          section {{ margin: 24px 0; }}
          ul {{ padding-left: 20px; }}
          .meta {{ color: #555; font-size: 0.95rem; }}
        </style>
      </head>
      <body>
        <h1>ChiefRiskBot Weekly Briefing</h1>
        <p class="meta">{html.escape(briefing.week_label)} · version {briefing.version}</p>
        <section>
          <h2>Executive Summary</h2>
          <p>{html.escape(str(output.get("executive_summary", "")))}</p>
        </section>
        <section>
          <h2>Sections</h2>
          {''.join(f"<h3>{html.escape(str(item.get('title', '')))}</h3><p>{html.escape(str(item.get('body', '')))}</p>" for item in sections)}
        </section>
        <section>
          <h2>Alerts</h2>
          <ul>
            {''.join(f"<li>{html.escape(str(item.get('severity', '')))}: {html.escape(str(item.get('message', '')))}</li>" for item in alerts)}
          </ul>
        </section>
        <section>
          <h2>Recommendations</h2>
          <ul>
            {''.join(f"<li>{html.escape(str(item))}</li>" for item in recommendations)}
          </ul>
        </section>
        <section>
          <h2>Data Caveats</h2>
          <ul>
            {''.join(f"<li>{html.escape(str(item))}</li>" for item in caveats)}
          </ul>
        </section>
      </body>
    </html>
    """


def export_briefing_pdf(db: Session, briefing: WeeklyBriefing, workspace_id: str) -> str:
    output_dir = Path("MVP2_codebase/backend/runtime/briefings") / workspace_id
    output_dir.mkdir(parents=True, exist_ok=True)
    html_text = _render_briefing_html(briefing)

    pdf_path = output_dir / f"{briefing.week_label}_v{briefing.version}.pdf"
    try:
        from weasyprint import HTML

        HTML(string=html_text, base_url=str(output_dir.resolve())).write_pdf(str(pdf_path))
        briefing.pdf_path = str(pdf_path)
        db.flush()
        return str(pdf_path)
    except Exception:
        fallback_path = output_dir / f"{briefing.week_label}_v{briefing.version}.html"
        fallback_path.write_text(html_text, encoding="utf-8")
        briefing.pdf_path = str(fallback_path)
        db.flush()
        return str(fallback_path)
