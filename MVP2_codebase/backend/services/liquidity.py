from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.capital import CapitalEvent
from ..models.deals import Deal
from ..models.funds import Commitment


def _month_key(value: Optional[date]) -> str:
    current = value or date.today()
    return f"{current.year:04d}-{current.month:02d}"


def generate_cash_flow_ladder(
    workspace_id: str,
    db: Session,
    *,
    scenario: str = "base",
    base_currency: str = "USD",
    projection_months: int = 24,
    liquidity_buffer: Decimal = Decimal("0"),
) -> dict:
    buckets: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {"inflows": Decimal("0"), "outflows": Decimal("0")}
    )

    events = db.scalars(
        select(CapitalEvent).where(CapitalEvent.workspace_id == workspace_id, CapitalEvent.deleted_at.is_(None))
    ).all()
    for event in events:
        amount = event.amount_base or event.amount or Decimal("0")
        bucket = buckets[_month_key(event.effective_date or event.due_date)]
        if event.type == "call" or event.type == "fee":
            bucket["outflows"] += amount
        elif event.type == "recallable_distribution":
            if event.recall_expires_at and event.recall_expires_at.date() <= date.today():
                bucket["inflows"] += amount
        else:
            bucket["inflows"] += amount

    commitments = db.scalars(
        select(Commitment).where(Commitment.workspace_id == workspace_id, Commitment.deleted_at.is_(None))
    ).all()
    for commitment in commitments:
        remaining = commitment.uncalled_capital_base or commitment.uncalled_capital or Decimal("0")
        months = commitment.remaining_fund_life_months or projection_months
        if remaining > 0 and months > 0:
            monthly_draw = remaining / Decimal(months)
            for offset in range(min(months, projection_months)):
                month = ((date.today().year * 12 + date.today().month - 1 + offset))
                year = month // 12
                month_num = month % 12 + 1
                buckets[f"{year:04d}-{month_num:02d}"]["outflows"] += monthly_draw

    deals = db.scalars(
        select(Deal).where(Deal.workspace_id == workspace_id, Deal.deleted_at.is_(None), Deal.stage == "ic_review")
    ).all()
    for deal in deals:
        amount = deal.target_commitment_base or deal.target_commitment or Decimal("0")
        buckets[_month_key(deal.target_close_date)]["outflows"] += amount

    monthly_buckets = []
    liquidity_gaps = []
    cumulative = Decimal("0")
    for key in sorted(buckets.keys())[:projection_months]:
        inflows = buckets[key]["inflows"]
        outflows = buckets[key]["outflows"]
        if scenario == "stress" and inflows > 0:
            inflows = inflows * Decimal("0.75")
        net = inflows - outflows
        cumulative += net
        row = {
            "month": key,
            "inflows": inflows,
            "outflows": outflows,
            "net": net,
            "cumulative": cumulative,
        }
        monthly_buckets.append(row)
        if cumulative < liquidity_buffer:
            liquidity_gaps.append(
                {
                    "month": key,
                    "gap_amount": liquidity_buffer - cumulative,
                    "description": f"Liquidity below buffer in {key}",
                }
            )

    return {
        "scenario": scenario,
        "base_currency": base_currency,
        "projection_months": projection_months,
        "monthly_buckets": monthly_buckets,
        "liquidity_gaps": liquidity_gaps,
    }
