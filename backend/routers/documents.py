from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.deps import get_db
from backend.models.content import Document, ExtractionResult
from backend.routers.auth import require_cookie_csrf, require_session
from backend.schemas.auth import MessageResponse
from backend.schemas.content import (
    DocumentListResponse,
    DocumentResponse,
    DocumentTagRequest,
    ExtractionResponse,
    ExtractionReviewResponse,
    ReviewUpdateRequest,
)
from backend.services.documents import (
    approve_document_extraction,
    create_document,
    get_document_review,
    parse_document,
    update_document_review,
)

router = APIRouter(prefix="/documents", tags=["documents"])


def _serialize(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        file_size_bytes=document.file_size_bytes,
        folder=document.folder,
        tag=document.tag,
        malware_scan_status=document.malware_scan_status,
        extraction_status=document.extraction_status,
        extraction_result_id=document.extraction_result_id,
        created_at=document.created_at,
    )


@router.post(
    "/upload",
    response_model=DocumentResponse,
    dependencies=[Depends(require_cookie_csrf)],
)
async def upload_document(
    file: UploadFile = File(...),
    folder: str = Form(default="custodian_statements"),
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    _, user = auth
    payload = await file.read()
    try:
        document = create_document(
            db,
            workspace_id=user.workspace_id,
            uploaded_by=user.id,
            filename=file.filename or "upload.pdf",
            payload=payload,
            folder=folder,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(document)
    return _serialize(document)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    _, user = auth
    items = db.scalars(
        select(Document).where(Document.workspace_id == user.workspace_id, Document.deleted_at.is_(None)).order_by(Document.created_at.desc())
    ).all()
    folder_counts: dict[str, int] = {}
    for item in items:
        folder_counts[item.folder] = folder_counts.get(item.folder, 0) + 1
    return DocumentListResponse(
        items=[_serialize(item) for item in items[offset : offset + limit]],
        folder_counts=folder_counts,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    _, user = auth
    document = db.get(Document, document_id)
    if document is None or document.workspace_id != user.workspace_id or document.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return _serialize(document)


@router.post(
    "/{document_id}/parse",
    response_model=MessageResponse,
    dependencies=[Depends(require_cookie_csrf)],
)
async def parse_uploaded_document(
    document_id: str,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> MessageResponse:
    _, user = auth
    document = db.get(Document, document_id)
    if document is None or document.workspace_id != user.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        await parse_document(db, document)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return MessageResponse(detail="Document parsed")


@router.get("/{document_id}/extraction", response_model=ExtractionResponse)
def get_extraction(
    document_id: str,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> ExtractionResponse:
    _, user = auth
    document = db.get(Document, document_id)
    if document is None or document.workspace_id != user.workspace_id or document.extraction_result_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction not found")
    extraction = db.get(ExtractionResult, document.extraction_result_id)
    if extraction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction not found")
    confidence_payload = json.loads(extraction.confidence_json)
    confidence_rows = confidence_payload.get("rows", []) if isinstance(confidence_payload, dict) else confidence_payload
    return ExtractionResponse(
        id=extraction.id,
        positions=json.loads(extraction.positions_json),
        confidence=confidence_rows,
        needs_review_count=extraction.needs_review_count,
        raw_text_truncated=extraction.raw_text_truncated,
    )


@router.get("/{document_id}/review", response_model=ExtractionReviewResponse)
def get_review(
    document_id: str,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> ExtractionReviewResponse:
    _, user = auth
    document = db.get(Document, document_id)
    if document is None or document.workspace_id != user.workspace_id or document.extraction_result_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction not found")
    try:
        payload = get_document_review(db, document)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ExtractionReviewResponse(**payload)


@router.patch(
    "/{document_id}/review",
    response_model=ExtractionReviewResponse,
    dependencies=[Depends(require_cookie_csrf)],
)
def patch_review(
    document_id: str,
    payload: ReviewUpdateRequest,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> ExtractionReviewResponse:
    _, user = auth
    document = db.get(Document, document_id)
    if document is None or document.workspace_id != user.workspace_id or document.extraction_result_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction not found")
    try:
        update_document_review(
            db,
            document,
            positions=payload.positions,
            treasury=payload.treasury,
            resolved_fields=payload.resolved_fields,
        )
        review = get_document_review(db, document)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return ExtractionReviewResponse(**review)


@router.post(
    "/{document_id}/tag",
    response_model=DocumentResponse,
    dependencies=[Depends(require_cookie_csrf)],
)
def tag_document(
    document_id: str,
    payload: DocumentTagRequest,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    _, user = auth
    document = db.get(Document, document_id)
    if document is None or document.workspace_id != user.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    document.tag = payload.tag
    db.commit()
    db.refresh(document)
    return _serialize(document)


@router.post(
    "/{document_id}/approve",
    response_model=MessageResponse,
    dependencies=[Depends(require_cookie_csrf)],
)
def approve_document(
    document_id: str,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> MessageResponse:
    _, user = auth
    document = db.get(Document, document_id)
    if document is None or document.workspace_id != user.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        snapshot = approve_document_extraction(db, document)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return MessageResponse(detail=f"Document extraction approved into snapshot {snapshot.id}")


@router.delete(
    "/{document_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_cookie_csrf)],
)
def delete_document(
    document_id: str,
    auth=Depends(require_session),
    db: Session = Depends(get_db),
) -> MessageResponse:
    _, user = auth
    document = db.get(Document, document_id)
    if document is None or document.workspace_id != user.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    from backend.services.auth.session import utc_now

    document.deleted_at = utc_now()
    db.commit()
    return MessageResponse(detail="Document deleted")
