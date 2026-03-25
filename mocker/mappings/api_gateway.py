API_GATEWAY_MAPPING = {
    "id": "api-gateway-mapper-v1",
    "name": "API Gateway Mapper v1.0",
    "source_type": "api-gateway",
    "version": "1.0.0",
    "description": "Maps API Gateway routes (K8s Ingress) to Endpoint nodes",
    "edge_preset_id": "default",
    "field_mappings": [
        {
            "id": "endpoint-id",
            "source_path": "spec.rules[0].http.paths[0].path",
            "target_field": "id",
            "target_node_type": "Endpoint",
            "transform_type": "template",
            "transform_config": {"template": "urn:endpoint:{value}"},
        },
        {
            "id": "endpoint-path",
            "source_path": "spec.rules[0].http.paths[0].path",
            "target_field": "path",
            "target_node_type": "Endpoint",
        },
        {
            "id": "endpoint-name",
            "source_path": "spec.rules[0].http.paths[0].path",
            "target_field": "name",
            "target_node_type": "Endpoint",
        },
        {
            "id": "endpoint-service",
            "source_path": "spec.rules[0].http.paths[0].backend.service.name",
            "target_field": "service_name",
            "target_node_type": "Endpoint",
            "description": "For ownedby edge to Service",
        },
        {
            "id": "endpoint-port",
            "source_path": "spec.rules[0].http.paths[0].backend.service.port.number",
            "target_field": "port",
            "target_node_type": "Endpoint",
        },
        {
            "id": "endpoint-host",
            "source_path": "spec.rules[0].host",
            "target_field": "host",
            "target_node_type": "Endpoint",
        },
        {
            "id": "endpoint-tls",
            "source_path": "spec.tls[0].secretName",
            "target_field": "tls_secret",
            "target_node_type": "Endpoint",
        },
        {
            "id": "endpoint-namespace",
            "source_path": "metadata.namespace",
            "target_field": "namespace",
            "target_node_type": "Endpoint",
        },
    ],
    "conditional_rules": [
        {
            "id": "cr-endpoint",
            "condition": "kind == 'Ingress'",
            "target_node_type": "Endpoint",
            "priority": 10,
        },
    ],
}
