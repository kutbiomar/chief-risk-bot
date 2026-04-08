from __future__ import annotations

import io

from fastapi.testclient import TestClient
from openpyxl import Workbook
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


def build_statement_xlsx() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Holdings"
    sheet.append(["Ticker", "Security Name", "Quantity", "Market Value USD", "Asset Class", "Custodian", "Region"])
    sheet.append(["MSFT", "Microsoft Corp", 12, 5040, "Public Equity", "Goldman", "US"])
    sheet.append(["BND", "Vanguard Total Bond", 40, 3200, "Fixed Income", "Fidelity", "US"])
    payload = io.BytesIO()
    workbook.save(payload)
    return payload.getvalue()


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
    assert "attachment;" in export.headers["content-disposition"]
    assert f"week-15-2026_v1" in export.headers["content-disposition"]
    assert len(export.content) > 0
    if export.headers["content-type"].startswith("text/plain"):
        assert "Executive Summary" in export.text

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
    )
    assert document.status_code == 200
    document_id = document.json()["id"]
    assert client.post(f"/api/documents/{document_id}/parse").status_code == 200
    extraction = client.get(f"/api/documents/{document_id}/extraction")
    assert extraction.status_code == 200
    extraction_body = extraction.json()
    assert extraction_body["needs_review_count"] == 0
    assert extraction_body["positions"][0]["ticker"] == "MSFT"
    assert extraction_body["positions"][0]["market_value_usd"] == 5040.0
    approve = client.post(f"/api/documents/{document_id}/approve")
    assert approve.status_code == 200
    portfolio_positions = client.get("/api/portfolio/positions")
    assert portfolio_positions.status_code == 200
    assert portfolio_positions.json()["total"] == 2
    assert portfolio_positions.json()["items"][0]["ticker"] == "MSFT"
    assert client.post(f"/api/documents/{document_id}/tag", json={"tag": "imported"}).status_code == 200
    docs = client.get("/api/documents")
    assert docs.status_code == 200
    assert docs.json()["folder_counts"]["custodian_statements"] == 1
    assert client.delete(f"/api/documents/{document_id}").status_code == 200

    revoke = client.delete(f"/api/settings/api-keys/{key_id}")
    assert revoke.status_code == 200


def test_position_mutations_target_the_correct_duplicate_ticker_row(client: TestClient, db_session: Session) -> None:
    auth = bootstrap_portfolio(client, db_session, email="duplicates@example.com")
    csrf = auth["csrf"]

    for name, quantity, market_value in (
        ("Apple Legacy Lot", 3, 333.0),
        ("Apple New Lot", 7, 777.0),
    ):
        created = client.post(
            "/api/portfolio/positions",
            json={
                "ticker": "AAPL",
                "name": name,
                "quantity": quantity,
                "market_value_usd": market_value,
                "asset_class": "public_equity",
                "position_currency": "USD",
            },
            headers={"X-CSRF-Token": csrf},
        )
        assert created.status_code == 201

    positions_before = client.get("/api/portfolio/positions")
    assert positions_before.status_code == 200
    duplicate_rows = [
        item
        for item in positions_before.json()["items"]
        if item["ticker"] == "AAPL" and item["name"] in {"Apple Legacy Lot", "Apple New Lot"}
    ]
    assert len(duplicate_rows) == 2
    legacy_row = next(item for item in duplicate_rows if item["name"] == "Apple Legacy Lot")
    new_row = next(item for item in duplicate_rows if item["name"] == "Apple New Lot")

    update = client.patch(
        f"/api/portfolio/positions/{legacy_row['id']}",
        json={"quantity": 11},
        headers={"X-CSRF-Token": csrf},
    )
    assert update.status_code == 200

    positions_after_update = client.get("/api/portfolio/positions")
    assert positions_after_update.status_code == 200
    updated_rows = [
        item
        for item in positions_after_update.json()["items"]
        if item["ticker"] == "AAPL" and item["name"] in {"Apple Legacy Lot", "Apple New Lot"}
    ]
    assert len(updated_rows) == 2
    assert next(item for item in updated_rows if item["name"] == "Apple Legacy Lot")["quantity"] == 11.0
    assert next(item for item in updated_rows if item["name"] == "Apple New Lot")["quantity"] == new_row["quantity"]

    refreshed_new_row = next(item for item in updated_rows if item["name"] == "Apple New Lot")
    delete = client.delete(
        f"/api/portfolio/positions/{refreshed_new_row['id']}",
        headers={"X-CSRF-Token": csrf},
    )
    assert delete.status_code == 200

    positions_after_delete = client.get("/api/portfolio/positions")
    assert positions_after_delete.status_code == 200
    final_rows = [
        item
        for item in positions_after_delete.json()["items"]
        if item["ticker"] == "AAPL" and item["name"] in {"Apple Legacy Lot", "Apple New Lot"}
    ]
    assert len(final_rows) == 1
    assert final_rows[0]["name"] == "Apple Legacy Lot"
    assert final_rows[0]["quantity"] == 11.0
