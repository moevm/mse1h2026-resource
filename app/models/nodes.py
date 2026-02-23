from __future__ import annotations
from datetime import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class NodeBase(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(
        ..., description="Global URN identifier (e.g. urn:service:payment-api)"
    )
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    environment: Optional[str] = None
    status: Optional[str] = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ServiceNode(NodeBase):
    type: Literal["Service"] = "Service"
    language: Optional[str] = None
    framework: Optional[str] = None
    version: Optional[str] = None
    repository_url: Optional[str] = None
    commit_hash: Optional[str] = None
    tier: Optional[int] = Field(None, ge=1, le=4, description="Criticality tier 1‑4")
    is_external: Optional[bool] = False
    build_id: Optional[str] = None
    runtime_version: Optional[str] = None
    memory_allocated_mb: Optional[int] = None
    cpu_allocated_cores: Optional[float] = None
    rps: Optional[float] = None
    latency_p99_ms: Optional[float] = None
    error_rate_percent: Optional[float] = None
    active_connections: Optional[int] = None


class EndpointNode(NodeBase):
    type: Literal["Endpoint"] = "Endpoint"
    path: Optional[str] = None
    method: Optional[str] = None
    rps_limit: Optional[float] = None
    timeout_ms: Optional[int] = None
    is_public: Optional[bool] = False
    payload_format: Optional[str] = None
    openapi_spec_url: Optional[str] = None
    auth_required: Optional[bool] = None
    deprecated: Optional[bool] = False
    current_rps: Optional[float] = None
    latency_p50_ms: Optional[float] = None
    latency_p99_ms: Optional[float] = None
    error_count_1h: Optional[int] = None


class DeploymentNode(NodeBase):
    type: Literal["Deployment"] = "Deployment"
    replicas_desired: Optional[int] = None
    replicas_ready: Optional[int] = None
    strategy: Optional[str] = None
    namespace: Optional[str] = None
    cluster_id: Optional[str] = None
    image_tag: Optional[str] = None
    helm_chart_version: Optional[str] = None
    last_deployed_at: Optional[datetime] = None
    rollback_revision: Optional[int] = None
    replicas_available: Optional[int] = None
    replicas_unavailable: Optional[int] = None


class PodNode(NodeBase):
    type: Literal["Pod"] = "Pod"
    namespace: Optional[str] = None
    node_name: Optional[str] = None
    ip_address: Optional[str] = None
    phase: Optional[str] = None
    restart_count: Optional[int] = None
    cpu_usage_m: Optional[int] = None
    memory_usage_mi: Optional[int] = None
    service_account: Optional[str] = None
    qos_class: Optional[str] = None


class ComputeNodeNode(NodeBase):
    type: Literal["Node"] = "Node"
    instance_type: Optional[str] = None
    os_image: Optional[str] = None
    kernel_version: Optional[str] = None
    kubelet_version: Optional[str] = None
    architecture: Optional[str] = None
    capacity_cpu: Optional[int] = None
    capacity_memory_gb: Optional[float] = None
    region: Optional[str] = None
    zone: Optional[str] = None
    internal_ip: Optional[str] = None
    external_ip: Optional[str] = None
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    disk_pressure: Optional[bool] = None
    network_unavailable: Optional[bool] = None


class DatabaseNode(NodeBase):
    type: Literal["Database"] = "Database"
    engine: Optional[str] = None
    version: Optional[str] = None
    capacity_gb: Optional[float] = None
    connection_string: Optional[str] = None
    is_managed: Optional[bool] = None
    region: Optional[str] = None
    instance_class: Optional[str] = None
    max_connections: Optional[int] = None
    backup_retention_days: Optional[int] = None
    multi_az: Optional[bool] = None
    active_connections: Optional[int] = None
    queries_per_second: Optional[float] = None
    replication_lag_ms: Optional[float] = None
    disk_usage_percent: Optional[float] = None


class TableNode(NodeBase):
    type: Literal["Table"] = "Table"
    schema_name: Optional[str] = None
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    primary_key: Optional[List[str]] = None
    is_partitioned: Optional[bool] = None
    retention_days: Optional[int] = None
    index_count: Optional[int] = None
    last_vacuumed_at: Optional[datetime] = None
    table_locks: Optional[int] = None
    rows_inserted_per_min: Optional[int] = None
    rows_updated_per_min: Optional[int] = None
    avg_query_time_ms: Optional[float] = None
    dead_tuples_pct: Optional[float] = None


class QueueTopicNode(NodeBase):
    type: Literal["QueueTopic"] = "QueueTopic"
    broker: Optional[str] = None
    partitions: Optional[int] = None
    retention_bytes: Optional[int] = None
    retention_ms: Optional[int] = None
    message_rate: Optional[float] = None
    consumer_groups: Optional[List[str]] = None
    max_message_size_bytes: Optional[int] = None
    replication_factor: Optional[int] = None
    is_dead_letter: Optional[bool] = False
    consumer_lag: Optional[int] = None
    bytes_per_second: Optional[int] = None


class CacheNode(NodeBase):
    type: Literal["Cache"] = "Cache"
    engine: Optional[str] = None
    eviction_policy: Optional[str] = None
    max_memory_mb: Optional[int] = None
    hit_rate_target: Optional[float] = None
    keys_count: Optional[int] = None
    connected_clients: Optional[int] = None
    uptime_days: Optional[float] = None
    hit_rate: Optional[float] = None
    memory_usage_mb: Optional[int] = None
    evictions_per_sec: Optional[int] = None


class ExternalAPINode(NodeBase):
    type: Literal["ExternalAPI"] = "ExternalAPI"
    provider: Optional[str] = None
    base_url: Optional[str] = None
    auth_type: Optional[str] = None
    rate_limit_tier: Optional[str] = None
    sla_percentage: Optional[float] = None
    support_email: Optional[str] = None
    documentation_url: Optional[str] = None
    ip_whitelisted: Optional[bool] = None
    response_time_ms: Optional[float] = None
    availability_percent: Optional[float] = None
    rate_limit_remaining: Optional[int] = None


class SecretConfigNode(NodeBase):
    type: Literal["SecretConfig"] = "SecretConfig"
    provider: Optional[str] = None
    key_names: Optional[List[str]] = None
    rotation_interval_days: Optional[int] = None
    last_rotated: Optional[datetime] = None
    is_encrypted: Optional[bool] = None
    algorithm: Optional[str] = None
    vault_path: Optional[str] = None
    expiration_date: Optional[datetime] = None
    last_rotated_days_ago: Optional[int] = None
    access_count_1h: Optional[int] = None


class LibraryNode(NodeBase):
    type: Literal["Library"] = "Library"
    package_manager: Optional[str] = None
    version: Optional[str] = None
    license: Optional[str] = None
    cve_count: Optional[int] = None
    is_internal: Optional[bool] = None
    repository: Optional[str] = None
    author: Optional[str] = None
    deprecated: Optional[bool] = False
    is_latest: Optional[bool] = None
    vulnerabilities_found: Optional[int] = None


class TeamOwnerNode(NodeBase):
    type: Literal["TeamOwner"] = "TeamOwner"
    email: Optional[str] = None
    slack_channel: Optional[str] = None
    pagerduty_service: Optional[str] = None
    lead_name: Optional[str] = None
    department: Optional[str] = None
    cost_center: Optional[str] = None
    on_call_schedule: Optional[str] = None
    active_incidents: Optional[int] = None
    services_owned_count: Optional[int] = None


class SLASLONode(NodeBase):
    type: Literal["SLASLO"] = "SLASLO"
    metric_name: Optional[str] = None
    target_percentage: Optional[float] = None
    window_days: Optional[int] = None
    current_value: Optional[float] = None
    alert_threshold: Optional[float] = None
    violation_count: Optional[int] = None
    monitoring_url: Optional[str] = None
    error_budget_remaining_pct: Optional[float] = None


class RegionClusterNode(NodeBase):
    type: Literal["RegionCluster"] = "RegionCluster"
    provider: Optional[str] = None
    region_code: Optional[str] = None
    zones: Optional[List[str]] = None
    k8s_version: Optional[str] = None
    node_count: Optional[int] = None
    vpc_id: Optional[str] = None
    is_active: Optional[bool] = None
    total_cpu: Optional[int] = None
    total_memory_gb: Optional[float] = None
    pods_running: Optional[int] = None
    pods_pending: Optional[int] = None
    cluster_cpu_usage_pct: Optional[float] = None
    cluster_memory_usage_pct: Optional[float] = None


AnyNode = Annotated[
    Union[
        ServiceNode,
        EndpointNode,
        DeploymentNode,
        PodNode,
        ComputeNodeNode,
        DatabaseNode,
        TableNode,
        QueueTopicNode,
        CacheNode,
        ExternalAPINode,
        SecretConfigNode,
        LibraryNode,
        TeamOwnerNode,
        SLASLONode,
        RegionClusterNode,
    ],
    Field(discriminator="type"),
]
