from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.auth import ApiKey, User
from backend.models.portfolio import Position, PortfolioSnapshot
from backend.services.auth.password import hash_password
from backend.services.auth.session import sha256_hex
from backend.tests.test_auth import seed_user
from backend.tests.test_phase_cd import bootstrap_portfolio, build_statement_xlsx, csrf_headers


def _api_headers(user: User, raw_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {raw_key}"}


def _issue_api_key(db_session: Session, user: User, raw_key: str) -> dict[str, str]:
    db_session.add(
        ApiKey(
            workspace_id=user.workspace_id,
            user_id=user.id,
            label="Regression",
            key_type="anthropic",
            key_prefix=raw_key[:10],
            lookup_hash=sha256_hex(raw_key),
            key_hash=hash_password(raw_key),
        )
    )
    db_session.commit()
    return _api_headers(user, raw_key)


def _upload_document(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/documents/upload",
        data={"folder": "custodian_statements"},
        files={
            "file": (
                "statement.xlsx",
                build_statement_xlsx(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_mutating_cookie_routes_reject_missing_csrf(client: TestClient, db_session: Session) -> None:
    auth = bootstrap_portfolio(client, db_session, email="csrf-regression@example.com")

    create_position = client.post(
        "/api/portfolio/positions",
        json={
            "ticker": "TSLA",
            "position_currency": "USD",
            "quantity": 5,
            "market_value_usd": 1000,
            "asset_class": "public_equity",
        },
    )
    assert create_position.status_code == 403

    run_risk = client.post("/api/risk/run")
    assert run_risk.status_code == 403

    patch_settings = client.patch("/api/settings", json={"briefing_day": "Friday"})
    assert patch_settings.status_code == 403

    upload_document = client.post(
        "/api/documents/upload",
        data={"folder": "custodian_statements"},
        files={
            "file": (
                "statement.xlsx",
                build_statement_xlsx(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert upload_document.status_code == 403

    ok = client.post("/api/risk/run", headers=csrf_headers(auth))
    assert ok.status_code == 200


def test_protected_routes_require_authentication(client: TestClient, db_session: Session) -> None:
    seed_user(db_session, email="anonymous-guard@example.com")

    assert client.get("/api/auth/session").status_code == 401
    assert client.get("/api/cockpit").status_code == 401
    assert client.get("/api/briefings").status_code == 401
    assert client.get("/api/documents").status_code == 401
    assert client.get("/api/liquidity/summary").status_code == 401
    assert client.post("/api/risk/run").status_code == 401


def test_workspace_isolation_blocks_cross_workspace_reads(client: TestClient, db_session: Session) -> None:
    auth_a = bootstrap_portfolio(client, db_session, email="workspace-a@example.com")
    user_a = db_session.scalar(select(User).where(User.email == "workspace-a@example.com"))
    assert user_a is not None

    assert client.post("/api/var/compute", headers=csrf_headers(auth_a)).status_code == 200
    assert client.post("/api/risk/run", headers=csrf_headers(auth_a)).status_code == 200
    briefing_a = client.post("/api/briefings/generate", headers=csrf_headers(auth_a))
    assert briefing_a.status_code == 200
    briefing_a_id = briefing_a.json()["id"]
    document_a_id = _upload_document(client, csrf_headers(auth_a))

    auth_b = bootstrap_portfolio(client, db_session, email="workspace-b@example.com")
    user_b = db_session.scalar(select(User).where(User.email == "workspace-b@example.com"))
    assert user_b is not None

    snapshot_b = db_session.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.workspace_id == user_b.workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
    )
    assert snapshot_b is not None
    b_position = db_session.scalar(
        select(Position).where(
            Position.snapshot_id == snapshot_b.id,
            Position.ticker == "AAPL",
        )
    )
    assert b_position is not None
    b_position.market_value_usd = 9999.0
    snapshot_b.total_aum_usd = sum(
        float(position.market_value_usd or 0)
        for position in db_session.scalars(select(Position).where(Position.snapshot_id == snapshot_b.id)).all()
    )
    db_session.commit()

    headers_a = _issue_api_key(db_session, user_a, "crb_workspace_a_regression")
    headers_b = _issue_api_key(db_session, user_b, "crb_workspace_b_regression")
    client.cookies.clear()

    briefing_cross = client.get(f"/api/briefings/{briefing_a_id}", headers=headers_b)
    assert briefing_cross.status_code == 404

    document_cross = client.get(f"/api/documents/{document_a_id}", headers=headers_b)
    assert document_cross.status_code == 404

    briefing_list_b = client.get("/api/briefings", headers=headers_b)
    assert briefing_list_b.status_code == 200
    assert all(item["id"] != briefing_a_id for item in briefing_list_b.json()["items"])

    docs_list_b = client.get("/api/documents", headers=headers_b)
    assert docs_list_b.status_code == 200
    assert all(item["id"] != document_a_id for item in docs_list_b.json()["items"])

    cockpit_a = client.get("/api/cockpit", headers=headers_a)
    cockpit_b = client.get("/api/cockpit", headers=headers_b)
    assert cockpit_a.status_code == 200
    assert cockpit_b.status_code == 200
    assert cockpit_a.json()["portfolio_summary"]["total_aum_usd"] != cockpit_b.json()["portfolio_summary"]["total_aum_usd"]

    overlay_a = client.get("/api/overlay/aum-triangulation", headers=headers_a)
    overlay_b = client.get("/api/overlay/aum-triangulation", headers=headers_b)
    assert overlay_a.status_code == 200
    assert overlay_b.status_code == 200
    assert overlay_a.json()["factors"][0]["aum_exposed_usd"] != overlay_b.json()["factors"][0]["aum_exposed_usd"]
