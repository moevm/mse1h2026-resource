"""
Mapping configuration for prometheus source type.

Maps Prometheus metrics to Service nodes.
"""

PROMETHEUS_MAPPING = {
    "id": "prometheus-mapper-v1",
    "name": "Prometheus Mapper v1.0",
    "source_type": "prometheus",
    "version": "1.0.0",
    "description": "Maps Prometheus metrics to Service nodes",
    "edge_preset_id": "default",
    "field_mappings": [
        # === SERVICE ===
        {
            "id": "svc-id",
            "source_path": "labels.service",
            "target_field": "id",
            "target_node_type": "Service",
            "transform_type": "template",
            "transform_config": {"template": "urn:service:{value}"},
        },
        {
            "id": "svc-name",
            "source_path": "labels.service",
            "target_field": "name",
            "target_node_type": "Service",
        },
        {
            "id": "svc-namespace",
            "source_path": "labels.namespace",
            "target_field": "namespace",
            "target_node_type": "Service",
        },
        {
            "id": "svc-job",
            "source_path": "labels.job",
            "target_field": "job",
            "target_node_type": "Service",
        },
        {
            "id": "svc-instance",
            "source_path": "labels.instance",
            "target_field": "instance",
            "target_node_type": "Service",
        },
        # Metrics
        {
            "id": "svc-cpu",
            "source_path": "metrics.process_cpu_seconds_total",
            "target_field": "cpu_seconds_total",
            "target_node_type": "Service",
        },
        {
            "id": "svc-memory",
            "source_path": "metrics.process_resident_memory_bytes",
            "target_field": "memory_bytes",
            "target_node_type": "Service",
        },
        {
            "id": "svc-http-requests",
            "source_path": "metrics.http_requests_total",
            "target_field": "http_requests_total",
            "target_node_type": "Service",
        },
    ],
    "conditional_rules": [
        {
            "id": "cr-service",
            "condition": "labels.service != `null`",
            "target_node_type": "Service",
            "priority": 10,
        },
    ],
}
