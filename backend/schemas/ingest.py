from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class CsvIngestResponse(BaseModel):
    snapshot_id: str
    job_id: str
    position_count: int
    warnings: list[str]
    ready_for_enrichment: bool


class IngestStatusResponse(BaseModel):
    job_id: str
    status: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    progress_pct: Optional[int] = None
    error_message: Optional[str] = None
