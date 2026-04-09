from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from MVP2_codebase.backend.database import Base, SessionLocal, engine
from MVP2_codebase.backend.main import app
from MVP2_codebase.backend.models.auth import WorkspaceSetting
from MVP2_codebase.backend.models.identity import User, Workspace
from MVP2_codebase.backend.services.auth.password import hash_password


def ensure_demo_records() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        workspace = db.get(Workspace, "demo-workspace")
        if workspace is None:
            db.add(
                Workspace(
                    id="demo-workspace",
                    name="Demo Workspace",
                    reporting_currency="USD",
                    timezone="UTC",
                )
            )
        user = db.get(User, "demo-user")
        if user is None:
            db.add(
                User(
                    id="demo-user",
                    workspace_id="demo-workspace",
                    email="auth@example.com",
                    display_name="Demo User",
                    role="admin",
                    password_hash=hash_password("secret123"),
                )
            )
        settings = db.get(WorkspaceSetting, "demo-workspace")
        if settings is None:
            db.add(
                WorkspaceSetting(
                    workspace_id="demo-workspace",
                    briefing_day="Monday",
                    briefing_time="06:00",
                    briefing_recipients="",
                    briefing_auto_publish=False,
                    briefing_send_pdf=False,
                    briefing_include_audit_footer=False,
                    ai_model="deterministic-mvp2-briefing",
                    ai_risk_tone="conservative",
                    ai_allow_trade_actions=False,
                    base_currency="USD",
                    reporting_timezone="UTC",
                    liquidity_buffer_default=0,
                    updated_at=datetime.now(timezone.utc),
                )
            )
        db.commit()


def login_client() -> TestClient:
    ensure_demo_records()
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"email": "auth@example.com", "password": "secret123"})
    assert response.status_code == 200
    return client


def test_fund_crud_shape() -> None:
    client = login_client()

    create = client.post(
        "/api/portfolio/funds",
        json={
            "name": "North Lake PE I",
            "type": "PE",
            "manager_name": "North Lake",
            "currency": "USD",
        },
    )
    assert create.status_code == 201
    fund_id = create.json()["id"]

    listing = client.get("/api/portfolio/funds")
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    detail = client.get(f"/api/portfolio/funds/{fund_id}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "North Lake PE I"


def test_document_parse_flow() -> None:
    client = login_client()

    upload = client.post(
        "/api/documents/upload",
        files={"file": ("capital_call.txt", b"Capital call notice amount USD 100000 due 2026-05-01", "text/plain")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]

    parsed = client.post(f"/api/documents/{document_id}/parse")
    assert parsed.status_code == 200

    extraction = client.get(f"/api/documents/{document_id}/extraction")
    assert extraction.status_code == 200
    assert extraction.json()["document_type"] == "capital_call"

    reconciliation = client.get(f"/api/documents/{document_id}/reconcile")
    assert reconciliation.status_code == 200
    flag_ids = [item["id"] for item in reconciliation.json()["items"]]

    resolved = client.post(
        f"/api/documents/{document_id}/reconcile",
        json={"flag_ids": flag_ids, "action": "resolved"},
    )
    assert resolved.status_code == 200

    reopened = client.post(
        f"/api/documents/{document_id}/reconcile",
        json={"flag_ids": flag_ids, "action": "reopen"},
    )
    assert reopened.status_code == 200


def test_briefing_generation_flow() -> None:
    client = login_client()

    fund = client.post(
        "/api/portfolio/funds",
        json={"name": "North Lake PE I", "type": "PE", "manager_name": "North Lake", "currency": "USD"},
    )
    fund_id = fund.json()["id"]
    client.post(
        "/api/portfolio/commitments",
        json={
            "fund_id": fund_id,
            "committed_amount": "5000000",
            "commitment_currency": "USD",
            "committed_amount_base": "5000000",
            "called_capital": "2000000",
            "called_capital_base": "2000000",
            "uncalled_capital": "3000000",
            "uncalled_capital_base": "3000000",
            "distributions_received": "250000",
            "distributions_received_base": "250000",
        },
    )
    client.post(
        "/api/portfolio/capital-events",
        json={
            "fund_id": fund_id,
            "type": "call",
            "amount": "1000000",
            "currency": "USD",
            "amount_base": "1000000",
            "due_date": "2026-05-01",
            "is_confirmed": True,
        },
    )

    generated = client.post("/api/briefings/generate")
    assert generated.status_code == 200
    briefing_id = generated.json()["id"]

    listing = client.get("/api/briefings")
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    detail = client.get(f"/api/briefings/{briefing_id}")
    assert detail.status_code == 200
    assert "executive_summary" in detail.json()["output"]

    published = client.post(f"/api/briefings/{briefing_id}/publish")
    assert published.status_code == 200

    exported = client.get(f"/api/briefings/{briefing_id}/export/pdf")
    assert exported.status_code == 200


def test_root_redirect_and_app_mount() -> None:
    client = TestClient(app)
    root = client.get("/", follow_redirects=False)
    assert root.status_code in {302, 307}
    assert root.headers["location"] == "/app/login.html"
    mounted = client.get("/app/login.html")
    assert mounted.status_code == 200


def test_protected_routes_require_authentication() -> None:
    ensure_demo_records()
    client = TestClient(app)
    funds = client.get("/api/portfolio/funds")
    assert funds.status_code == 401

    settings = client.get("/api/settings")
    assert settings.status_code == 401


def test_login_and_session_flow() -> None:
    client = login_client()
    session = client.get("/api/auth/session")
    assert session.status_code == 200
    assert session.json()["user"]["email"] == "auth@example.com"

    funds = client.get("/api/portfolio/funds")
    assert funds.status_code == 200


def test_health_and_settings_flow() -> None:
    ensure_demo_records()
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    client = login_client()
    settings = client.get("/api/settings")
    assert settings.status_code == 200
    assert settings.json()["base_currency"] == "USD"

    patched = client.patch(
        "/api/settings",
        json={
            "base_currency": "EUR",
            "reporting_timezone": "Europe/Zurich",
            "liquidity_buffer_default": 250000,
        },
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["base_currency"] == "EUR"
    assert body["reporting_timezone"] == "Europe/Zurich"
    assert body["liquidity_buffer_default"] == 250000

    api_key = client.post("/api/settings/api-keys", json={"label": "Demo integration", "key_type": "service"})
    assert api_key.status_code == 200
    raw_key = api_key.json()["plain_text_key"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {raw_key}"})
    assert me.status_code == 200
