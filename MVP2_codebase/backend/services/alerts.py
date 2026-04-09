from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .liquidity import generate_cash_flow_ladder
from .portfolio.aggregations import summarize_funds
from ..models.capital import CapitalEvent
from ..models.funds import Commitment, Fund
from ..models.reconciliation import ReconciliationFlag


def build_alerts(workspace_id: str, db: Session) -> list[dict]:
    now = datetime.now(timezone.utc)
    alerts: list[dict] = []

    events = db.scalars(
        select(CapitalEvent).where(CapitalEvent.workspace_id == workspace_id, CapitalEvent.deleted_at.is_(None))
    ).all()
    for event in events:
        if event.type != "call" or not event.due_date:
            continue
        days_until_due = (event.due_date - now.date()).days
        if days_until_due < 14:
            alerts.append(
                {
                    "rule": "capital_call_due_14d",
                    "severity": "critical",
                    "entity_id": event.id,
                    "entity_type": "capital_event",
                    "message": f"Capital call due in {days_until_due} days",
                    "created_at": now,
                }
            )
        elif days_until_due < 30:
            alerts.append(
                {
                    "rule": "capital_call_due_30d",
                    "severity": "high",
                    "entity_id": event.id,
                    "entity_type": "capital_event",
                    "message": f"Capital call due in {days_until_due} days",
                    "created_at": now,
                }
            )

    commitments = db.scalars(
        select(Commitment).where(Commitment.workspace_id == workspace_id, Commitment.deleted_at.is_(None))
    ).all()
    funds = {
        fund.id: fund
        for fund in db.scalars(
            select(Fund).where(Fund.workspace_id == workspace_id, Fund.deleted_at.is_(None))
        ).all()
    }
    total_committed = sum((c.committed_amount_base or c.committed_amount or Decimal("0")) for c in commitments)
    manager_totals: dict[str, Decimal] = {}
    fund_totals: dict[str, Decimal] = {}
    for commitment in commitments:
        amount = commitment.committed_amount_base or commitment.committed_amount or Decimal("0")
        fund_totals[commitment.fund_id] = fund_totals.get(commitment.fund_id, Decimal("0")) + amount
        manager = funds.get(commitment.fund_id).manager_name if funds.get(commitment.fund_id) else "Unknown"
        manager_totals[manager] = manager_totals.get(manager, Decimal("0")) + amount

    for fund_id, amount in fund_totals.items():
        if total_committed and amount / total_committed > Decimal("0.30"):
            alerts.append(
                {
                    "rule": "single_fund_concentration",
                    "severity": "elevated",
                    "entity_id": fund_id,
                    "entity_type": "fund",
                    "message": "Single fund exceeds 30% of total committed capital",
                    "created_at": now,
                }
            )

    for manager_name, amount in manager_totals.items():
        if total_committed and amount / total_committed > Decimal("0.40"):
            alerts.append(
                {
                    "rule": "single_manager_concentration",
                    "severity": "elevated",
                    "entity_id": manager_name,
                    "entity_type": "manager",
                    "message": "Single manager exceeds 40% of total committed capital",
                    "created_at": now,
                }
            )

    open_flags = db.scalars(
        select(ReconciliationFlag).where(
            ReconciliationFlag.workspace_id == workspace_id,
            ReconciliationFlag.status == "open",
        )
    ).all()
    if open_flags:
        alerts.append(
            {
                "rule": "open_reconciliation_flags",
                "severity": "info",
                "entity_id": None,
                "entity_type": "reconciliation",
                "message": f"{len(open_flags)} reconciliation flags need review",
                "created_at": now,
            }
        )

    summary = summarize_funds(workspace_id, db)
    if summary["total_called_base"] and summary["total_uncalled_base"] > summary["total_called_base"] * Decimal("0.50"):
        alerts.append(
            {
                "rule": "uncalled_commitments_watch",
                "severity": "watch",
                "entity_id": None,
                "entity_type": "portfolio",
                "message": "Uncalled commitments exceed 50% of called capital",
                "created_at": now,
            }
        )

    ladder = generate_cash_flow_ladder(workspace_id, db, scenario="base")
    if ladder["liquidity_gaps"]:
        first_gap = ladder["liquidity_gaps"][0]
        alerts.append(
            {
                "rule": "liquidity_gap",
                "severity": "high",
                "entity_id": first_gap["month"],
                "entity_type": "liquidity_projection",
                "message": first_gap["description"],
                "created_at": now,
            }
        )

    return sorted(alerts, key=lambda item: (item["severity"], item["created_at"]), reverse=True)
