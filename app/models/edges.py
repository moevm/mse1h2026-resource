from __future__ import annotations
from datetime import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class EdgeBase(BaseModel):
    model_config = ConfigDict(extra="allow")
    source_id: str = Field(..., description="URN of the source node")
    target_id: str = Field(..., description="URN of the target node")
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    weight: Optional[float] = 1.0
    status: Optional[str] = "active"


class CallsEdge(EdgeBase):
    type: Literal["calls"] = "calls"
    protocol: Optional[str] = None
    rps: Optional[float] = None
    latency_p99_ms: Optional[float] = None
    error_rate_percent: Optional[float] = None
    timeout_ms: Optional[int] = None
    retry_count: Optional[int] = None
    circuit_breaker_enabled: Optional[bool] = None
    circuit_breaker_state: Optional[str] = None
    payload_size_bytes: Optional[int] = None
    latency_p50_ms: Optional[float] = None
    request_content_type: Optional[str] = None


class PublishesToEdge(EdgeBase):
    type: Literal["publishesto"] = "publishesto"
    message_size_bytes: Optional[int] = None
    batch_size: Optional[int] = None
    compression: Optional[str] = None
    qos_level: Optional[int] = None
    routing_key: Optional[str] = None
    partition_key: Optional[str] = None
    messages_per_second: Optional[float] = None
    ack_mode: Optional[str] = None


class ConsumesFromEdge(EdgeBase):
    type: Literal["consumesfrom"] = "consumesfrom"
    consumer_group: Optional[str] = None
    lag_messages: Optional[int] = None
    processing_time_ms: Optional[float] = None
    auto_commit: Optional[bool] = None
    prefetch_count: Optional[int] = None
    concurrent_consumers: Optional[int] = None
    messages_per_second: Optional[float] = None


class ReadsEdge(EdgeBase):
    type: Literal["reads"] = "reads"
    query_type: Optional[str] = None
    rows_returned: Optional[int] = None
    index_used: Optional[bool] = None
    latency_ms: Optional[float] = None
    connection_pool_size: Optional[int] = None
    cache_hit_ratio: Optional[float] = None
    queries_per_second: Optional[float] = None
    rows_examined: Optional[int] = None


class WritesEdge(EdgeBase):
    type: Literal["writes"] = "writes"
    query_type: Optional[str] = None
    bytes_written: Optional[int] = None
    transaction_isolation: Optional[str] = None
    latency_ms: Optional[float] = None
    batch_size: Optional[int] = None
    is_upsert: Optional[bool] = None
    writes_per_second: Optional[float] = None


class DependsOnEdge(EdgeBase):
    type: Literal["dependson"] = "dependson"
    criticality: Optional[str] = None
    fallback_available: Optional[bool] = None
    circuit_breaker_state: Optional[str] = None
    is_async: Optional[bool] = None
    impact_score: Optional[float] = None
    health_check_status: Optional[str] = None


class DeployedOnEdge(EdgeBase):
    type: Literal["deployedon"] = "deployedon"
    path: Optional[str] = None
    isolation_level: Optional[str] = None
    resource_requests_cpu: Optional[float] = None
    resource_requests_mem_mb: Optional[int] = None
    resource_limits_cpu: Optional[float] = None
    resource_limits_mem_mb: Optional[int] = None
    resource_requests_cpu_m: Optional[int] = None
    resource_limits_cpu_m: Optional[int] = None
    mount_path: Optional[str] = None


class OwnedByEdge(EdgeBase):
    type: Literal["ownedby"] = "ownedby"
    ownership_type: Optional[str] = None
    escalation_policy: Optional[str] = None
    escalation_level: Optional[int] = None
    review_frequency_days: Optional[int] = None
    last_reviewed_at: Optional[datetime] = None


class AuthenticatesViaEdge(EdgeBase):
    type: Literal["authenticatesvia"] = "authenticatesvia"
    auth_method: Optional[str] = None
    token_expiry_seconds: Optional[int] = None
    scopes: Optional[List[str]] = None
    mfa_required: Optional[bool] = None
    issuer: Optional[str] = None
    last_rotated_days_ago: Optional[int] = None


class RateLimitedByEdge(EdgeBase):
    type: Literal["ratelimitedby"] = "ratelimitedby"
    limit_type: Optional[str] = None
    max_requests: Optional[int] = None
    window_seconds: Optional[int] = None
    algorithm: Optional[str] = None
    throttle_strategy: Optional[str] = None
    burst_capacity: Optional[int] = None
    current_usage: Optional[float] = None
    current_usage_pct: Optional[float] = None
    throttled_count_1h: Optional[int] = None


class FailsOverToEdge(EdgeBase):
    type: Literal["fails_over_to"] = "fails_over_to"
    trigger_condition: Optional[str] = None
    failover_latency_ms: Optional[int] = None
    is_active_active: Optional[bool] = None
    data_loss_acceptable: Optional[bool] = None
    last_tested_at: Optional[datetime] = None
    failover_time_seconds: Optional[int] = None
    last_tested_days_ago: Optional[int] = None


AnyEdge = Annotated[
    Union[
        CallsEdge,
        PublishesToEdge,
        ConsumesFromEdge,
        ReadsEdge,
        WritesEdge,
        DependsOnEdge,
        DeployedOnEdge,
        OwnedByEdge,
        AuthenticatesViaEdge,
        RateLimitedByEdge,
        FailsOverToEdge,
    ],
    Field(discriminator="type"),
]
