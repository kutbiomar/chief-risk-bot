#!/usr/bin/env python3
"""
Seed (or reset) the ChiefRiskBot demo database to a clean, presentable state.

Usage:
    cd /path/to/chief-risk-bot
    .venv/bin/python admin/demo/seed_demo.py

Creates one real demo workspace with one CIO user, uploads the demo portfolio,
runs VaR and risk analysis, and generates a published briefing — so the
demo account starts at the cockpit with real data already loaded.

Demo credentials:
    email:    cio@demo.chiefriskbot.com
    password: DemoPass2026!
"""
from __future__ import annotations

import csv
import io
import os
import sys
import argparse
import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from openpyxl import Workbook

# Run from repo root so backend imports resolve
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

if not (ROOT / ".env").exists():
    os.environ.setdefault("DATABASE_URL", "sqlite:///backend/runtime/chiefriskbot.db")
    os.environ.setdefault("SECRET_KEY", "demo-secret-key-please-change-in-production!")
    os.environ.setdefault("ENVIRONMENT", "development")

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from backend.database import Base, engine, SessionLocal  # noqa: E402
from backend.models.auth import ApiKey, AuthChallenge, PasswordResetToken, User, UserSession, WorkspaceSetting  # noqa: E402
from backend.models.portfolio import PortfolioSnapshot, Position, Workspace  # noqa: E402
from backend.models.analytics import PriceCache, FxCache, MacroCache, VarResult, RiskScore, RiskFlag  # noqa: E402
from backend.models.audit import AuditEvent  # noqa: E402
from backend.models.content import BriefingRun, Document, ExtractionArtifact, ExtractionResult  # noqa: E402
from backend.models.jobs import AsyncJob  # noqa: E402
from backend.models.onboarding import OnboardingProgress  # noqa: E402
from backend.models.overlay import AssetFactorExposure, FactorScore, RiskRegime  # noqa: E402
from backend.models.private_markets import CapitalEvent, Commitment, Fund  # noqa: E402
from backend.services.auth.password import hash_password  # noqa: E402
from backend.services.auth.supabase import is_supabase_auth_enabled, upsert_supabase_password_user  # noqa: E402
from backend.services.documents import create_document, parse_document  # noqa: E402
from backend.services.ingest.csv_parser import parse_csv_upload  # noqa: E402
from backend.services.enrichment import ensure_enrichment_for_positions  # noqa: E402
from backend.services.var import compute_var_for_snapshot  # noqa: E402
from backend.services.risk import run_risk_analysis  # noqa: E402
from backend.services.briefings import generate_briefing, export_briefing_pdf  # noqa: E402

DEMO_EMAIL = "cio@demo.chiefriskbot.com"
DEMO_PASSWORD = "DemoPass2026!"
DEMO_WORKSPACE_NAME = "Whitmore Family Office"
DEMO_CSV = ROOT / "admin" / "demo" / "demo_portfolio.csv"


