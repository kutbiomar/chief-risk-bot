#!/usr/bin/env python3
"""
Seed (or reset) the ChiefRiskBot demo database to a clean, presentable state.

Usage:
    cd /path/to/chief-risk-bot
    .venv/bin/python admin/demo/seed_demo.py

Creates one demo workspace with one CIO user, uploads the demo portfolio,
runs VaR and risk analysis, and generates a published briefing — so the
demo starts at the cockpit with real data already loaded.

Demo credentials:
    email:    cio@demo.chiefrisksbot.com
    password: DemoPass2026!
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
from pathlib import Path

# Run from repo root so backend imports resolve
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

os.environ.setdefault("DATABASE_URL", "sqlite:///backend/runtime/chiefriskbot.db")
os.environ.setdefault("SECRET_KEY", "demo-secret-key-please-change-in-production!")
os.environ.setdefault("ENVIRONMENT", "development")

from sqlalchemy.orm import Session  # noqa: E402

from backend.database import Base, engine, SessionLocal  # noqa: E402
from backend.models.auth import User, UserSession, ApiKey  # noqa: E402
from backend.models.core import Workspace, WorkspaceSettings  # noqa: E402
from backend.models.portfolio import PortfolioSnapshot, Position  # noqa: E402
from backend.models.analytics import PriceCache, FxCache, MacroCache, VarResult, RiskScore, RiskFlag  # noqa: E402
from backend.models.content import BriefingRun  # noqa: E402
from backend.models.onboarding import OnboardingProgress  # noqa: E402
from backend.services.auth.password import hash_password  # noqa: E402
from backend.services.ingest.csv_parser import parse_csv  # noqa: E402
from backend.services.portfolio import summarize_positions  # noqa: E402
from backend.services.enrichment import run_enrichment  # noqa: E402
from backend.services.var import compute_var_for_snapshot  # noqa: E402
from backend.services.risk import run_risk_analysis  # noqa: E402
from backend.services.briefings import generate_briefing, export_briefing_pdf  # noqa: E402

DEMO_EMAIL = "cio@demo.chiefriskbot.com"
DEMO_PASSWORD = "DemoPass2026!"
DEMO_WORKSPACE_NAME = "Whitmore Family Office"
DEMO_CSV = ROOT / "admin" / "demo" / "demo_portfolio.csv"


def wipe_demo_workspace(db: Session, workspace_id: str) -> None:
    """Remove all rows tied to an existing demo workspace so we can reseed cleanly."""
    from sqlalchemy import delete

    for model in [
        BriefingRun,
        RiskFlag,
        RiskScore,
        VarResult,
        MacroCache,
        FxCache,
        PriceCache,
        Position,
        PortfolioSnapshot,
        OnboardingProgress,
        ApiKey,
        UserSession,
        User,
        WorkspaceSettings,
    ]:
        db.execute(delete(model).where(model.workspace_id == workspace_id))  # type: ignore[attr-defined]

    from backend.models.core import Workspace as WS
    db.execute(delete(WS).where(WS.id == workspace_id))
    db.commit()
    print(f"  Wiped existing workspace {workspace_id}")


def main() -> None:
    print("ChiefRiskBot — demo seed script")
    print("=" * 50)

    # Ensure tables exist (idempotent)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
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

        settings = WorkspaceSettings(
            workspace_id=workspace_id,
            briefing_day="friday",
            briefing_time="07:00",
            briefing_recipients=DEMO_EMAIL,
            briefing_auto_publish=True,
            briefing_send_pdf=True,
        )
        db.add(settings)

        # --- User ---
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            workspace_id=workspace_id,
            email=DEMO_EMAIL,
            display_name="Victoria Whitmore",
            role="owner",
            password_hash=hash_password(DEMO_PASSWORD),
        )
        db.add(user)

        # --- Onboarding ---
        onboarding = OnboardingProgress(
            workspace_id=workspace_id,
            current_step="briefing_generated",
            completed_steps=json.dumps([
                "workspace_created",
                "portfolio_uploaded",
                "enrichment_run",
                "risk_run",
                "briefing_generated",
            ]),
            is_complete=True,
        )
        db.add(onboarding)
        db.commit()
        print(f"  Created workspace: {DEMO_WORKSPACE_NAME} ({workspace_id})")
        print(f"  Created user:      {DEMO_EMAIL}")

        # --- Portfolio snapshot from CSV ---
        print("  Ingesting demo portfolio...")
        csv_text = DEMO_CSV.read_text()
        rows = parse_csv(io.StringIO(csv_text))
        snapshot_id = str(uuid.uuid4())
        snapshot = PortfolioSnapshot(
            id=snapshot_id,
            workspace_id=workspace_id,
            label="Demo Portfolio — Whitmore Family Office",
            source="csv_upload",
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

        # Reload snapshot after commit
        snapshot = db.get(PortfolioSnapshot, snapshot_id)

        # --- Enrichment ---
        print("  Running market enrichment (yfinance/FRED or deterministic fallback)...")
        run_enrichment(db, snapshot)
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
