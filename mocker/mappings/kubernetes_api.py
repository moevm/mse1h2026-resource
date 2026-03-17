"""
Mapping configuration for kubernetes-api source type.

Maps K8s Pod/Node/Service/Deployment manifests to graph nodes.
"""

KUBERNETES_API_MAPPING = {
    "id": "k8s-api-mapper-v1",
    "name": "Kubernetes API Mapper v1.0",
    "source_type": "kubernetes-api",
    "version": "1.0.0",
    "description": "Maps K8s Pod/Node/Service/Deployment manifests to graph nodes",
    "edge_preset_id": "default",
    "field_mappings": [
        # === POD ===
        {
            "id": "pod-id",
            "source_path": "metadata.name",
            "target_field": "id",
            "target_node_type": "Pod",
            "transform_type": "template",
            "transform_config": {"template": "urn:pod:{value}"},
        },
        {
            "id": "pod-name",
            "source_path": "metadata.name",
            "target_field": "name",
            "target_node_type": "Pod",
        },
        {
            "id": "pod-namespace",
            "source_path": "metadata.namespace",
            "target_field": "namespace",
            "target_node_type": "Pod",
        },
        {
            "id": "pod-node",
            "source_path": "spec.nodeName",
            "target_field": "node_name",
            "target_node_type": "Pod",
            "description": "For deployedon edge to Node",
        },
        {
            "id": "pod-deployment",
            "source_path": "metadata.labels.deployment",
            "target_field": "deployment_name",
            "target_node_type": "Pod",
            "description": "For deployedon edge to Deployment",
        },
        {
            "id": "pod-service",
            "source_path": "metadata.labels.app",
            "target_field": "service_name",
            "target_node_type": "Pod",
        },
        {
            "id": "pod-status",
            "source_path": "status.phase",
            "target_field": "status",
            "target_node_type": "Pod",
        },
        {
            "id": "pod-ip",
            "source_path": "status.podIP",
            "target_field": "ip_address",
            "target_node_type": "Pod",
        },
        # === NODE ===
        {
            "id": "node-id",
            "source_path": "metadata.name",
            "target_field": "id",
            "target_node_type": "Node",
            "transform_type": "template",
            "transform_config": {"template": "urn:node:{value}"},
        },
        {
            "id": "node-name",
            "source_path": "metadata.name",
            "target_field": "name",
            "target_node_type": "Node",
        },
        {
            "id": "node-zone",
            "source_path": "metadata.labels.'topology.kubernetes.io/zone'",
            "target_field": "zone",
            "target_node_type": "Node",
        },
        {
            "id": "node-instance-type",
            "source_path": "metadata.labels.'node.kubernetes.io/instance-type'",
            "target_field": "instance_type",
            "target_node_type": "Node",
        },
        {
            "id": "node-cpu",
            "source_path": "status.capacity.cpu",
            "target_field": "capacity_cpu",
            "target_node_type": "Node",
        },
        {
            "id": "node-memory",
            "source_path": "status.capacity.memory",
            "target_field": "capacity_memory",
            "target_node_type": "Node",
        },
        {
            "id": "node-kubelet",
            "source_path": "status.nodeInfo.kubeletVersion",
            "target_field": "kubelet_version",
            "target_node_type": "Node",
        },
        # === SERVICE (K8s Service) ===
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
            "source_path": "metadata.namespace",
            "target_field": "namespace",
            "target_node_type": "Service",
        },
        {
            "id": "svc-port",
            "source_path": "spec.ports[0].port",
            "target_field": "port",
            "target_node_type": "Service",
        },
        {
            "id": "svc-cluster-ip",
            "source_path": "spec.clusterIP",
            "target_field": "cluster_ip",
            "target_node_type": "Service",
        },
        # === DEPLOYMENT ===
        {
            "id": "deploy-id",
            "source_path": "metadata.name",
            "target_field": "id",
            "target_node_type": "Deployment",
            "transform_type": "template",
            "transform_config": {"template": "urn:deployment:{value}"},
        },
        {
            "id": "deploy-name",
            "source_path": "metadata.name",
            "target_field": "name",
            "target_node_type": "Deployment",
        },
        {
            "id": "deploy-namespace",
            "source_path": "metadata.namespace",
            "target_field": "namespace",
            "target_node_type": "Deployment",
        },
        {
            "id": "deploy-replicas",
            "source_path": "spec.replicas",
            "target_field": "replicas_desired",
            "target_node_type": "Deployment",
        },
        {
            "id": "deploy-ready",
            "source_path": "status.readyReplicas",
            "target_field": "replicas_ready",
            "target_node_type": "Deployment",
        },
        {
            "id": "deploy-team",
            "source_path": "metadata.annotations.team",
            "target_field": "team",
            "target_node_type": "Deployment",
            "description": "For ownedby edge to TeamOwner",
        },
    ],
    "conditional_rules": [
        {
            "id": "cr-pod",
            "condition": "kind == 'Pod'",
            "target_node_type": "Pod",
            "priority": 40,
        },
        {
            "id": "cr-node",
            "condition": "kind == 'Node'",
            "target_node_type": "Node",
            "priority": 30,
        },
        {
            "id": "cr-service",
            "condition": "kind == 'Service'",
            "target_node_type": "Service",
            "priority": 20,
        },
        {
            "id": "cr-deployment",
            "condition": "kind == 'Deployment'",
            "target_node_type": "Deployment",
            "priority": 10,
        },
    ],
}