def _build_positions_workbook() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Custody Statement"
    sheet.append(["Ticker", "Security Name", "Quantity", "Market Value USD", "Asset Class", "Custodian", "Region", "Sector", "Currency"])
    sheet.append(["MSFT", "Microsoft Corp", 180, 680000, "Public Equity", "UBS", "North America", "Technology", "USD"])
    sheet.append(["LQD", "iShares iBoxx IG Corp Bond ETF", 1200, 132000, "Fixed Income", "UBS", "North America", "Credit", "USD"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _build_pending_call_workbook() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Capital Call"
    sheet.append(["Security", "Market Value USD", "Notes"])
    sheet.append(["Carlyle Growth Fund III", 425000, "Upcoming capital call due within 7 days. Manual confirmation required."])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def wipe_demo_workspace(db: Session, workspace_id: str) -> None:
    """Remove all rows tied to an existing demo workspace so we can reseed cleanly."""
    user_ids = db.scalars(select(User.id).where(User.workspace_id == workspace_id)).all()
    snapshot_ids = db.scalars(
        select(PortfolioSnapshot.id).where(PortfolioSnapshot.workspace_id == workspace_id)
    ).all()
    document_ids = db.scalars(select(Document.id).where(Document.workspace_id == workspace_id)).all()
    extraction_ids = db.scalars(
        select(ExtractionResult.id).where(ExtractionResult.document_id.in_(document_ids))
    ).all() if document_ids else []

    for model in [
        AssetFactorExposure,
        FactorScore,
        RiskRegime,
        BriefingRun,
        CapitalEvent,
        Commitment,
        Fund,
        RiskFlag,
        RiskScore,
        VarResult,
        MacroCache,
        OnboardingProgress,
        ApiKey,
        AsyncJob,
        AuditEvent,
        Document,
        WorkspaceSetting,
    ]:
        db.execute(delete(model).where(model.workspace_id == workspace_id))  # type: ignore[attr-defined]

    if extraction_ids:
        db.execute(delete(ExtractionArtifact).where(ExtractionArtifact.extraction_result_id.in_(extraction_ids)))
        db.execute(delete(ExtractionResult).where(ExtractionResult.id.in_(extraction_ids)))
    if snapshot_ids:
        db.execute(delete(Position).where(Position.snapshot_id.in_(snapshot_ids)))
        db.execute(delete(PortfolioSnapshot).where(PortfolioSnapshot.id.in_(snapshot_ids)))

    if user_ids:
        db.execute(delete(UserSession).where(UserSession.user_id.in_(user_ids)))
        db.execute(delete(AuthChallenge).where(AuthChallenge.user_id.in_(user_ids)))
        db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id.in_(user_ids)))
    db.execute(delete(User).where(User.workspace_id == workspace_id))
    db.execute(delete(Workspace).where(Workspace.id == workspace_id))
    db.commit()
    print(f"  Wiped existing workspace {workspace_id}")


