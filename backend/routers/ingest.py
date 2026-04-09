from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from backend.deps import get_db
from backend.models.jobs import AsyncJob
from backend.models.portfolio import PortfolioSnapshot, Position
from backend.routers.auth import require_cookie_csrf, require_session
from backend.schemas.ingest import CsvIngestResponse, IngestStatusResponse
from backend.services.auth.session import utc_now
from backend.services.jobs import AsyncJobService
from backend.services.ingest import parse_csv_upload

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/csv", response_model=CsvIngestResponse, dependencies=[Depends(require_cookie_csrf)])
async def ingest_csv(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> CsvIngestResponse:
    _, user = auth
    raw_bytes = await file.read()

    try:
        display_name, parsed_rows, warnings = parse_csv_upload(file.filename, file.content_type, raw_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    jobs = AsyncJobService(db)
    current_snapshot = (
        db.query(PortfolioSnapshot)
        .filter(
            PortfolioSnapshot.workspace_id == user.workspace_id,
            PortfolioSnapshot.is_current.is_(True),
        )
        .one_or_none()
    )
    if current_snapshot is not None:
        demoted = db.execute(
            PortfolioSnapshot.__table__.update()
            .where(
                PortfolioSnapshot.id == current_snapshot.id,
                PortfolioSnapshot.workspace_id == user.workspace_id,
                PortfolioSnapshot.is_current.is_(True),
            )
            .values(is_current=False)
        )
        if demoted.rowcount != 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Current snapshot changed during upload. Retry the request.",
            )

    snapshot = PortfolioSnapshot(
        workspace_id=user.workspace_id,
        parent_snapshot_id=current_snapshot.id if current_snapshot is not None else None,
        uploaded_by=user.id,
        source="csv",
        source_ref=display_name,
        raw_bytes=raw_bytes,
        position_count=len(parsed_rows),
        total_aum_usd=round(sum(row.market_value_usd for row in parsed_rows), 2),
        enriched_at=None,
        is_current=True,
    )
    db.add(snapshot)
    db.flush()

    for row in parsed_rows:
        db.add(
            Position(
                snapshot_id=snapshot.id,
                workspace_id=user.workspace_id,
                security_id=None,
                ticker=row.ticker,
                name=row.name,
                position_currency=row.position_currency,
                quantity=row.quantity,
                price_local=row.price_local,
                price_usd=row.price_usd,
                market_value_local=row.market_value_local,
                market_value_usd=row.market_value_usd,
                asset_class=row.asset_class,
                geo_region=row.geo_region,
                sector=row.sector,
                market_segment=row.market_segment,
                custodian=row.custodian,
                price_source="csv_upload",
                notes=row.notes,
            )
        )

    job = jobs.create_job(
        workspace_id=user.workspace_id,
        job_type="ingest_enrichment",
        created_by=user.id,
        resource_type="snapshot",
        resource_id=snapshot.id,
        request_payload={"filename": display_name, "position_count": len(parsed_rows)},
    )
    jobs.mark_running(job, started_children=1)
    jobs.mark_finished(
        job,
        status="succeeded",
        result_payload={"snapshot_id": snapshot.id, "position_count": len(parsed_rows)},
        succeeded_children=1,
        failed_children=0,
    )
    snapshot.enriched_at = utc_now()
    db.commit()

    return CsvIngestResponse(
        snapshot_id=snapshot.id,
        job_id=job.id,
        position_count=len(parsed_rows),
        warnings=warnings,
        ready_for_enrichment=True,
    )


@router.get("/status/{job_id}", response_model=IngestStatusResponse)
def get_ingest_status(
    job_id: str,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> IngestStatusResponse:
    _, user = auth
    job = db.get(AsyncJob, job_id)
    if job is None or job.workspace_id != user.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return IngestStatusResponse(
        job_id=job.id,
        status=job.status,
        resource_type=job.resource_type,
        resource_id=job.resource_id,
        progress_pct=job.progress_pct,
        error_message=job.error_message,
    )
