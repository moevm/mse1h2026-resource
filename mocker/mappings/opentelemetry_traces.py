"""
Mapping configuration for opentelemetry-traces source type.

Maps OTLP traces to Service, Database, Table, ExternalAPI, Library nodes.
"""

OTLP_TRACES_MAPPING = {
    "id": "otel-traces-mapper-v1",
    "name": "OpenTelemetry Traces Mapper v1.0",
    "source_type": "opentelemetry-traces",
    "version": "1.0.0",
    "description": "Maps OTLP traces to Service/Database/Table/ExternalAPI/Library nodes",
    "edge_preset_id": "default",
    "field_mappings": [
        # === SERVICE (source) ===
        {
            "id": "svc-id",
            "source_path": "resourceSpans[0].resource.attributes[?key=='service.name'].value.stringValue | [0]",
            "target_field": "id",
            "target_node_type": "Service",
            "transform_type": "template",
            "transform_config": {"template": "urn:service:{value}"},
        },
        {
            "id": "svc-name",
            "source_path": "resourceSpans[0].resource.attributes[?key=='service.name'].value.stringValue | [0]",
            "target_field": "name",
            "target_node_type": "Service",
        },
        {
            "id": "svc-peer",
            "source_path": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='peer.service'].value.stringValue | [0]",
            "target_field": "calls_services",
            "target_node_type": "Service",
            "description": "For calls edge to another Service",
        },
        {
            "id": "svc-version",
            "source_path": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='service.version'].value.stringValue | [0]",
            "target_field": "version",
            "target_node_type": "Service",
        },
        {
            "id": "svc-env",
            "source_path": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='deployment.environment'].value.stringValue | [0]",
            "target_field": "environment",
            "target_node_type": "Service",
        },
        # === External API ===
        {
            "id": "extapi-id",
            "source_path": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='external_api'].value.stringValue | [0]",
            "target_field": "id",
            "target_node_type": "ExternalAPI",
            "transform_type": "template",
            "transform_config": {"template": "urn:externalapi:{value}"},
        },
        {
            "id": "extapi-name",
            "source_path": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='external_api'].value.stringValue | [0]",
            "target_field": "name",
            "target_node_type": "ExternalAPI",
        },
        {
            "id": "svc-external-apis",
            "source_path": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='external_api'].value.stringValue | [0]",
            "target_field": "external_apis",
            "target_node_type": "Service",
            "description": "For calls edge to ExternalAPI",
        },
        # === DATABASE ===
        {
            "id": "db-id",
            "source_path": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='db.name'].value.stringValue | [0]",
            "target_field": "id",
            "target_node_type": "Database",
            "transform_type": "template",
            "transform_config": {"template": "urn:database:{value}"},
        },
        {
            "id": "db-name",
            "source_path": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='db.name'].value.stringValue | [0]",
            "target_field": "name",
            "target_node_type": "Database",
        },
        {
            "id": "db-system",
            "source_path": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='db.system'].value.stringValue | [0]",
            "target_field": "engine",
            "target_node_type": "Database",
        },
        {
            "id": "svc-reads-db",
            "source_path": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='db.name'].value.stringValue | [0]",
            "target_field": "reads_databases",
            "target_node_type": "Service",
            "description": "For reads edge to Database",
        },
        {
            "id": "svc-writes-db",
            "source_path": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='db.name'].value.stringValue | [0]",
            "target_field": "writes_databases",
            "target_node_type": "Service",
            "description": "For writes edge to Database",
        },
        # === TABLE ===
        {
            "id": "table-id",
            "source_path": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='db.table'].value.stringValue | [0]",
            "target_field": "id",
            "target_node_type": "Table",
            "transform_type": "template",
            "transform_config": {"template": "urn:table:{value}"},
        },
        {
            "id": "table-name",
            "source_path": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='db.table'].value.stringValue | [0]",
            "target_field": "name",
            "target_node_type": "Table",
        },
        {
            "id": "svc-reads-table",
            "source_path": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='db.table'].value.stringValue | [0]",
            "target_field": "reads_tables",
            "target_node_type": "Service",
        },
        {
            "id": "svc-writes-table",
            "source_path": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='db.table'].value.stringValue | [0]",
            "target_field": "writes_tables",
            "target_node_type": "Service",
        },
        # === LIBRARY ===
        {
            "id": "lib-id",
            "source_path": "resourceSpans[0].resource.attributes[?key=='telemetry.sdk.name'].value.stringValue | [0]",
            "target_field": "id",
            "target_node_type": "Library",
            "transform_type": "template",
            "transform_config": {"template": "urn:library:{value}"},
        },
        {
            "id": "lib-name",
            "source_path": "resourceSpans[0].resource.attributes[?key=='telemetry.sdk.name'].value.stringValue | [0]",
            "target_field": "name",
            "target_node_type": "Library",
        },
        {
            "id": "lib-language",
            "source_path": "resourceSpans[0].resource.attributes[?key=='telemetry.sdk.language'].value.stringValue | [0]",
            "target_field": "language",
            "target_node_type": "Library",
        },
        {
            "id": "svc-libraries",
            "source_path": "resourceSpans[0].resource.attributes[?key=='telemetry.sdk.name'].value.stringValue | [0]",
            "target_field": "libraries",
            "target_node_type": "Service",
            "description": "For dependson edge to Library",
        },
    ],
    "conditional_rules": [
        {
            "id": "cr-external-api",
            "condition": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='external_api'] | [0] != `null`",
            "target_node_type": "ExternalAPI",
            "priority": 50,
        },
        {
            "id": "cr-database",
            "condition": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='db.system'] | [0] != `null`",
            "target_node_type": "Database",
            "priority": 40,
        },
        {
            "id": "cr-table",
            "condition": "resourceSpans[0].scopeSpans[0].spans[0].attributes[?key=='db.table'] | [0] != `null`",
            "target_node_type": "Table",
            "priority": 35,
        },
        {
            "id": "cr-library",
            "condition": "resourceSpans[0].resource.attributes[?key=='telemetry.sdk.language'] | [0] != `null`",
            "target_node_type": "Library",
            "priority": 30,
        },
        {
            "id": "cr-service",
            "condition": "resourceSpans[0].resource.attributes[?key=='service.name'] | [0] != `null`",
            "target_node_type": "Service",
            "priority": 10,
        },
    ],
}
