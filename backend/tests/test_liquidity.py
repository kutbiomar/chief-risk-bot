from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.auth import User
from backend.models.content import BriefingRun
from backend.models.private_markets import CapitalEvent, Commitment, Fund
from backend.services.auth.session import utc_now
from backend.tests.test_phase_cd import bootstrap_portfolio, csrf_headers


def seed_liquidity_data(db_session: Session, workspace_id: str) -> None:
    now = utc_now()
    fund = Fund(
        workspace_id=workspace_id,
        name="Blue River Capital Partners",
        type="private_equity",
        manager_name="Blue River",
        vintage_year=2023,
        currency="USD",
    )
    db_session.add(fund)
    db_session.flush()

    commitment = Commitment(
        workspace_id=workspace_id,
        fund_id=fund.id,
        committed_amount=Decimal("3000000"),
        committed_amount_base=Decimal("3000000"),
        called_capital=Decimal("1800000"),
        called_capital_base=Decimal("1800000"),
        uncalled_capital=Decimal("1200000"),
        uncalled_capital_base=Decimal("1200000"),
        distributions_received=Decimal("200000"),
        distributions_received_base=Decimal("200000"),
        nav=Decimal("1800000"),
        nav_base=Decimal("1800000"),
        nav_date=now.date(),
        remaining_fund_life_months=24,
    )
    db_session.add(commitment)
    db_session.flush()

    db_session.add_all(
        [
            CapitalEvent(
                workspace_id=workspace_id,
                fund_id=fund.id,
                commitment_id=commitment.id,
                type="call",
                amount=Decimal("250000"),
                amount_base=Decimal("250000"),
                currency="USD",
                due_date=(now + timedelta(days=12)).date(),
                effective_date=(now + timedelta(days=12)).date(),
                is_confirmed=True,
            ),
            CapitalEvent(
                workspace_id=workspace_id,
                fund_id=fund.id,
                commitment_id=commitment.id,
                type="distribution",
                amount=Decimal("175000"),
                amount_base=Decimal("175000"),
                currency="USD",
                effective_date=(now + timedelta(days=40)).date(),
                is_confirmed=True,
            ),
            CapitalEvent(
                workspace_id=workspace_id,
                fund_id=fund.id,
                commitment_id=commitment.id,
                type="fee",
                amount=Decimal("30000"),
                amount_base=Decimal("30000"),
                currency="USD",
                due_date=(now + timedelta(days=20)).date(),
                effective_date=(now + timedelta(days=20)).date(),
                is_confirmed=True,
            ),
        ]
    )
    db_session.commit()


def test_liquidity_endpoints_and_cockpit_summary(client: TestClient, db_session: Session) -> None:
    bootstrap_portfolio(client, db_session, email="liquidity@example.com")
    user = db_session.scalar(select(User).where(User.email == "liquidity@example.com"))
    assert user is not None
    seed_liquidity_data(db_session, user.workspace_id)

    summary = client.get("/api/liquidity/summary")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["next_call_amount_usd"] == 250000.0
    assert summary_body["total_unfunded_usd"] == 1200000.0
    assert "buffer_breach" in summary_body

    cashflow = client.get("/api/liquidity/cashflow?months=6&scenario=stress")
    assert cashflow.status_code == 200
    cashflow_body = cashflow.json()
    assert cashflow_body["scenario"] == "stress"
    assert len(cashflow_body["monthly_buckets"]) == 6
    assert cashflow_body["liquidity_buffer"] == 2000000.0

    cockpit = client.get("/api/cockpit")
    assert cockpit.status_code == 200
    cockpit_summary = cockpit.json()["portfolio_summary"]["liquidity_summary"]
    assert cockpit_summary["next_call_amount_usd"] == 250000.0


def test_briefing_includes_liquidity_snapshot(client: TestClient, db_session: Session) -> None:
    auth = bootstrap_portfolio(client, db_session, email="liquidity-briefing@example.com")
    user = db_session.scalar(select(User).where(User.email == "liquidity-briefing@example.com"))
    assert user is not None
    seed_liquidity_data(db_session, user.workspace_id)

    assert client.post("/api/var/compute", headers=csrf_headers(auth)).status_code == 200
    assert client.post("/api/risk/run", headers=csrf_headers(auth)).status_code == 200

    briefing = client.post("/api/briefings/generate", headers=csrf_headers(auth))
    assert briefing.status_code == 200
    output = briefing.json()["output"]
    assert "liquidity_snapshot" in output
    assert "liquidity_commentary" in output

    briefing_id = briefing.json()["id"]
    row = db_session.get(BriefingRun, briefing_id)
    assert row is not None
    body = json.loads(row.output_json)
    assert body["liquidity_snapshot"]["next_call_amount_usd"] == 250000.0
