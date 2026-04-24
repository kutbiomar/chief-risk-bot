from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.portfolio import PortfolioSnapshot, Position
from backend.models.private_markets import CapitalEvent, Commitment


DEFAULT_BUFFER_USD = Decimal("2000000")


def _month_key(value: Optional[date]) -> str:
    current = value or date.today()
    return f"{current.year:04d}-{current.month:02d}"


def _bucket_date(month_key: str) -> date:
    year, month = month_key.split("-")
    return date(int(year), int(month), 1)


def _amount(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _current_snapshot(db: Session, workspace_id: str) -> PortfolioSnapshot | None:
    return db.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.workspace_id == workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
    )


def _current_cash_usd(db: Session, workspace_id: str) -> Decimal:
    snapshot = _current_snapshot(db, workspace_id)
    if snapshot is None:
        return Decimal("0")
    positions = db.scalars(select(Position).where(Position.snapshot_id == snapshot.id)).all()
    cash_total = sum(
        _amount(position.market_value_usd)
        for position in positions
        if str(position.asset_class or "").lower() == "cash"
    )
    return cash_total


def generate_cash_flow_ladder(
    workspace_id: str,
    db: Session,
    *,
    scenario: str = "base",
    base_currency: str = "USD",
    projection_months: int = 24,
    liquidity_buffer: Decimal = DEFAULT_BUFFER_USD,
) -> dict[str, object]:
    today = date.today()
    buckets: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {"inflows": Decimal("0"), "outflows": Decimal("0")}
    )

    for offset in range(projection_months):
        month_index = today.year * 12 + today.month - 1 + offset
        year = month_index // 12
        month_num = month_index % 12 + 1
        buckets[f"{year:04d}-{month_num:02d}"]

    events = db.scalars(
        select(CapitalEvent).where(
            CapitalEvent.workspace_id == workspace_id,
            CapitalEvent.deleted_at.is_(None),
        )
    ).all()
    for event in events:
        amount = _amount(event.amount_base or event.amount)
        bucket = buckets[_month_key(event.effective_date or event.due_date)]
        if event.type in {"call", "fee"}:
            bucket["outflows"] += amount
        elif event.type == "recallable_distribution":
            if event.recall_expires_at and event.recall_expires_at.date() <= today:
                bucket["inflows"] += amount
        else:
            bucket["inflows"] += amount

    commitments = db.scalars(
        select(Commitment).where(
            Commitment.workspace_id == workspace_id,
            Commitment.deleted_at.is_(None),
        )
    ).all()
    for commitment in commitments:
        remaining = _amount(commitment.uncalled_capital_base or commitment.uncalled_capital)
        months = int(commitment.remaining_fund_life_months or projection_months)
        if remaining <= 0 or months <= 0:
            continue
        monthly_draw = remaining / Decimal(months)
        for offset in range(min(months, projection_months)):
            month_index = today.year * 12 + today.month - 1 + offset
            year = month_index // 12
            month_num = month_index % 12 + 1
            buckets[f"{year:04d}-{month_num:02d}"]["outflows"] += monthly_draw

    monthly_buckets: list[dict[str, object]] = []
    liquidity_gaps: list[dict[str, object]] = []
    cumulative = Decimal("0")

    for key in sorted(buckets.keys())[:projection_months]:
        inflows = buckets[key]["inflows"]
        outflows = buckets[key]["outflows"]
        if scenario == "stress" and inflows > 0:
            inflows *= Decimal("0.75")
        net = inflows - outflows
        cumulative += net
        monthly_buckets.append(
            {
                "month": key,
                "inflows": float(inflows),
                "outflows": float(outflows),
                "net": float(net),
                "cumulative": float(cumulative),
            }
        )
        if cumulative < liquidity_buffer:
            liquidity_gaps.append(
                {
                    "month": key,
                    "gap_amount": float(liquidity_buffer - cumulative),
                    "description": f"Liquidity below buffer in {key}",
                }
            )

    return {
        "scenario": scenario,
        "base_currency": base_currency,
        "projection_months": projection_months,
        "liquidity_buffer": float(liquidity_buffer),
        "monthly_buckets": monthly_buckets,
        "liquidity_gaps": liquidity_gaps,
    }


def get_liquidity_summary(
    workspace_id: str,
    db: Session,
    *,
    days: int = 90,
    liquidity_buffer: Decimal = DEFAULT_BUFFER_USD,
) -> dict[str, object]:
    today = date.today()
    end_date = today + timedelta(days=days)
    cash_usd = _current_cash_usd(db, workspace_id)

    events = db.scalars(
        select(CapitalEvent).where(
            CapitalEvent.workspace_id == workspace_id,
            CapitalEvent.deleted_at.is_(None),
        )
    ).all()
    commitments = db.scalars(
        select(Commitment).where(
            Commitment.workspace_id == workspace_id,
            Commitment.deleted_at.is_(None),
        )
    ).all()

    next_call = None
    expected_distributions = Decimal("0")
    scheduled_outflows = Decimal("0")
    recallable_pending = Decimal("0")

    for event in events:
        event_date = event.effective_date or event.due_date
        amount = _amount(event.amount_base or event.amount)
        if event.type == "call" and event_date and event_date >= today:
            if next_call is None or event_date < next_call["date"]:
                next_call = {"date": event_date, "amount": amount, "fund_id": event.fund_id}
        if not event_date or event_date > end_date:
            continue
        if event.type in {"call", "fee"}:
            scheduled_outflows += amount
        elif event.type == "recallable_distribution":
            if event.recall_expires_at and event.recall_expires_at.date() <= today:
                expected_distributions += amount
            else:
                recallable_pending += amount
        else:
            expected_distributions += amount

    ladder = generate_cash_flow_ladder(
        workspace_id,
        db,
        scenario="base",
        projection_months=max(3, (days + 29) // 30),
        liquidity_buffer=liquidity_buffer,
    )
    net_90d = sum(Decimal(str(row["net"])) for row in ladder["monthly_buckets"])

    total_unfunded = sum(
        _amount(commitment.uncalled_capital_base or commitment.uncalled_capital)
        for commitment in commitments
    )
    projected_cash = cash_usd + net_90d
    buffer_gap = max(Decimal("0"), liquidity_buffer - projected_cash)

    return {
        "window_days": days,
        "buffer_target_usd": float(liquidity_buffer),
        "cash_on_hand_usd": float(cash_usd),
        "next_call_due_date": next_call["date"].isoformat() if next_call else None,
        "next_call_amount_usd": float(next_call["amount"]) if next_call else 0.0,
        "total_unfunded_usd": float(total_unfunded),
        "expected_distributions_usd": float(expected_distributions),
        "scheduled_outflows_usd": float(scheduled_outflows),
        "recallable_pending_usd": float(recallable_pending),
        "net_liquidity_usd": float(net_90d),
        "projected_cash_usd": float(projected_cash),
        "buffer_gap_usd": float(buffer_gap),
        "buffer_breach": buffer_gap > 0,
    }
