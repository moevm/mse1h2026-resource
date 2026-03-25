from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RawDataSource(str, Enum):
    OPEN_TELEMETRY_TRACES = "opentelemetry-traces"
    OPEN_TELEMETRY_METRICS = "opentelemetry-metrics"
    ISTIO_METRICS = "istio-metrics"
    ISTIO_ACCESS_LOGS = "istio-access-logs"
    KUBERNETES_API = "kubernetes-api"
    PROMETHEUS = "prometheus"
    PROMETHEUS_SLO = "prometheus-slo"
    TERRAFORM_STATE = "terraform-state"
    ARGCD = "argocd"
    API_GATEWAY = "api-gateway"
    CUSTOM = "custom"


class RawDataChunk(BaseModel):
    id: str = Field(..., description="Unique chunk identifier (UUID)")
    agent_id: str = Field(..., description="ID of the agent that sent this data")
    source_type: RawDataSource = Field(..., description="Type of data source")
    timestamp: datetime = Field(..., description="When this chunk was received")
    sequence: int = Field(default=0, description="Sequence number for ordering")
    data: Dict[str, Any] = Field(..., description="The actual raw JSON payload")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Source metadata (headers, endpoint, etc.)",
    )
    size_bytes: int = Field(default=0, description="Size of the data in bytes")
    is_processed: bool = Field(default=False, description="Whether this chunk has been mapped")
    processed_at: Optional[datetime] = Field(default=None, description="When this chunk was processed")
    mapping_id: Optional[str] = Field(default=None, description="ID of the mapping used to process")


class RawDataListResponse(BaseModel):
    chunks: List[RawDataChunk]
    total: int
    timeline_min: Optional[datetime] = None
    timeline_max: Optional[datetime] = None
