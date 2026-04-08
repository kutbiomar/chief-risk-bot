from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database import Base
from backend.models.auth import User
from backend.models.portfolio import Workspace
from backend.services.audit.logger import AuditLogger
from backend.services.jobs import AsyncJobService


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    return TestingSessionLocal()


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
