from typing import Optional
from pydantic import BaseModel


class DependencyHealth(BaseModel):
    status: str
    detail: str
    latency_ms: Optional[float] = None


class ObservabilitySnapshot(BaseModel):
    requests_total: float
    requests_5xx: float
    error_rate_5xx: float
    avg_latency_ms: float
    db_queries_total: float
    db_query_avg_ms: float


class HealthResponse(BaseModel):
    status: str
    environment: str
    checked_at: str
    components: dict[str, DependencyHealth]
    metrics: ObservabilitySnapshot