def main() -> None:
    print("ChiefRiskBot — demo seed script")
    print("=" * 50)

    # Ensure tables exist (idempotent)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        supabase_identity = None
        if is_supabase_auth_enabled():
            print("  Ensuring Supabase demo auth user exists...")
            supabase_identity = upsert_supabase_password_user(
                email=DEMO_EMAIL,
                password=DEMO_PASSWORD,
                display_name="Victoria Whitmore",
            )
            print(f"  Supabase auth user ready: {supabase_identity.email}")

        # --- Wipe any existing demo user/workspace ---
        existing = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if existing:
            print(f"Found existing demo user ({DEMO_EMAIL}), wiping workspace...")
            wipe_demo_workspace(db, existing.workspace_id)

        # --- Workspace ---
        import uuid
        workspace_id = str(uuid.uuid4())
        workspace = Workspace(
            id=workspace_id,
            name=DEMO_WORKSPACE_NAME,
            slug="whitmore-family-office",
            reporting_currency="USD",
            timezone="America/New_York",
        )
        db.add(workspace)
        db.flush()

        now = datetime.now(timezone.utc)

        settings = WorkspaceSetting(
            workspace_id=workspace_id,
            briefing_day="friday",
            briefing_time="07:00",
            briefing_recipients=DEMO_EMAIL,
            briefing_auto_publish=True,
            briefing_send_pdf=True,
            updated_at=now,
        )
        db.add(settings)

        # --- User ---
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            workspace_id=workspace_id,
            email=DEMO_EMAIL,
            display_name="Victoria Whitmore",
            auth_provider="supabase" if supabase_identity else None,
            auth_subject=supabase_identity.subject if supabase_identity else None,
            role="owner",
            password_hash=hash_password(DEMO_PASSWORD),
        )
        db.add(user)

        # --- Onboarding ---
        onboarding = OnboardingProgress(
            workspace_id=workspace_id,
            current_step=5,
            completed_steps_json=json.dumps([
                "workspace_created",
                "portfolio_uploaded",
                "enrichment_run",
                "risk_run",
                "briefing_generated",
            ]),
            total_steps=5,
            completed_at=now,
        )
        db.add(onboarding)
        db.commit()
        print(f"  Created workspace: {DEMO_WORKSPACE_NAME} ({workspace_id})")
        print(f"  Created user:      {DEMO_EMAIL}")

        # --- Private markets seed for liquidity view ---
        pe_fund = Fund(
            workspace_id=workspace_id,
            name="Carlyle Growth Fund III",
            type="private_equity",
            manager_name="Carlyle",
            vintage_year=2021,
            currency="USD",
        )
        re_fund = Fund(
            workspace_id=workspace_id,
            name="Blackstone Real Estate IX",
            type="real_assets",
            manager_name="Blackstone",
            vintage_year=2022,
            currency="USD",
        )
        db.add_all([pe_fund, re_fund])
        db.flush()

        pe_commitment = Commitment(
            workspace_id=workspace_id,
            fund_id=pe_fund.id,
            committed_amount=3_500_000,
            committed_amount_base=3_500_000,
            called_capital=2_400_000,
            called_capital_base=2_400_000,
            uncalled_capital=1_100_000,
            uncalled_capital_base=1_100_000,
            distributions_received=350_000,
            distributions_received_base=350_000,
            nav=2_400_000,
            nav_base=2_400_000,
            nav_date=now.date(),
            remaining_fund_life_months=24,
        )
        re_commitment = Commitment(
            workspace_id=workspace_id,
            fund_id=re_fund.id,
            committed_amount=2_750_000,
            committed_amount_base=2_750_000,
            called_capital=1_800_000,
            called_capital_base=1_800_000,
            uncalled_capital=950_000,
            uncalled_capital_base=950_000,
            distributions_received=125_000,
            distributions_received_base=125_000,
            nav=1_800_000,
            nav_base=1_800_000,
            nav_date=now.date(),
            remaining_fund_life_months=30,
        )
        db.add_all([pe_commitment, re_commitment])
        db.flush()

        capital_events = [
            CapitalEvent(
                workspace_id=workspace_id,
                fund_id=pe_fund.id,
                commitment_id=pe_commitment.id,
                type="call",
                amount=425_000,
                amount_base=425_000,
                currency="USD",
                due_date=(now + timedelta(days=7)).date(),
                effective_date=(now + timedelta(days=7)).date(),
                is_confirmed=True,
                notes="Quarterly capital call",
            ),
            CapitalEvent(
                workspace_id=workspace_id,
                fund_id=re_fund.id,
                commitment_id=re_commitment.id,
                type="call",
                amount=210_000,
                amount_base=210_000,
                currency="USD",
                due_date=(now + timedelta(days=21)).date(),
                effective_date=(now + timedelta(days=21)).date(),
                is_confirmed=True,
                notes="Property improvement reserve",
            ),
            CapitalEvent(
                workspace_id=workspace_id,
                fund_id=pe_fund.id,
                commitment_id=pe_commitment.id,
                type="distribution",
                amount=180_000,
                amount_base=180_000,
                currency="USD",
                effective_date=(now + timedelta(days=14)).date(),
                is_confirmed=True,
                notes="Portfolio exit proceeds",
            ),
            CapitalEvent(
                workspace_id=workspace_id,
                fund_id=re_fund.id,
                commitment_id=re_commitment.id,
                type="distribution",
                amount=140_000,
                amount_base=140_000,
                currency="USD",
                effective_date=(now + timedelta(days=45)).date(),
                is_confirmed=True,
                notes="Quarterly property income distribution",
            ),
            CapitalEvent(
                workspace_id=workspace_id,
                fund_id=pe_fund.id,
                commitment_id=pe_commitment.id,
                type="fee",
                amount=55_000,
                amount_base=55_000,
                currency="USD",
                due_date=(now + timedelta(days=10)).date(),
                effective_date=(now + timedelta(days=10)).date(),
                is_confirmed=True,
                notes="Management fee",
            ),
            CapitalEvent(
                workspace_id=workspace_id,
                fund_id=re_fund.id,
                commitment_id=re_commitment.id,
                type="recallable_distribution",
                amount=95_000,
                amount_base=95_000,
                currency="USD",
                effective_date=now.date(),
                is_confirmed=True,
                recall_period_days=10,
                recall_expires_at=now,
                notes="Recall window expired",
            ),
        ]
        db.add_all(capital_events)
        db.commit()
        print("  Seeded liquidity data: 2 funds, 2 commitments, 6 capital events")

        # --- Documents seed for review queue ---
        print("  Seeding documents...")
        parsed_document = create_document(
            db,
            workspace_id=workspace_id,
            uploaded_by=user_id,
            filename="ubs_q1_custody_statement.xlsx",
            payload=_build_positions_workbook(),
            folder="custodian_statements",
        )
        asyncio.run(parse_document(db, parsed_document))
        pending_document = create_document(
            db,
            workspace_id=workspace_id,
            uploaded_by=user_id,
            filename="carlyle_capital_call_notice.xlsx",
            payload=_build_pending_call_workbook(),
            folder="private_equity",
        )
        pending_document.tag = "capital_call"
        db.commit()
        print("  Seeded documents: 1 parsed, 1 pending")

        # --- Portfolio snapshot from CSV ---
        print("  Ingesting demo portfolio...")
        csv_payload = DEMO_CSV.read_bytes()
        _, parsed_rows, warnings = parse_csv_upload(DEMO_CSV.name, "text/csv", csv_payload)
        rows = [asdict(row) for row in parsed_rows]
        snapshot_id = str(uuid.uuid4())
        snapshot = PortfolioSnapshot(
            id=snapshot_id,
            workspace_id=workspace_id,
            uploaded_by=user_id,
            source="csv_upload",
            source_ref="admin/demo/demo_portfolio.csv",
            is_current=True,
            position_count=len(rows),
            total_aum_usd=sum(r.get("market_value_usd", 0) for r in rows),
        )
        db.add(snapshot)
        db.flush()
        for row in rows:
            pos = Position(
                id=str(uuid.uuid4()),
                snapshot_id=snapshot_id,
                workspace_id=workspace_id,
                **row,
            )
            db.add(pos)
        db.commit()
        print(f"  Snapshot created: {len(rows)} positions, ${snapshot.total_aum_usd:,.0f} AUM")
        if warnings:
            print(f"  CSV warnings: {len(warnings)}")

        # Reload snapshot after commit
        snapshot = db.get(PortfolioSnapshot, snapshot_id)
        positions = db.query(Position).filter(Position.snapshot_id == snapshot_id).all()

        # --- Enrichment ---
        print("  Running market enrichment (yfinance/FRED or deterministic fallback)...")
        ensure_enrichment_for_positions(db, workspace_id, positions)
        snapshot.enriched_at = datetime.now(timezone.utc)
        db.commit()
        print("  Enrichment complete")

        # --- VaR ---
        print("  Computing VaR...")
        var_result = compute_var_for_snapshot(db, snapshot)
        db.commit()
        db.refresh(var_result)
        print(f"  VaR 1d 95%: ${var_result.var_1d_95:,.0f} ({var_result.model_coverage_pct:.0f}% coverage)")

        # --- Risk analysis ---
        print("  Running risk analysis (Claude or deterministic fallback)...")
        run_risk_analysis(db, snapshot, user_id)
        db.commit()
        print("  Risk analysis complete")

        # --- Briefing ---
        print("  Generating briefing (Claude or deterministic fallback)...")
        briefing = generate_briefing(db, snapshot, user_id)
        briefing.status = "published"
        from backend.services.auth.session import utc_now
        briefing.published_at = utc_now()
        briefing.published_by = user_id
        db.commit()
        db.refresh(briefing)
        print(f"  Briefing generated: {briefing.week_label} (published)")

        # --- PDF export ---
        print("  Exporting briefing PDF...")
        try:
            pdf_path = export_briefing_pdf(db, briefing, workspace_id)
            db.commit()
            print(f"  PDF: {pdf_path}")
        except Exception as exc:
            print(f"  PDF export skipped ({exc})")

        print()
        print("=" * 50)
        print("Demo seed complete.")
        print()
        print(f"  URL:      http://localhost:8000")
        print(f"  Email:    {DEMO_EMAIL}")
        print(f"  Password: {DEMO_PASSWORD}")
        print()
        print("Start the backend:  cd backend && ../.venv/bin/uvicorn backend.main:app --port 8001 --reload")
        print("Start the frontend: node .claude/serve.js")

    finally:
        db.close()


if __name__ == "__main__":
    main()
