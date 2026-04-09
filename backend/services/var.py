from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.analytics import PriceCache, VarResult
from backend.models.portfolio import PortfolioSnapshot, Position
from backend.services.analytics.factor_var import compute_overlay_var_for_snapshot
from backend.services.auth.session import ensure_utc, utc_now
from backend.services.enrichment import ensure_enrichment_for_positions

LOOKBACK_DAYS: int = 252  # standard trading-year lookback for historical simulation VaR


def compute_var_for_snapshot(db: Session, snapshot: PortfolioSnapshot) -> VarResult:
    positions = db.scalars(select(Position).where(Position.snapshot_id == snapshot.id)).all()
    enrichment_info = ensure_enrichment_for_positions(db, snapshot.workspace_id, positions)
    total_aum = float(snapshot.total_aum_usd or 0.0)
    overlay_var = compute_overlay_var_for_snapshot(db, snapshot)
    drawdown = (overlay_var["worst_loss"] / total_aum) if total_aum else 0.0

    existing = db.scalar(
        select(VarResult)
        .where(VarResult.snapshot_id == snapshot.id)
        .order_by(VarResult.computed_at.desc())
    )
    result = existing or VarResult(snapshot_id=snapshot.id, workspace_id=snapshot.workspace_id)
    result.var_1d_95 = overlay_var["var_1d_95"]
    result.var_1d_99 = overlay_var["var_1d_99"]
    result.cvar_1d_95 = overlay_var["cvar_1d_95"]
    result.cvar_1d_99 = overlay_var["cvar_1d_99"]
    result.max_drawdown_1y = round(drawdown * 100.0, 2)
    result.worst_scenario_date = (utc_now() - timedelta(days=int(overlay_var["worst_index"]))).date()
    result.worst_scenario_loss = overlay_var["worst_loss"]
    result.lookback_days = LOOKBACK_DAYS
    result.effective_lookback_days = overlay_var["effective_lookback_days"]
    result.methodology = "historical_simulation"
    result.model_coverage_pct = overlay_var["model_coverage_pct"] if total_aum else 0.0
    result.unmodeled_value_usd = max(0.0, overlay_var["unmodeled_value_usd"], total_aum - float(enrichment_info["modeled_value_usd"]))
    result.position_contributions_json = json.dumps(overlay_var["position_contributions"], sort_keys=True)
    assumptions = overlay_var["assumptions"]
    assumptions["tickers_modeled"] = sorted(set(assumptions["tickers_modeled"]) | set(enrichment_info["tickers"]))
    result.assumptions_json = json.dumps(assumptions, sort_keys=True)
    result.computed_at = utc_now()
    db.add(result)
    db.flush()
    return result
