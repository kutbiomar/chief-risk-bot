from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import CurrentUser, get_current_user, get_db
from ..models.content import Document, ExtractionResult
from ..models.reconciliation import ReconciliationFlag
from ..services.documents import apply_reconciliation_decision, create_document, parse_document

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size_bytes: int
    provider_name: Optional[str] = None
    auto_category: str
    processing_status: str
    extraction_result_id: Optional[str] = None
    needs_review: bool


class DocumentListResponse(BaseModel):
    total: int
    items: list[DocumentResponse]


class ExtractionResponse(BaseModel):
    id: str
    document_type: str
    classification_confidence: Optional[int] = None
    extracted_json: dict[str, Any]
    confidence_json: dict[str, Any]
    needs_review_count: int


class ReconciliationFlagResponse(BaseModel):
    id: str
    field_name: str
    document_value: Optional[str] = None
    system_value: Optional[str] = None
    variance_pct: Optional[float] = None
    severity: str
    status: str


class ReconciliationResponse(BaseModel):
    total: int
    items: list[ReconciliationFlagResponse]


class ReconciliationDecisionRequest(BaseModel):
    flag_ids: list[str]
    action: str
    notes: Optional[str] = None


class MessageResponse(BaseModel):
    detail: str


def _serialize(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        file_size_bytes=document.file_size_bytes,
        provider_name=document.provider_name,
        auto_category=document.auto_category,
        processing_status=document.processing_status,
        extraction_result_id=document.extraction_result_id,
        needs_review=document.needs_review,
    )


def _get_document_or_404(db: Session, workspace_id: str, document_id: str) -> Document:
    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id,
            Document.deleted_at.is_(None),
        )
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    provider_name: Optional[str] = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    payload = await file.read()
    document = create_document(
        db,
        workspace_id=user.workspace_id,
        uploaded_by_user_id=user.id,
        filename=file.filename or "upload.txt",
        payload=payload,
        provider_name=provider_name,
    )
    db.commit()
    db.refresh(document)
    return _serialize(document)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    category: Optional[str] = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    query = select(Document).where(
        Document.workspace_id == user.workspace_id,
        Document.deleted_at.is_(None),
    )
    if category:
        query = query.where(Document.auto_category == category)
    items = db.scalars(query.order_by(Document.created_at.desc())).all()
    return DocumentListResponse(total=len(items), items=[_serialize(item) for item in items])


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    return _serialize(_get_document_or_404(db, user.workspace_id, document_id))


@router.post("/{document_id}/parse", response_model=MessageResponse)
def parse_uploaded_document(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    document = _get_document_or_404(db, user.workspace_id, document_id)
    parse_document(db, document)
    db.commit()
    return MessageResponse(detail="Document parsed and reconciliation flags generated")


@router.get("/{document_id}/extraction", response_model=ExtractionResponse)
def get_extraction(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExtractionResponse:
    document = _get_document_or_404(db, user.workspace_id, document_id)
    if not document.extraction_result_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction not found")
    extraction = db.scalar(
        select(ExtractionResult).where(
            ExtractionResult.id == document.extraction_result_id,
            ExtractionResult.workspace_id == user.workspace_id,
        )
    )
    if extraction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction not found")
    return ExtractionResponse(
        id=extraction.id,
        document_type=extraction.document_type,
        classification_confidence=extraction.classification_confidence,
        extracted_json=extraction.extracted_json,
        confidence_json=extraction.confidence_json,
        needs_review_count=extraction.needs_review_count,
    )


@router.get("/{document_id}/reconcile", response_model=ReconciliationResponse)
def get_reconciliation_flags(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReconciliationResponse:
    _get_document_or_404(db, user.workspace_id, document_id)
    flags = db.scalars(
        select(ReconciliationFlag).where(
            ReconciliationFlag.workspace_id == user.workspace_id,
            ReconciliationFlag.document_id == document_id,
        )
    ).all()
    return ReconciliationResponse(
        total=len(flags),
        items=[
            ReconciliationFlagResponse(
                id=flag.id,
                field_name=flag.field_name,
                document_value=flag.document_value,
                system_value=flag.system_value,
                variance_pct=float(flag.variance_pct) if flag.variance_pct is not None else None,
                severity=flag.severity,
                status=flag.status,
            )
            for flag in flags
        ],
    )


@router.post("/{document_id}/reconcile", response_model=MessageResponse)
def resolve_reconciliation_flags(
    document_id: str,
    body: ReconciliationDecisionRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    document = _get_document_or_404(db, user.workspace_id, document_id)
    updated = apply_reconciliation_decision(
        db,
        workspace_id=user.workspace_id,
        document=document,
        resolution=body.model_dump(),
    )
    db.commit()
    return MessageResponse(detail=f"Updated {len(updated)} reconciliation flags")
