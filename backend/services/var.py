from __future__ import annotations

import json
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.analytics import PriceCache, VarResult
from backend.models.portfolio import PortfolioSnapshot, Position
from backend.services.auth.session import ensure_utc, utc_now
from backend.services.enrichment import ensure_enrichment_for_positions


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    index = max(0, min(len(sorted_values) - 1, int((len(sorted_values) - 1) * p)))
    return sorted_values[index]


def compute_var_for_snapshot(db: Session, snapshot: PortfolioSnapshot) -> VarResult:
    positions = db.scalars(select(Position).where(Position.snapshot_id == snapshot.id)).all()
    enrichment_info = ensure_enrichment_for_positions(db, snapshot.workspace_id, positions)

    scenario_losses: list[tuple[int, float]] = []
    contributions: dict[str, float] = {}
    total_aum = float(snapshot.total_aum_usd or 0.0)

    histories: dict[str, list[float]] = {}
    for position in positions:
        cache = db.get(PriceCache, position.ticker)
        if cache is None:
            continue
        history_json = json.loads(cache.history_json)
        histories[position.id] = [float(point["close_usd"]) for point in history_json][-252:]

    effective_lookback_days = min((len(series) for series in histories.values()), default=0)
    for scenario_index in range(1, effective_lookback_days):
        scenario_loss = 0.0
        for position in positions:
            history = histories.get(position.id)
            if not history or scenario_index >= len(history):
                continue
            previous = history[scenario_index - 1]
            current = history[scenario_index]
            if not previous:
                continue
            scenario_return = (current / previous) - 1.0
            loss = float(position.market_value_usd or 0.0) * scenario_return
            scenario_loss += loss
            contributions[position.id] = contributions.get(position.id, 0.0) + loss
        scenario_losses.append((scenario_index, scenario_loss))

    ordered_losses = sorted(loss for _, loss in scenario_losses)
    var_95 = abs(_percentile(ordered_losses, 0.05))
    var_99 = abs(_percentile(ordered_losses, 0.01))
    cvar_95 = abs(mean(ordered_losses[: max(1, int(len(ordered_losses) * 0.05))])) if ordered_losses else 0.0
    cvar_99 = abs(mean(ordered_losses[: max(1, int(len(ordered_losses) * 0.01))])) if ordered_losses else 0.0
    worst_index, worst_loss = min(scenario_losses, key=lambda item: item[1]) if scenario_losses else (0, 0.0)
    drawdown = abs(min(ordered_losses)) / total_aum if ordered_losses and total_aum else 0.0

    contribution_rows = []
    for position in positions:
        aggregate_loss = contributions.get(position.id, 0.0)
        contribution_rows.append(
            {
                "ticker": position.ticker,
                "security_id": position.security_id,
                "contribution_pct": round((abs(aggregate_loss) / abs(sum(contributions.values())) * 100.0), 2)
                if contributions and sum(contributions.values()) != 0
                else 0.0,
                "contribution_usd": round(abs(aggregate_loss), 2),
                "method": "historical_scenario_additive",
            }
        )

    existing = db.scalar(
        select(VarResult)
        .where(VarResult.snapshot_id == snapshot.id)
        .order_by(VarResult.computed_at.desc())
    )
    result = existing or VarResult(snapshot_id=snapshot.id, workspace_id=snapshot.workspace_id)
    result.var_1d_95 = round(var_95, 2)
    result.var_1d_99 = round(var_99, 2)
    result.cvar_1d_95 = round(cvar_95, 2)
    result.cvar_1d_99 = round(cvar_99, 2)
    result.max_drawdown_1y = round(drawdown * 100.0, 2)
    result.worst_scenario_date = ensure_utc(snapshot.created_at).date() if worst_index == 0 else (utc_now().date())
    result.worst_scenario_loss = round(abs(worst_loss), 2)
    result.lookback_days = 252
    result.effective_lookback_days = effective_lookback_days
    result.methodology = "historical_simulation"
    result.model_coverage_pct = 100.0 if total_aum else 0.0
    result.unmodeled_value_usd = max(0.0, total_aum - float(enrichment_info["modeled_value_usd"]))
    result.position_contributions_json = json.dumps(contribution_rows, sort_keys=True)
    result.assumptions_json = json.dumps(
        {
            "coverage_warning": None if total_aum else "empty portfolio",
            "fx_pairs_used": ["USDUSD"],
            "tickers_modeled": enrichment_info["tickers"],
        },
        sort_keys=True,
    )
    result.computed_at = utc_now()
    db.add(result)
    db.flush()
    return result
