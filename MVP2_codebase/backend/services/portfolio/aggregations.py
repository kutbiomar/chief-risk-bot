from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.capital import CapitalEvent
from ...models.funds import Commitment, Fund
from ...models.holdings import Holding


def summarize_funds(workspace_id: str, db: Session) -> dict:
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
    total_called = sum((c.called_capital_base or c.called_capital or Decimal("0")) for c in commitments)
    total_uncalled = sum((c.uncalled_capital_base or c.uncalled_capital or Decimal("0")) for c in commitments)
    total_distributions = sum(
        (c.distributions_received_base or c.distributions_received or Decimal("0")) for c in commitments
    )

    grouped: dict[str, dict[str, Decimal | int]] = defaultdict(
        lambda: {"value_base": Decimal("0"), "item_count": 0}
    )
    for commitment in commitments:
        fund = funds.get(commitment.fund_id)
        label = fund.type if fund else "Unknown"
        grouped[label]["value_base"] += commitment.nav_base or commitment.committed_amount_base or commitment.committed_amount or Decimal("0")
        grouped[label]["item_count"] += 1

    by_fund_type = []
    for label, payload in grouped.items():
        value_base = payload["value_base"]
        pct = float(value_base / total_committed) if total_committed else 0.0
        by_fund_type.append(
            {
                "label": label,
                "value_base": value_base,
                "pct_of_total": pct,
                "item_count": payload["item_count"],
            }
        )

    by_fund_type.sort(key=lambda item: item["value_base"], reverse=True)
    return {
        "total_committed_base": total_committed,
        "total_called_base": total_called,
        "total_uncalled_base": total_uncalled,
        "total_distributions_base": total_distributions,
        "by_fund_type": by_fund_type,
    }


def summarize_capital_events(workspace_id: str, db: Session) -> dict:
    events = db.scalars(
        select(CapitalEvent).where(
            CapitalEvent.workspace_id == workspace_id,
            CapitalEvent.deleted_at.is_(None),
        )
    ).all()

    upcoming_calls = []
    recent_distributions = []
    for event in events:
        amount = event.amount_base or event.amount
        payload = {
            "id": event.id,
            "fund_id": event.fund_id,
            "type": event.type,
            "amount_base": amount,
            "due_date": event.due_date,
            "effective_date": event.effective_date,
            "is_confirmed": event.is_confirmed,
        }
        if event.type == "call":
            upcoming_calls.append(payload)
        if event.type in {"distribution", "recallable_distribution"}:
            recent_distributions.append(payload)

    upcoming_calls.sort(key=lambda item: (item["due_date"] is None, item["due_date"]))
    recent_distributions.sort(
        key=lambda item: (item["effective_date"] is None, item["effective_date"]),
        reverse=True,
    )
    return {
        "upcoming_calls": upcoming_calls[:20],
        "recent_distributions": recent_distributions[:20],
    }


def summarize_holdings(workspace_id: str, db: Session) -> dict:
    holdings = db.scalars(
        select(Holding).where(Holding.workspace_id == workspace_id, Holding.deleted_at.is_(None))
    ).all()
    total_value = sum((h.current_value_base or h.current_value or Decimal("0")) for h in holdings)

    def group_by(field_name: str) -> list[dict]:
        grouped: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        counts: dict[str, int] = defaultdict(int)
        for holding in holdings:
            label = getattr(holding, field_name) or "Unknown"
            grouped[label] += holding.current_value_base or holding.current_value or Decimal("0")
            counts[label] += 1
        items = []
        for label, value in grouped.items():
            items.append(
                {
                    "label": label,
                    "value_base": value,
                    "pct_of_total": float(value / total_value) if total_value else 0.0,
                    "item_count": counts[label],
                }
            )
        items.sort(key=lambda item: item["value_base"], reverse=True)
        return items

    return {
        "asset_class": group_by("asset_type"),
        "geo": group_by("geo_region"),
        "sector": group_by("sector"),
    }
