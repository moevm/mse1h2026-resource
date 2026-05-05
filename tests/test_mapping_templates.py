from __future__ import annotations

from datetime import datetime, timezone
import sys
import types

from app.models.mapper.raw_data import RawDataChunk
from app.repositories.mapping_template_repo import mapping_template_repo
from app.services.mapper_service import mapper_service


def _chunk(data: dict, chunk_id: str) -> RawDataChunk:
    return RawDataChunk(
        id=chunk_id,
        agent_id="agent-1",
        timestamp=datetime.now(timezone.utc),
        data=data,
    )


def _install_fake_neo4j_module(nodes: list[dict] | None = None):
    fake_module = types.ModuleType("app.repositories.neo4j_repo")

    def fake_find_node_by_field(target_type: str, target_field: str, value: str):
        for node in nodes or []:
            if node.get("type") != target_type:
                continue
            if str(node.get(target_field)) == str(value):
                return node
        return None

    fake_module.find_node_by_field = fake_find_node_by_field
    sys.modules["app.repositories.neo4j_repo"] = fake_module


def _map_payloads(mapping_id: str, payloads: list[dict]):
    mapping = mapping_template_repo.get(mapping_id)
    assert mapping is not None

    nodes = []
    _install_fake_neo4j_module(nodes)
    for idx, payload in enumerate(payloads, start=1):
        mapped_nodes, _, _ = mapper_service.map_chunk(_chunk(payload, f"chunk-{idx}"), mapping)
        nodes.extend(mapped_nodes)
    return mapping, nodes


def _edge_tuples(nodes: list[dict], mapping, monkeypatch):
    _install_fake_neo4j_module(nodes)
    edges, unresolved = mapper_service.recreate_edges_for_nodes(nodes, mapping)
    return {(edge["source_id"], edge["target_id"], edge["type"]) for edge in edges}, unresolved


def test_kubernetes_template_builds_connected_topology(monkeypatch):
    payloads = [
        {
            "metadata": {
                "name": "worker-1",
                "labels": {
                    "topology.kubernetes.io/zone": "zone-a",
                    "topology.kubernetes.io/region": "region-a",
                    "node.kubernetes.io/instance-type": "vm-standard",
                },
            },
            "status": {
                "capacity": {"cpu": "4"},
                "node_info": {
                    "kubelet_version": "v1.30.0",
                    "os_image": "Ubuntu",
                    "architecture": "amd64",
                },
            },
        },
        {
            "metadata": {"name": "fastapi-app", "namespace": "monitoring-demo"},
            "spec": {
                "ports": [{"port": 8000}],
                "cluster_ip": "10.0.0.10",
                "selector": {"app": "fastapi-app"},
            },
        },
        {
            "metadata": {"name": "postgres-db", "namespace": "monitoring-demo"},
            "spec": {
                "ports": [{"port": 5432}],
                "cluster_ip": "10.0.0.20",
                "selector": {"app": "postgres-db"},
            },
        },
        {
            "metadata": {
                "name": "fastapi-app",
                "namespace": "monitoring-demo",
            },
            "spec": {
                "replicas": 1,
                "selector": {"match_labels": {"app": "fastapi-app"}},
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "image": "rectid/general:fastapi-app",
                                "env": [
                                    {
                                        "value_from": {
                                            "secret_key_ref": {"name": "postgres-credentials"}
                                        }
                                    }
                                ],
                            }
                        ]
                    }
                },
            },
            "status": {"ready_replicas": 1},
        },
        {
            "metadata": {
                "name": "postgres-db",
                "namespace": "monitoring-demo",
            },
            "spec": {
                "replicas": 1,
                "selector": {"match_labels": {"app": "postgres-db"}},
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "image": "postgres:16-alpine",
                            }
                        ]
                    }
                },
            },
            "status": {"ready_replicas": 1},
        },
        {
            "metadata": {
                "name": "fastapi-app-abc",
                "namespace": "monitoring-demo",
                "labels": {"app": "fastapi-app"},
            },
            "spec": {"node_name": "worker-1"},
            "status": {"phase": "Running", "pod_ip": "10.1.0.15"},
        },
        {
            "metadata": {"name": "postgres-credentials", "namespace": "monitoring-demo"},
            "type": "Opaque",
            "data": {},
        },
        {
            "metadata": {"name": "fastapi-app", "namespace": "monitoring-demo"},
            "subsets": [{"addresses": [{"ip": "10.1.0.15"}]}],
        },
        {
            "metadata": {"name": "postgres-init", "namespace": "monitoring-demo"},
            "data": {
                "init_tables.sql": "CREATE TABLE IF NOT EXISTS Users (id int, name text, age int, PRIMARY KEY (id));"
            },
        },
        {
            "metadata": {"name": "pyrra-slos", "namespace": "monitoring-demo"},
            "data": {
                "fastapi-api-availability.yaml": "target: '95'\nwindow: 1w\nmetric: http_requests_total"
            },
        },
    ]

    mapping, nodes = _map_payloads("watcher-kubernetes-objects-v1", payloads)
    node_types = {node["type"] for node in nodes}

    assert {"Pod", "Node", "Service", "Deployment", "Database", "Table", "Endpoint", "SecretConfig", "SLASLO", "RegionCluster"} <= node_types

    edges, unresolved = _edge_tuples(nodes, mapping, monkeypatch)

    assert ("urn:pod:fastapi-app-abc", "urn:node:worker-1", "deployedon") in edges
    assert ("urn:pod:fastapi-app-abc", "urn:deployment:fastapi-app", "deployedon") in edges
    assert ("urn:service:fastapi-app", "urn:deployment:fastapi-app", "deployedon") in edges
    assert ("urn:deployment:fastapi-app", "urn:secretconfig:postgres-credentials", "authenticatesvia") in edges
    assert ("urn:database:postgres-db", "urn:service:fastapi-app", "ownedby") in edges
    assert ("urn:table:users", "urn:database:postgres-db", "ownedby") in edges
    assert ("urn:slaslo:fastapi-app-api", "urn:service:fastapi-app", "dependson") in edges
    assert not unresolved
