OTLP_METRICS_MAPPING = {
    "id": "otel-metrics-mapper-v1",
    "name": "OpenTelemetry Metrics Mapper v1.0",
    "source_type": "opentelemetry-metrics",
    "version": "1.0.0",
    "description": "Maps OTLP metrics to Service nodes with runtime data",
    "edge_preset_id": "default",
    "field_mappings": [
        {
            "id": "svc-id",
            "source_path": "resourceMetrics[0].resource.attributes[?key=='service.name'].value.stringValue | [0]",
            "target_field": "id",
            "target_node_type": "Service",
            "transform_type": "template",
            "transform_config": {"template": "urn:service:{value}"},
        },
        {
            "id": "svc-name",
            "source_path": "resourceMetrics[0].resource.attributes[?key=='service.name'].value.stringValue | [0]",
            "target_field": "name",
            "target_node_type": "Service",
        },
        {
            "id": "svc-cpu",
            "source_path": "resourceMetrics[0].scopeMetrics[0].metrics[?name=='process_cpu_utilization'].gauge.dataPoints[0].asDouble | [0]",
            "target_field": "cpu_utilization",
            "target_node_type": "Service",
        },
        {
            "id": "svc-memory",
            "source_path": "resourceMetrics[0].scopeMetrics[0].metrics[?name=='process_memory_usage'].gauge.dataPoints[0].asInt | [0]",
            "target_field": "memory_bytes",
            "target_node_type": "Service",
        },
        {
            "id": "svc-http-requests",
            "source_path": "resourceMetrics[0].scopeMetrics[0].metrics[?name=='http_server_requests'].sum.dataPoints[0].asInt | [0]",
            "target_field": "http_requests_total",
            "target_node_type": "Service",
        },
    ],
    "conditional_rules": [
        {
            "id": "cr-service",
            "condition": "resourceMetrics[0].resource.attributes[?key=='service.name'] | [0] != `null`",
            "target_node_type": "Service",
            "priority": 10,
        },
    ],
}
