from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.services.overlay.regime_detector import detect_risk_regime
from backend.services.overlay.sentiment_agent import (
    MAX_SENTIMENT_MODIFIER_PCT,
    apply_sentiment_modifier,
    score_factor_sentiment,
)
from backend.tests.test_phase_cd import bootstrap_portfolio


def test_overlay_endpoints_and_cockpit_summary(client: TestClient, db_session: Session) -> None:
    auth = bootstrap_portfolio(client, db_session, email="overlay@example.com")

    factors = client.get("/api/overlay/factors")
    assert factors.status_code == 200
    factor_rows = factors.json()
    assert len(factor_rows) >= 4
    assert any(row["factor_key"] == "asset_class:private_equity" for row in factor_rows)

    regime = client.get("/api/overlay/regime")
    assert regime.status_code == 200
    regime_body = regime.json()
    assert regime_body["regime"] in {"normal", "stress", "crisis"}
    assert regime_body["trigger_signal"]

    triangulation = client.get("/api/overlay/aum-triangulation")
    assert triangulation.status_code == 200
    triangulation_body = triangulation.json()
    assert triangulation_body["composite_score"] >= 0.0
    assert len(triangulation_body["factors"]) >= 4
    assert triangulation_body["top_risk_contributors"][0]["aum_exposed_usd"] > 0.0

    cockpit = client.get("/api/cockpit")
    assert cockpit.status_code == 200
    overlay_summary = cockpit.json()["overlay_summary"]
    assert overlay_summary["regime"] == regime_body["regime"]
    assert len(overlay_summary["top_risk_factors"]) > 0

    stress = client.get("/api/overlay/stress")
    assert stress.status_code == 200
    stress_body = stress.json()
    assert stress_body["regime"] == regime_body["regime"]
    assert len(stress_body["scenarios"]) == 6
    assert "estimated_impact_usd" in stress_body["scenarios"][0]

    run = client.post("/api/overlay/run", headers={"X-CSRF-Token": auth["csrf"]})
    assert run.status_code == 200
    run_body = run.json()
    assert run_body["status"] == "succeeded"
    assert run_body["factor_count"] >= 4
    assert run_body["stress_count"] == 6


def test_private_var_uses_proxy_basket_labelling(client: TestClient, db_session: Session) -> None:
    auth = bootstrap_portfolio(client, db_session, email="proxyvar@example.com")

    response = client.post("/api/var/compute", headers={"X-CSRF-Token": auth["csrf"]})
    assert response.status_code == 200
    contributions = response.json()["position_contributions"]
    pef = next(item for item in contributions if item["ticker"] == "PEF")
    assert pef["method"] == "Estimated — proxy basket method"


def test_regime_detector_thresholds() -> None:
    assert detect_risk_regime({"vix": 14.0, "ig_spread_bps": 110.0}).regime == "normal"
    assert detect_risk_regime({"vix": 22.0, "ig_spread_bps": 140.0}).regime == "stress"
    assert detect_risk_regime({"vix": 31.0, "ig_spread_bps": 180.0}).regime == "crisis"


def test_sentiment_modifier_is_bounded_and_sector_specific() -> None:
    signal = score_factor_sentiment(
        "sector:technology",
        macro_payload={"vix": 16.0, "dxy": 101.0},
        latest_returns={"CL=F": 0.01},
    )
    assert 0.0 < signal.modifier_pct <= MAX_SENTIMENT_MODIFIER_PCT

    stressed_financials = score_factor_sentiment(
        "sector:financials",
        macro_payload={"vix": 22.0, "dxy": 103.5},
        latest_returns={"CL=F": -0.02},
    )
    assert -MAX_SENTIMENT_MODIFIER_PCT <= stressed_financials.modifier_pct < 0.0
    assert apply_sentiment_modifier(70.0, 50.0) == 77.0
    assert apply_sentiment_modifier(70.0, -50.0) == 63.0


def test_overlay_factor_scores_persist_sentiment_metadata(client: TestClient, db_session: Session) -> None:
    bootstrap_portfolio(client, db_session, email="overlay-sentiment@example.com")

    factors = client.get("/api/overlay/factors")
    assert factors.status_code == 200
    body = factors.json()
    technology = next(row for row in body if row["factor_key"] == "sector:technology")
    private_equity = next(row for row in body if row["factor_key"] == "asset_class:private_equity")

    assert 0.0 < technology["sentiment_modifier"] <= MAX_SENTIMENT_MODIFIER_PCT
    assert -MAX_SENTIMENT_MODIFIER_PCT <= private_equity["sentiment_modifier"] <= 0.0

    signal_payload = json.loads(technology["signal_payload_json"])
    assert signal_payload["sentiment_modifier_pct"] == technology["sentiment_modifier"]
    assert signal_payload["base_score"] >= 0.0
    assert "sentiment_driver" in signal_payload
