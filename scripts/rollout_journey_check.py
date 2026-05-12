#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import tempfile
from typing import Any

os.environ.setdefault("AUTH_MODE", "local")
os.environ.setdefault("SECRET_KEY", "rollout-journey-local-secret")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.deps import get_db
from backend.main import app
from backend.models.auth import PasswordResetToken


ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT_DIR / "frontend-mvp"


class JourneyFailure(RuntimeError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise JourneyFailure(message)


def pass_step(message: str) -> None:
    print(f"PASS: {message}")


def build_statement_xlsx() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Holdings"
    sheet.append(
        [
            "Ticker",
            "Security Name",
            "Quantity",
            "Market Value USD",
            "Asset Class",
            "Custodian",
            "Region",
            "Sector",
            "Market Segment",
        ]
    )
    sheet.append(["MSFT", "Microsoft Corp", 12, 5040, "Public Equity", "Goldman", "US", "Technology", "Large Cap"])
    sheet.append(["BND", "Vanguard Total Bond", 40, 3200, "Fixed Income", "Fidelity", "US", "Fixed Income", "IG Credit"])
    payload = io.BytesIO()
    workbook.save(payload)
    return payload.getvalue()


def build_capital_call_xlsx() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Capital Call"
    sheet.append(["Capital Call Notice"])
    sheet.append(["Due Date", "2026-04-30"])
    sheet.append(["Amount", "$1,250,000"])
    sheet.append(["Bank", "First Private Bank"])
    sheet.append(["Account Number", "99887766"])
    sheet.append(["ABA", "021000021"])
    payload = io.BytesIO()
    workbook.save(payload)
    return payload.getvalue()


def require_status(response: Any, expected: int, label: str) -> dict[str, Any]:
    expect(response.status_code == expected, f"{label} returned {response.status_code}: {response.text[:300]}")
    if response.content:
        return response.json()
    return {}


def csrf_headers(client: TestClient) -> dict[str, str]:
    csrf = client.cookies.get("__crb_csrf")
    expect(bool(csrf), "csrf cookie missing after login/register")
    return {"X-CSRF-Token": str(csrf)}


def verify_frontend_contract() -> None:
    required_pages = {
        "index": "index.html",
        "assets": "assets.html",
        "cockpit": "cockpit.html",
        "liquidity": "liquidity.html",
        "briefings": "briefings.html",
        "documents": "documents.html",
        "table": "table.html",
        "settings": "settings.html",
        "access": "access.html",
        "scenarios": "scenarios.html",
        "onboarding": "onboarding.html",
        "login": "login.html",
    }
    for page, filename in required_pages.items():
        html_path = FRONTEND_DIR / filename
        expect(html_path.exists(), f"missing frontend page {filename}")
        html = html_path.read_text(encoding="utf-8")
        expect(f'data-page="{page}"' in html, f"{filename} missing data-page={page}")
        expect("_app.js" in html, f"{filename} missing shared app script")
        if page != "login":
            expect("_shell.js" in html, f"{filename} missing shared navigation shell script")
    access_html = (FRONTEND_DIR / "access.html").read_text(encoding="utf-8")
    expect("admin-assisted for the v1 design-partner rollout" in access_html, "access page does not disclose v1 team-management limits")
    pass_step("frontend route/static contract")


def run_journeys(client: TestClient, db: Session) -> None:
    register = client.post(
        "/api/auth/register",
        json={
            "workspace_name": "Rollout Family Office",
            "display_name": "Rollout Tester",
            "email": "rollout-check@example.com",
            "password": "secret123",
            "timezone": "Europe/Zurich",
            "reporting_currency": "CHF",
        },
    )
    session = require_status(register, 200, "register")
    expect(session["user"]["workspace_name"] == "Rollout Family Office", "registered workspace mismatch")
    pass_step("fresh workspace registration")

    headers = csrf_headers(client)
    onboarding = require_status(client.get("/api/onboarding/state"), 200, "onboarding state")
    expect(onboarding["current_step"] == 1, "new workspace onboarding step mismatch")

    csv_payload = (
        "ticker,quantity,asset_class,custodian,geo_region,sector,market_segment,market_value_usd\n"
        "AAPL,10,public_equity,Goldman,US,Technology,Large Cap,1900\n"
        "BND,20,fixed_income,Fidelity,US,Fixed Income,IG Credit,1500\n"
        "VGK,15,public_equity,Goldman,Europe,Financials,Large Cap,800\n"
    )
    ingest = require_status(
        client.post("/api/ingest/csv", files={"file": ("positions.csv", csv_payload, "text/csv")}, headers=headers),
        200,
        "csv ingest",
    )
    expect(ingest["position_count"] == 3, "csv ingest row count mismatch")
    pass_step("onboarding position import")

    for endpoint in (
        "/api/portfolio/summary",
        "/api/portfolio/positions",
        "/api/cockpit",
        "/api/liquidity/summary",
        "/api/overlay/factors",
        "/api/overlay/stress",
        "/api/settings",
        "/api/settings/members",
    ):
        require_status(client.get(endpoint), 200, endpoint)
    pass_step("core P0/P1 API surfaces")

    positions = require_status(client.get("/api/portfolio/positions"), 200, "positions list")
    target = positions["items"][0]
    updated = require_status(
        client.patch(f"/api/portfolio/positions/{target['id']}", json={"quantity": target["quantity"] + 1}, headers=headers),
        200,
        "position update",
    )
    updated_positions = require_status(client.get("/api/portfolio/positions"), 200, "positions after update")
    updated_row = next(item for item in updated_positions["items"] if item["id"] == updated["position_id"])
    expect(updated_row["quantity"] == target["quantity"] + 1, "position update did not persist")
    created = require_status(
        client.post(
            "/api/portfolio/positions",
            json={
                "ticker": "CASH",
                "name": "Cash reserve",
                "quantity": 1,
                "market_value_usd": 250000,
                "position_currency": "USD",
                "asset_class": "cash",
                "geo_region": "US",
                "sector": "Cash",
                "market_segment": "Treasury",
            },
            headers=headers,
        ),
        201,
        "position create",
    )
    require_status(client.delete(f"/api/portfolio/positions/{created['position_id']}", headers=headers), 200, "position delete")
    pass_step("positions create/update/delete")

    document = require_status(
        client.post(
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
        ),
        200,
        "document upload",
    )
    document_id = document["id"]
    require_status(client.post(f"/api/documents/{document_id}/parse", headers=headers), 200, "document parse")
    review = require_status(client.get(f"/api/documents/{document_id}/review"), 200, "document review")
    expect(review["positions"][0]["source_ref"]["sheet_name"] == "Holdings", "document review source reference missing")
    require_status(client.post(f"/api/documents/{document_id}/approve", headers=headers), 200, "document approve")
    require_status(client.delete(f"/api/documents/{document_id}", headers=headers), 200, "document delete")
    pass_step("document upload/parse/review/approve/delete")

    cap_call = require_status(
        client.post(
            "/api/documents/upload",
            data={"folder": "capital_calls"},
            files={
                "file": (
                    "capital-call.xlsx",
                    build_capital_call_xlsx(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            headers=headers,
        ),
        200,
        "capital-call upload",
    )
    cap_call_id = cap_call["id"]
    require_status(client.post(f"/api/documents/{cap_call_id}/parse", headers=headers), 200, "capital-call parse")
    cap_review = require_status(client.get(f"/api/documents/{cap_call_id}/review"), 200, "capital-call review")
    expect(cap_review["field_reviews"][0]["resolved"] is False, "capital-call should require HITL review")
    cap_review["positions"][0].update(
        {
            "ticker": "BLUERIVER",
            "name": "BlueRiver Capital Call",
            "quantity": 1,
            "market_value_usd": 1250000,
            "asset_class": "private_equity",
            "geo_region": "US",
            "sector": "Alternatives",
            "market_segment": "Private Equity",
            "factor_asset_class": "private_equity",
            "factor_sector": "alternatives",
            "factor_region": "us",
            "factor_market_segment": "private_equity",
        }
    )
    require_status(
        client.patch(
            f"/api/documents/{cap_call_id}/review",
            json={
                "positions": cap_review["positions"],
                "treasury": {
                    "wire_bank": "First Private Bank Zurich",
                    "wire_account": "9988776655",
                    "wire_routing": "021000021",
                    "wire_reference": "BlueRiver Q2",
                    "contact_email": "ops@blueriver.com",
                },
                "resolved_fields": ["wire_instructions"],
            },
            headers=headers,
        ),
        200,
        "capital-call review patch",
    )
    require_status(client.post(f"/api/documents/{cap_call_id}/approve", headers=headers), 200, "capital-call approve")
    pass_step("HITL document review resolution")

    require_status(client.post("/api/var/compute", headers=headers), 200, "var compute")
    require_status(client.post("/api/risk/run", headers=headers), 200, "risk run")
    briefing = require_status(client.post("/api/briefings/generate", headers=headers), 200, "briefing generate")
    briefing_id = briefing["id"]
    expect("executive_summary" in briefing["output"], "briefing missing executive summary")
    require_status(client.get(f"/api/briefings/{briefing_id}"), 200, "briefing detail")
    pdf = client.get(f"/api/briefings/{briefing_id}/export/pdf")
    expect(pdf.status_code in {200, 503}, f"briefing export returned {pdf.status_code}: {pdf.text[:300]}")
    if pdf.status_code == 200:
        expect(pdf.content.startswith(b"%PDF"), "briefing export did not return PDF bytes")
    pass_step("briefing generate/detail/export")

    settings = require_status(
        client.patch("/api/settings", json={"briefing_day": "Friday", "briefing_send_pdf": True}, headers=headers),
        200,
        "settings save",
    )
    expect(settings["briefing_day"] == "Friday", "settings save mismatch")
    access = require_status(client.get("/api/settings/members"), 200, "members list")
    expect(access["items"][0]["email"] == "rollout-check@example.com", "members list missing current user")
    pass_step("settings and access/member profile")

    forgot = require_status(
        client.post("/api/auth/forgot-password", json={"email": "rollout-check@example.com"}, headers=headers),
        200,
        "forgot password",
    )
    expect(forgot.get("accepted") is True, "forgot password response not accepted")
    token_row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.invalidated_at.is_(None)))
    expect(token_row is not None, "password reset token row missing")
    raw_reset_token = "rollout-reset-token"
    token_row.token_hash = hashlib.sha256(raw_reset_token.encode("utf-8")).hexdigest()
    db.commit()
    require_status(
        client.post(
            "/api/auth/reset-password",
            json={"token": raw_reset_token, "new_password": "new-secret456"},
            headers=headers,
        ),
        200,
        "reset password",
    )
    old_login = client.post("/api/auth/login", json={"email": "rollout-check@example.com", "password": "secret123"})
    expect(old_login.status_code == 401, "old password still works after reset")
    new_login = require_status(
        client.post("/api/auth/login", json={"email": "rollout-check@example.com", "password": "new-secret456"}),
        200,
        "new password login",
    )
    expect(new_login.get("user", {}).get("email") == "rollout-check@example.com", "new-password login user mismatch")
    headers = csrf_headers(client)
    require_status(client.post("/api/auth/logout", headers=headers), 200, "logout")
    logged_out = client.get("/api/auth/session")
    expect(logged_out.status_code == 401, "session still valid after logout")
    invalid = client.get("/api/auth/session", headers={"Authorization": "Bearer invalid-rollout-token"})
    expect(invalid.status_code == 401, "invalid bearer token accepted")
    pass_step("password reset, logout, invalid-session rejection")


def main() -> None:
    verify_frontend_contract()
    with tempfile.TemporaryDirectory(prefix="crb-rollout-") as tmp_dir:
        engine = create_engine(
            f"sqlite:///{Path(tmp_dir) / 'rollout.db'}",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
        db = SessionLocal()

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app) as client:
                run_journeys(client, db)
        finally:
            app.dependency_overrides.clear()
            db.close()
    print("Rollout journey check complete.")


if __name__ == "__main__":
    main()
