"""
Mapping configuration for argocd source type.

Maps ArgoCD Application manifests to Service and TeamOwner nodes.
"""

ARGOCD_MAPPING = {
    "id": "argocd-mapper-v1",
    "name": "ArgoCD Mapper v1.0",
    "source_type": "argocd",
    "version": "1.0.0",
    "description": "Maps ArgoCD Application manifests to Service/TeamOwner nodes",
    "edge_preset_id": "default",
    "field_mappings": [
        # === SERVICE ===
        {
            "id": "svc-id",
            "source_path": "metadata.name",
            "target_field": "id",
            "target_node_type": "Service",
            "transform_type": "template",
            "transform_config": {"template": "urn:service:{value}"},
        },
        {
            "id": "svc-name",
            "source_path": "metadata.name",
            "target_field": "name",
            "target_node_type": "Service",
        },
        {
            "id": "svc-namespace",
            "source_path": "spec.destination.namespace",
            "target_field": "namespace",
            "target_node_type": "Service",
        },
        {
            "id": "svc-team",
            "source_path": "metadata.labels.team",
            "target_field": "team",
            "target_node_type": "Service",
            "description": "For ownedby edge to TeamOwner",
        },
        {
            "id": "svc-health",
            "source_path": "status.health.status",
            "target_field": "health_status",
            "target_node_type": "Service",
        },
        {
            "id": "svc-sync",
            "source_path": "status.sync.status",
            "target_field": "sync_status",
            "target_node_type": "Service",
        },
        {
            "id": "svc-repo",
            "source_path": "spec.source.repoURL",
            "target_field": "repository_url",
            "target_node_type": "Service",
        },
        {
            "id": "svc-path",
            "source_path": "spec.source.path",
            "target_field": "deploy_path",
            "target_node_type": "Service",
        },
        {
            "id": "svc-revision",
            "source_path": "status.history[0].revision",
            "target_field": "commit_hash",
            "target_node_type": "Service",
        },
        # === TEAMOWNER ===
        {
            "id": "team-id",
            "source_path": "metadata.labels.team",
            "target_field": "id",
            "target_node_type": "TeamOwner",
            "transform_type": "template",
            "transform_config": {"template": "urn:teamowner:{value}"},
        },
        {
            "id": "team-name",
            "source_path": "metadata.labels.team",
            "target_field": "name",
            "target_node_type": "TeamOwner",
        },
    ],
    "conditional_rules": [
        {
            "id": "cr-team",
            "condition": "metadata.labels.team != `null`",
            "target_node_type": "TeamOwner",
            "priority": 20,
        },
        {
            "id": "cr-service",
            "condition": "kind == 'Application'",
            "target_node_type": "Service",
            "priority": 10,
        },
    ],
}
