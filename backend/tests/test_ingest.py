from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.jobs import AsyncJob
from backend.models.portfolio import PortfolioSnapshot
from backend.tests.test_auth import seed_user


def login_headers(client, db_session: Session, email: str = "ingest@example.com") -> dict[str, str]:
    user = seed_user(db_session, email=email)
    login = client.post("/api/auth/login", json={"email": user.email, "password": "secret123"})
    assert login.status_code == 200
    return {"X-CSRF-Token": login.cookies.get("__crb_csrf", "")}


def test_csv_ingest_creates_snapshot_and_job(client, db_session: Session) -> None:
    headers = login_headers(client, db_session)
    payload = (
        "ticker,quantity,asset_class,custodian,geo_region,sector,market_segment,market_value_usd,notes\n"
        "AAPL,10,public_equity,Goldman,US,Technology,Large Cap,1900,Core holding\n"
        "BND,20,fixed_income,Fidelity,US,Fixed Income,IG Credit,1500,Income sleeve\n"
    )

    response = client.post(
        "/api/ingest/csv",
        files={"file": ("positions.csv", payload, "text/csv")},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["position_count"] == 2
    assert body["ready_for_enrichment"] is True

    snapshot = db_session.get(PortfolioSnapshot, body["snapshot_id"])
    assert snapshot is not None
    assert snapshot.is_current is True
    assert snapshot.total_aum_usd == 3400.0

    job = db_session.get(AsyncJob, body["job_id"])
    assert job is not None
    assert job.status == "succeeded"
    assert job.resource_id == snapshot.id


def test_second_ingest_replaces_current_snapshot(client, db_session: Session) -> None:
    headers = login_headers(client, db_session, email="history@example.com")
    first_payload = "ticker,quantity,market_value_usd\nAAPL,10,1900\n"
    second_payload = "ticker,quantity,market_value_usd\nMSFT,5,2100\n"

    first = client.post(
        "/api/ingest/csv",
        files={"file": ("first.csv", first_payload, "text/csv")},
        headers=headers,
    )
    second = client.post(
        "/api/ingest/csv",
        files={"file": ("second.csv", second_payload, "text/csv")},
        headers=headers,
    )

    first_snapshot = db_session.get(PortfolioSnapshot, first.json()["snapshot_id"])
    second_snapshot = db_session.get(PortfolioSnapshot, second.json()["snapshot_id"])
    assert first_snapshot is not None
    assert second_snapshot is not None
    db_session.refresh(first_snapshot)
    db_session.refresh(second_snapshot)

    assert first_snapshot.is_current is False
    assert second_snapshot.is_current is True
    assert second_snapshot.parent_snapshot_id == first_snapshot.id


def test_portfolio_summary_and_positions_flow(client, db_session: Session) -> None:
    headers = login_headers(client, db_session, email="summary@example.com")
    payload = (
        "ticker,quantity,asset_class,custodian,geo_region,sector,market_segment,market_value_usd\n"
        "AAPL,10,public_equity,Goldman,US,Technology,Large Cap,1900\n"
        "BND,20,fixed_income,Fidelity,US,Fixed Income,IG Credit,1500\n"
        "CASH,100,cash,Goldman,Global,Treasury,Cash,100\n"
    )
    upload = client.post(
        "/api/ingest/csv",
        files={"file": ("summary.csv", payload, "text/csv")},
        headers=headers,
    )
    assert upload.status_code == 200
    snapshot_id = upload.json()["snapshot_id"]

    snapshot_response = client.get("/api/portfolio/snapshot")
    assert snapshot_response.status_code == 200
    assert snapshot_response.json()["snapshot_id"] == snapshot_id
    assert snapshot_response.json()["position_count"] == 3

    summary = client.get("/api/portfolio/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["total_aum_usd"] == 3500.0
    assert body["liquidity_score_pct"] == 100.0
    assert body["asset_class"][0]["label"] == "public_equity"
    assert body["custodian_distribution"][0]["label"] == "Goldman"

    positions = client.get("/api/portfolio/positions")
    assert positions.status_code == 200
    position_body = positions.json()
    assert position_body["total"] == 3
    assert [item["ticker"] for item in position_body["items"]] == ["AAPL", "BND", "CASH"]


def test_csv_ingest_preserves_real_assets_class(client, db_session: Session) -> None:
    headers = login_headers(client, db_session, email="real-assets@example.com")
    payload = (
        "ticker,quantity,asset_class,custodian,geo_region,sector,market_segment,market_value_usd\n"
        "GLD,10,real_assets,Fidelity,Global,Precious Metals,ETF,2500\n"
        "VNQ,5,real_assets,Goldman,US,Real Estate,REIT,500\n"
    )

    upload = client.post(
        "/api/ingest/csv",
        files={"file": ("real-assets.csv", payload, "text/csv")},
        headers=headers,
    )
    assert upload.status_code == 200

    summary = client.get("/api/portfolio/summary")
    assert summary.status_code == 200
    asset_classes = {item["label"]: item for item in summary.json()["asset_class"]}
    assert "real_assets" in asset_classes
    assert asset_classes["real_assets"]["position_count"] == 2


def test_csv_ingest_rejects_invalid_extension(client, db_session: Session) -> None:
    headers = login_headers(client, db_session, email="badfile@example.com")

    response = client.post(
        "/api/ingest/csv",
        files={"file": ("positions.xlsx", "ticker,quantity\nAAPL,10\n", "text/csv")},
        headers=headers,
    )

    assert response.status_code == 400
    assert "Only .csv and .tsv files are accepted" in response.json()["detail"]
