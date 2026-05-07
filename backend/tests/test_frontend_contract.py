from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.tests.test_phase_cd import bootstrap_portfolio, build_statement_xlsx, csrf_headers


def test_frontend_contract_aliases(client: TestClient, db_session: Session) -> None:
    auth = bootstrap_portfolio(client, db_session, email="frontend-contract@example.com")
    headers = csrf_headers(auth)

    var_response = client.get("/api/var")
    assert var_response.status_code == 200
    assert var_response.json()["var_1d_95"] >= 0.0

    liquidity = client.get("/api/liquidity?months=6")
    assert liquidity.status_code == 200
    liquidity_body = liquidity.json()
    assert {"buckets", "cash_flows", "upcoming_events", "cash_runway_months"} <= set(liquidity_body)
    assert len(liquidity_body["cash_flows"]) == 6

    onboarding = client.get("/api/onboarding/status")
    assert onboarding.status_code == 200
    assert onboarding.json()["state"] == "complete"

    created_briefing = client.post("/api/briefings", json={"scope": "risk"}, headers=headers)
    assert created_briefing.status_code == 200
    assert created_briefing.json()["scope"] == "risk"

    settings = client.put("/api/settings", json={"briefing_day": "Thursday"}, headers=headers)
    assert settings.status_code == 200
    assert settings.json()["briefing_day"] == "Thursday"

    members = client.get("/api/settings/members")
    assert members.status_code == 200
    assert members.json()["items"][0]["email"] == "frontend-contract@example.com"

    security = client.get("/api/settings/security")
    assert security.status_code == 200
    assert "sessions" in security.json()

    billing = client.get("/api/settings/billing-portal")
    assert billing.status_code == 200
    assert billing.json()["url"].startswith("https://")

    document = client.post(
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
    assert document.status_code == 200
    document_id = document.json()["id"]
    assert client.post(f"/api/documents/{document_id}/parse", headers=headers).status_code == 200

    fields = client.get(f"/api/documents/{document_id}/fields")
    assert fields.status_code == 200
    assert "field_reviews" in fields.json()

    apply = client.post(f"/api/documents/{document_id}/apply", headers=headers)
    assert apply.status_code == 200
    assert "snapshot" in apply.json()["detail"]
