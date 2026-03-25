ISTIO_METRICS_MAPPING = {
    "id": "istio-metrics-mapper-v1",
    "name": "Istio Metrics Mapper v1.0",
    "source_type": "istio-metrics",
    "version": "1.0.0",
    "description": "Maps Istio metrics to Service nodes with call relationships",
    "edge_preset_id": "default",
    "field_mappings": [
        {
            "id": "src-svc-id",
            "source_path": "metric_samples[0].labels.source_workload",
            "target_field": "id",
            "target_node_type": "Service",
            "transform_type": "template",
            "transform_config": {"template": "urn:service:{value}"},
        },
        {
            "id": "src-svc-name",
            "source_path": "metric_samples[0].labels.source_workload",
            "target_field": "name",
            "target_node_type": "Service",
        },
        {
            "id": "src-svc-namespace",
            "source_path": "metric_samples[0].labels.source_namespace",
            "target_field": "namespace",
            "target_node_type": "Service",
        },
        {
            "id": "src-svc-calls",
            "source_path": "metric_samples[0].labels.destination_workload",
            "target_field": "calls_services",
            "target_node_type": "Service",
            "description": "For calls edge to destination Service",
        },
        {
            "id": "svc-requests",
            "source_path": "metric_samples[?name=='istio_requests_total'].value | [0]",
            "target_field": "istio_requests_total",
            "target_node_type": "Service",
        },
        {
            "id": "svc-latency",
            "source_path": "metric_samples[?name=='istio_request_duration_milliseconds'].value | [0]",
            "target_field": "istio_latency_ms",
            "target_node_type": "Service",
        },
    ],
    "conditional_rules": [
        {
            "id": "cr-service",
            "condition": "metric_samples[0].labels.source_workload != `null`",
            "target_node_type": "Service",
            "priority": 10,
        },
    ],
}
