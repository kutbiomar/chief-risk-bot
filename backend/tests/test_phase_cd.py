from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.tests.test_auth import seed_user


def bootstrap_portfolio(client: TestClient, db_session: Session, email: str = "phasecd@example.com") -> dict[str, str]:
    user = seed_user(db_session, email=email)
    login = client.post("/api/auth/login", json={"email": user.email, "password": "secret123"})
    assert login.status_code == 200
    csrf = login.cookies.get("__crb_csrf", "")
    payload = (
        "ticker,quantity,asset_class,custodian,geo_region,sector,market_segment,market_value_usd\n"
        "AAPL,10,public_equity,Goldman,US,Technology,Large Cap,1900\n"
        "BND,20,fixed_income,Fidelity,US,Fixed Income,IG Credit,1500\n"
        "VGK,15,public_equity,Goldman,Europe,Financials,Large Cap,800\n"
        "PEF,5,private_equity,AltCustodian,Global,Alternatives,Private Equity,600\n"
    )
    upload = client.post(
        "/api/ingest/csv",
        files={"file": ("positions.csv", payload, "text/csv")},
        headers={"X-CSRF-Token": csrf},
    )
    assert upload.status_code == 200
    return {"csrf": csrf, "snapshot_id": upload.json()["snapshot_id"]}


def test_var_risk_and_cockpit_flow(client: TestClient, db_session: Session) -> None:
    bootstrap_portfolio(client, db_session)

    var_response = client.post("/api/var/compute")
    assert var_response.status_code == 200
    assert var_response.json()["methodology"] == "historical_simulation"
    assert var_response.json()["effective_lookback_days"] > 200

    risk_response = client.post("/api/risk/run")
    assert risk_response.status_code == 200
    assert len(risk_response.json()["scores"]) == 5

    cockpit = client.get("/api/cockpit")
    assert cockpit.status_code == 200
    body = cockpit.json()
    assert body["portfolio_summary"]["total_aum_usd"] == 4800.0
    assert body["var_result"]["var_1d_95"] >= 0.0
    assert len(body["risk_register"]) >= 5


def test_briefings_settings_api_keys_and_documents_flow(client: TestClient, db_session: Session) -> None:
    bootstrap_portfolio(client, db_session, email="phasecd2@example.com")
    assert client.post("/api/var/compute").status_code == 200
    assert client.post("/api/risk/run").status_code == 200

    settings_patch = client.patch("/api/settings", json={"briefing_day": "Friday", "briefing_send_pdf": True})
    assert settings_patch.status_code == 200
    assert settings_patch.json()["briefing_day"] == "Friday"
    assert settings_patch.json()["briefing_send_pdf"] is True

    key_create = client.post("/api/settings/api-keys", json={"label": "Demo", "key_type": "anthropic"})
    assert key_create.status_code == 200
    assert key_create.json()["plain_text_key"].startswith("crb_")
    key_id = key_create.json()["id"]
    key_list = client.get("/api/settings/api-keys")
    assert key_list.status_code == 200
    assert len(key_list.json()) == 1

    briefing = client.post("/api/briefings/generate")
    assert briefing.status_code == 200
    briefing_id = briefing.json()["id"]
    output = briefing.json()["output"]
    assert "executive_summary" in output
    assert "portfolio_risks" in output
    assert "recommendations" in output
    assert client.post(f"/api/briefings/{briefing_id}/publish").status_code == 200
    export = client.get(f"/api/briefings/{briefing_id}/export/pdf")
    assert export.status_code == 200
    assert briefing_id in export.text

    document = client.post(
        "/api/documents/upload",
        data={"folder": "custodian_statements"},
        files={"file": ("statement.pdf", b"%PDF-1.4 demo", "application/pdf")},
    )
    assert document.status_code == 200
    document_id = document.json()["id"]
    assert client.post(f"/api/documents/{document_id}/parse").status_code == 200
    extraction = client.get(f"/api/documents/{document_id}/extraction")
    assert extraction.status_code == 200
    assert extraction.json()["needs_review_count"] == 1
    assert client.post(f"/api/documents/{document_id}/tag", json={"tag": "needs_review"}).status_code == 200
    docs = client.get("/api/documents")
    assert docs.status_code == 200
    assert docs.json()["folder_counts"]["custodian_statements"] == 1
    assert client.delete(f"/api/documents/{document_id}").status_code == 200

    revoke = client.delete(f"/api/settings/api-keys/{key_id}")
    assert revoke.status_code == 200
