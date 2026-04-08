from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.models.auth import WorkspaceSetting
from backend.models.content import BriefingRun
from backend.models.portfolio import PortfolioSnapshot, Position
from backend.database import Base
from backend.models.auth import User
from backend.models.portfolio import Workspace
from backend.services.audit.logger import AuditLogger
from backend.services.jobs import AsyncJobService
from backend.services.scheduler import BriefingSchedulerManager, run_workspace_briefing_cycle


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    return TestingSessionLocal()


def make_session_factory() -> sessionmaker:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def test_audit_logger_assigns_sequence_and_hash_chain() -> None:
    db = make_session()
    workspace = Workspace(
        name="Test Workspace",
        slug="test-workspace",
        reporting_currency="USD",
        timezone="UTC",
        plan="starter",
    )
    db.add(workspace)
    db.flush()
    user = User(
        workspace_id=workspace.id,
        email="owner@example.com",
        display_name="Owner",
        password_hash="not-needed-for-this-test",
        role="owner",
        scope="All clients",
        totp_enabled=False,
    )
    db.add(user)
    db.commit()

    logger = AuditLogger(db)
    first = logger.append_event(
        workspace_id=workspace.id,
        actor_user_id=user.id,
        actor_type="user",
        event_type="auth",
        action="logged_in",
        subject_type="session",
        subject_id="s1",
    )
    second = logger.append_event(
        workspace_id=workspace.id,
        actor_user_id=user.id,
        actor_type="user",
        event_type="auth",
        action="logged_out",
        subject_type="session",
        subject_id="s1",
    )
    db.commit()

    assert first.sequence_no == 1
    assert first.prev_hash == "GENESIS"
    assert second.sequence_no == 2
    assert second.prev_hash == first.event_hash
    db.close()


def test_async_job_service_tracks_status() -> None:
    db = make_session()
    workspace = Workspace(
        name="Test Workspace",
        slug="jobs-workspace",
        reporting_currency="USD",
        timezone="UTC",
        plan="starter",
    )
    db.add(workspace)
    db.commit()

    service = AsyncJobService(db)
    job = service.create_job(workspace_id=workspace.id, job_type="risk_run")
    service.mark_running(job, started_children=5)
    service.mark_finished(
        job,
        status="succeeded",
        result_payload={"ok": True},
        succeeded_children=5,
        failed_children=0,
    )
    db.commit()

    saved = service.get_job(job.id)
    assert saved is not None
    assert saved.status == "succeeded"
    assert saved.started_children == 5
    assert saved.succeeded_children == 5
    db.close()


def test_scheduler_syncs_workspace_job() -> None:
    db = make_session()
    workspace = Workspace(
        name="Schedule Workspace",
        slug="schedule-workspace",
        reporting_currency="USD",
        timezone="Europe/Zurich",
        plan="starter",
    )
    db.add(workspace)
    db.flush()
    db.add(
        WorkspaceSetting(
            workspace_id=workspace.id,
            briefing_day="Friday",
            briefing_time="07:30",
            briefing_recipients="cio@example.com",
            briefing_auto_publish=True,
            briefing_send_pdf=True,
            briefing_include_audit_footer=False,
            ai_model="claude-opus-4-6",
            ai_risk_tone="conservative",
            ai_allow_trade_actions=False,
            sso_mode="disabled",
            updated_at=workspace.created_at,
        )
    )
    db.commit()

    manager = BriefingSchedulerManager(enabled=True, db_factory=lambda: db)
    manager.sync_workspace_job(workspace.id)
    job = manager.scheduler.get_job(f"weekly-briefing:{workspace.id}")

    assert job is not None
    assert str(job.trigger.timezone) == "Europe/Zurich"
    assert "fri" in str(job.trigger).lower()
    assert "7" in str(job.trigger)
    db.close()


def test_scheduled_briefing_cycle_generates_publishes_and_exports() -> None:
    session_factory = make_session_factory()
    db = session_factory()
    workspace = Workspace(
        name="Briefing Workspace",
        slug="briefing-workspace",
        reporting_currency="USD",
        timezone="UTC",
        plan="starter",
    )
    db.add(workspace)
    db.flush()
    user = User(
        workspace_id=workspace.id,
        email="owner@example.com",
        display_name="Owner",
        password_hash="not-needed",
        role="owner",
        scope="All clients",
        totp_enabled=False,
    )
    db.add(user)
    db.flush()
    db.add(
        WorkspaceSetting(
            workspace_id=workspace.id,
            briefing_day="Monday",
            briefing_time="06:00",
            briefing_recipients="cio@example.com",
            briefing_auto_publish=True,
            briefing_send_pdf=True,
            briefing_include_audit_footer=False,
            ai_model="claude-opus-4-6",
            ai_risk_tone="conservative",
            ai_allow_trade_actions=False,
            sso_mode="disabled",
            updated_at=workspace.created_at,
        )
    )
    snapshot = PortfolioSnapshot(
        workspace_id=workspace.id,
        uploaded_by=user.id,
        source="csv",
        position_count=2,
        total_aum_usd=2700.0,
        is_current=True,
    )
    db.add(snapshot)
    db.flush()
    db.add_all(
        [
            Position(
                snapshot_id=snapshot.id,
                workspace_id=workspace.id,
                ticker="AAPL",
                name="Apple",
                position_currency="USD",
                quantity=10,
                price_usd=190,
                market_value_usd=1900,
                asset_class="public_equity",
                geo_region="US",
                sector="Technology",
                market_segment="Large Cap",
                custodian="Goldman",
                price_source="manual",
            ),
            Position(
                snapshot_id=snapshot.id,
                workspace_id=workspace.id,
                ticker="BND",
                name="Bond ETF",
                position_currency="USD",
                quantity=20,
                price_usd=40,
                market_value_usd=800,
                asset_class="fixed_income",
                geo_region="US",
                sector="Fixed Income",
                market_segment="IG Credit",
                custodian="Fidelity",
                price_source="manual",
            ),
        ]
    )
    workspace_id = workspace.id
    db.commit()
    db.close()

    result = run_workspace_briefing_cycle(workspace_id, db_factory=session_factory)

    assert result.status == "succeeded"
    assert result.briefing_id is not None

    verify_db = session_factory()
    saved = verify_db.scalar(select(BriefingRun).where(BriefingRun.id == result.briefing_id))
    assert saved is not None
    assert saved.status == "published"
    if saved.pdf_path is not None:
        assert Path(saved.pdf_path).exists()
    else:
        assert result.detail == "PDF export unavailable — WeasyPrint system libraries not installed"
    verify_db.close()
