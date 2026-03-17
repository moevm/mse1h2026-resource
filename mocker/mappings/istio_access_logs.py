"""
Mapping configuration for istio-access-logs source type.

Maps Istio access logs to Service and ExternalAPI nodes.
"""

ISTIO_ACCESS_LOGS_MAPPING = {
    "id": "istio-logs-mapper-v1",
    "name": "Istio Access Logs Mapper v1.0",
    "source_type": "istio-access-logs",
    "version": "1.0.0",
    "description": "Maps Istio access logs to Service/ExternalAPI nodes with call relationships",
    "edge_preset_id": "default",
    "field_mappings": [
        # === SERVICE (source) ===
        {
            "id": "src-svc-id",
            "source_path": "source.workload",
            "target_field": "id",
            "target_node_type": "Service",
            "transform_type": "template",
            "transform_config": {"template": "urn:service:{value}"},
        },
        {
            "id": "src-svc-name",
            "source_path": "source.workload",
            "target_field": "name",
            "target_node_type": "Service",
        },
        {
            "id": "src-svc-namespace",
            "source_path": "source.namespace",
            "target_field": "namespace",
            "target_node_type": "Service",
        },
        # Destination as calls_services (for internal calls)
        {
            "id": "src-svc-calls",
            "source_path": "destination.workload",
            "target_field": "calls_services",
            "target_node_type": "Service",
            "description": "For calls edge to another Service",
        },
        # === External API ===
        {
            "id": "extapi-id",
            "source_path": "external_api_name",
            "target_field": "id",
            "target_node_type": "ExternalAPI",
            "transform_type": "template",
            "transform_config": {"template": "urn:externalapi:{value}"},
        },
        {
            "id": "extapi-name",
            "source_path": "external_api_name",
            "target_field": "name",
            "target_node_type": "ExternalAPI",
        },
        # Link service to external API
        {
            "id": "src-svc-external",
            "source_path": "external_api_name",
            "target_field": "external_apis",
            "target_node_type": "Service",
            "description": "For calls edge to ExternalAPI",
        },
        # === ENDPOINT (optional) ===
        {
            "id": "endpoint-id",
            "source_path": "path",
            "target_field": "id",
            "target_node_type": "Endpoint",
            "transform_type": "template",
            "transform_config": {"template": "urn:endpoint:{value}"},
        },
        {
            "id": "endpoint-path",
            "source_path": "path",
            "target_field": "path",
            "target_node_type": "Endpoint",
        },
        {
            "id": "endpoint-method",
            "source_path": "method",
            "target_field": "methods",
            "target_node_type": "Endpoint",
        },
    ],
    "conditional_rules": [
        {
            "id": "cr-external-api",
            "condition": "is_external_call == `true`",
            "target_node_type": "ExternalAPI",
            "priority": 30,
        },
        {
            "id": "cr-service",
            "condition": "source.workload != `null`",
            "target_node_type": "Service",
            "priority": 10,
        },
    ],
}
