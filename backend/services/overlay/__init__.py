from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.overlay import RiskRegime
from backend.models.portfolio import PortfolioSnapshot, Position
from backend.services.auth.session import utc_now
from backend.services.enrichment import ensure_enrichment_for_positions
from backend.services.overlay.factor_scorer import compute_factor_scores, sync_asset_factor_exposures
from backend.services.overlay.propagator import build_aum_triangulation
from backend.services.overlay.regime_detector import detect_risk_regime
from backend.services.overlay.signal_collector import collect_overlay_signals


def ensure_overlay_state(db: Session, snapshot: PortfolioSnapshot) -> dict[str, object]:
    positions = db.scalars(select(Position).where(Position.snapshot_id == snapshot.id)).all()
    ensure_enrichment_for_positions(db, snapshot.workspace_id, positions)
    signals = collect_overlay_signals(db, snapshot.workspace_id)
    as_of_date = signals["as_of_date"]
    exposures = sync_asset_factor_exposures(db, snapshot, positions, as_of_date=as_of_date)
    factor_scores = compute_factor_scores(db, snapshot, positions, signals=signals, as_of_date=as_of_date)
    detected_regime = detect_risk_regime(signals["macro"])

    db.query(RiskRegime).filter(
        RiskRegime.workspace_id == snapshot.workspace_id,
        RiskRegime.as_of_date == as_of_date,
    ).delete()
    regime = RiskRegime(
        workspace_id=snapshot.workspace_id,
        snapshot_id=snapshot.id,
        regime=detected_regime.regime,
        trigger_signal=detected_regime.trigger_signal,
        vix_level=detected_regime.vix_level,
        credit_spread_bps=detected_regime.credit_spread_bps,
        methodology_note=detected_regime.methodology_note,
        as_of_date=as_of_date,
    )
    db.add(regime)
    db.flush()

    triangulation = build_aum_triangulation(positions, exposures, factor_scores)
    return {
        "as_of_date": as_of_date,
        "positions": positions,
        "exposures": exposures,
        "factor_scores": factor_scores,
        "regime": regime,
        "triangulation": triangulation,
        "signals": signals,
    }


__all__ = ["ensure_overlay_state"]
