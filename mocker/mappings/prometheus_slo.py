"""
Mapping configuration for prometheus-slo source type.

Maps Prometheus SLO metrics to Service and SLASLO nodes.
"""

PROMETHEUS_SLO_MAPPING = {
    "id": "prometheus-slo-mapper-v1",
    "name": "Prometheus SLO Mapper v1.0",
    "source_type": "prometheus-slo",
    "version": "1.0.0",
    "description": "Maps Prometheus SLO metrics to SLASLO nodes",
    "edge_preset_id": "default",
    "field_mappings": [
        # === SLASLO ===
        {
            "id": "slo-id",
            "source_path": "slo_name",
            "target_field": "id",
            "target_node_type": "SLASLO",
            "transform_type": "template",
            "transform_config": {"template": "urn:slaslo:{value}"},
        },
        {
            "id": "slo-name",
            "source_path": "slo_name",
            "target_field": "name",
            "target_node_type": "SLASLO",
        },
        {
            "id": "slo-service",
            "source_path": "service",
            "target_field": "service_ref",
            "target_node_type": "SLASLO",
            "description": "For ownedby edge to Service",
        },
        {
            "id": "slo-metric",
            "source_path": "metric_name",
            "target_field": "metric_name",
            "target_node_type": "SLASLO",
        },
        {
            "id": "slo-target",
            "source_path": "target",
            "target_field": "target_percentage",
            "target_node_type": "SLASLO",
        },
        {
            "id": "slo-current",
            "source_path": "current",
            "target_field": "current_value",
            "target_node_type": "SLASLO",
        },
        {
            "id": "slo-budget",
            "source_path": "metrics.slo_error_budget_remaining",
            "target_field": "error_budget_remaining_pct",
            "target_node_type": "SLASLO",
        },
        {
            "id": "slo-burn-rate",
            "source_path": "metrics.slo_burn_rate",
            "target_field": "burn_rate",
            "target_node_type": "SLASLO",
        },
    ],
    "conditional_rules": [
        {
            "id": "cr-slo",
            "condition": "slo_name != `null`",
            "target_node_type": "SLASLO",
            "priority": 10,
        },
    ],
}
