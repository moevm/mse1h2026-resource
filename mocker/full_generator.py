from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from mocker.shared_state import SharedState


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ns() -> int:
    now = datetime.now(timezone.utc)
    return int(now.timestamp() * 1_000_000_000)


def _random_hex(length: int = 16) -> str:
    return ''.join(random.choices('0123456789abcdef', k=length))


def _random_trace_id() -> str:
    return _random_hex(32)


def _random_span_id() -> str:
    return _random_hex(16)


class FullGraphGenerator:
    def __init__(self, state: SharedState):
        self.state = state

    def generate_all(self) -> Dict[str, List[Dict[str, Any]]]:
        result = {
            "kubernetes-api": [],
            "opentelemetry-traces": [],
            "opentelemetry-metrics": [],
            "istio-access-logs": [],
            "istio-metrics": [],
            "prometheus": [],
            "prometheus-slo": [],
            "terraform-state": [],
            "argocd": [],
            "api-gateway": [],
        }

        result["kubernetes-api"].extend(self._generate_nodes())
        result["kubernetes-api"].append(self._generate_cluster())

        for service in self.state.services:
            result["kubernetes-api"].append(self._generate_deployment(service))
            result["kubernetes-api"].append(self._generate_service(service))

        result["kubernetes-api"].extend(self._generate_all_pods())

        for db in self.state.databases:
            result["terraform-state"].append(self._generate_database(db))
        for cache in self.state.caches:
            result["terraform-state"].append(self._generate_cache(cache))
        for queue in self.state.queues:
            result["terraform-state"].append(self._generate_queue(queue))
        for table in self.state.tables:
            result["terraform-state"].append(self._generate_table(table))

        for secret in self.state.secrets:
            result["terraform-state"].append(self._generate_secret(secret))

        for source, target in self.state.service_calls:
            result["opentelemetry-traces"].append(self._generate_service_call_trace(source, target))

        for db in self.state.databases:
            owner = db["owner"]
            result["opentelemetry-traces"].append(self._generate_db_trace(owner, db))

        for cache in self.state.caches:
            owner = cache["owner"]
            result["opentelemetry-traces"].append(self._generate_cache_trace(owner, cache))

        for queue in self.state.queues:
            for publisher in queue["publishers"]:
                result["opentelemetry-traces"].append(self._generate_publish_trace(publisher, queue))
            for consumer in queue["consumers"]:
                result["opentelemetry-traces"].append(self._generate_consume_trace(consumer, queue))

        for ext_api in self.state.external_apis:
            owner = ext_api["owner"]
            result["opentelemetry-traces"].append(self._generate_external_api_trace(owner, ext_api))

        for slo in self.state.slo_configs:
            result["prometheus-slo"].append(self._generate_slo(slo))

        for endpoint in self.state.endpoints:
            result["api-gateway"].append(self._generate_endpoint(endpoint))

        for service in self.state.services:
            result["argocd"].append(self._generate_argocd_app(service))

        for source, target in self.state.service_calls:
            result["istio-access-logs"].append(self._generate_istio_log(source, target))

        for service in self.state.services:
            result["prometheus"].append(self._generate_prometheus_metrics(service))

        for service in self.state.services:
            result["opentelemetry-metrics"].append(self._generate_otel_metrics(service))

        for source, target in self.state.service_calls:
            result["istio-metrics"].append(self._generate_istio_metrics(source, target))

        return result


    def _generate_nodes(self) -> List[Dict[str, Any]]:
        nodes = []
        for node_info in self.state.nodes:
            nodes.append({
                "apiVersion": "v1",
                "kind": "Node",
                "metadata": {
                    "name": node_info["name"],
                    "uid": f"node-{node_info['name']}-{_random_hex(8)}",
                    "labels": {
                        "kubernetes.io/arch": "amd64",
                        "kubernetes.io/os": "linux",
                        "node-role.kubernetes.io/worker": "true",
                        "topology.kubernetes.io/zone": node_info["zone"],
                        "node.kubernetes.io/instance-type": node_info["instance_type"],
                    },
                },
                "spec": {
                    "podCIDR": f"10.{random.randint(200, 255)}.0.0/24",
                    "providerID": f"aws:///{node_info['zone']}/i-{_random_hex(17)}",
                },
                "status": {
                    "capacity": {
                        "cpu": node_info["capacity_cpu"],
                        "memory": node_info["capacity_memory"],
                        "pods": "110",
                    },
                    "allocatable": {
                        "cpu": f"{int(node_info['capacity_cpu']) * 1000 - 500}m",
                        "memory": f"{int(node_info['capacity_memory'].replace('Gi', '')) - 4}Gi",
                        "pods": "100",
                    },
                    "conditions": [
                        {"type": "Ready", "status": "True"},
                        {"type": "MemoryPressure", "status": "False"},
                        {"type": "DiskPressure", "status": "False"},
                    ],
                    "nodeInfo": {
                        "kubeletVersion": "v1.28.4",
                        "osImage": "Ubuntu 22.04.3 LTS",
                        "containerRuntime": "containerd://1.7.2",
                    },
                },
            })
        return nodes

    def _generate_cluster(self) -> Dict[str, Any]:
        return {
            "apiVersion": "cluster.k8s.io/v1alpha1",
            "kind": "Cluster",
            "metadata": {
                "name": self.state.cluster["name"],
                "uid": f"cluster-{self.state.cluster['name']}-{_random_hex(8)}",
                "labels": {
                    "region": self.state.cluster["region"],
                    "provider": self.state.cluster["provider"],
                },
            },
            "spec": {
                "region": self.state.cluster["region"],
                "provider": self.state.cluster["provider"],
                "cluster_id": self.state.cluster["name"],
            },
        }

    def _generate_deployment(self, service_name: str) -> Dict[str, Any]:
        team = self.state.get_team_for_service(service_name)
        replicas = random.randint(2, 4)
        uid = str(uuid.uuid4())

        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": service_name,
                "namespace": "production",
                "uid": uid,
                "labels": {"app": service_name, "cluster": self.state.cluster["name"]},
                "annotations": {
                    "deployment.kubernetes.io/revision": "1",
                    "team": team,
                },
            },
            "spec": {
                "replicas": replicas,
                "selector": {"matchLabels": {"app": service_name}},
                "template": {
                    "metadata": {"labels": {"app": service_name}},
                    "spec": {
                        "containers": [{
                            "name": service_name,
                            "image": f"myregistry.io/{service_name}:latest",
                        }]
                    },
                },
            },
            "status": {
                "replicas": replicas,
                "readyReplicas": replicas,
                "availableReplicas": replicas,
                "conditions": [
                    {"type": "Progressing", "status": "True"},
                    {"type": "Available", "status": "True"},
                ],
            },
        }

    def _generate_service(self, service_name: str) -> Dict[str, Any]:
        uid = str(uuid.uuid4())
        port = random.choice([80, 443, 8080, 9090])

        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": service_name,
                "namespace": "production",
                "uid": uid,
                "labels": {"app": service_name},
            },
            "spec": {
                "type": "ClusterIP",
                "selector": {"app": service_name},
                "ports": [{
                    "port": port,
                    "targetPort": 8080,
                    "protocol": "TCP",
                    "name": "http",
                }],
                "clusterIP": f"10.{random.randint(96, 111)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
            },
            "status": {
                "loadBalancer": {},
            },
        }

    def _generate_all_pods(self) -> List[Dict[str, Any]]:
        pods = []
        for pod_info in self.state.pods:
            uid = str(uuid.uuid4())
            pods.append({
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": pod_info["name"],
                    "namespace": pod_info["namespace"],
                    "uid": uid,
                    "labels": {
                        "app": pod_info["service"],
                        "deployment": pod_info["deployment"],
                    },
                    "annotations": {
                        "prometheus.io/scrape": "true",
                        "prometheus.io/port": "9090",
                    },
                    "creationTimestamp": _now(),
                },
                "spec": {
                    "nodeName": pod_info["node"],
                    "serviceAccountName": "default",
                    "containers": [{
                        "name": pod_info["service"],
                        "image": f"myregistry.io/{pod_info['service']}:v{random.randint(1, 10)}.{random.randint(0, 99)}",
                        "ports": [{"containerPort": 8080, "protocol": "TCP"}],
                        "resources": {
                            "requests": {"cpu": "100m", "memory": "256Mi"},
                            "limits": {"cpu": "500m", "memory": "512Mi"},
                        },
                    }],
                },
                "status": {
                    "phase": "Running",
                    "podIP": f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
                    "hostIP": f"192.168.{random.randint(1, 10)}.{random.randint(1, 254)}",
                    "conditions": [
                        {"type": "Ready", "status": "True"},
                        {"type": "ContainersReady", "status": "True"},
                    ],
                },
            })
        return pods


    def _generate_database(self, db: Dict[str, Any]) -> Dict[str, Any]:
        team = self.state.get_team_for_service(db["owner"])
        return {
            "module": "module.database",
            "mode": "managed",
            "type": "aws_db_instance",
            "name": db["name"].replace("-", "_").replace(" ", "_").lower(),
            "instances": [{
                "attributes": {
                    "identifier": db["name"].replace(" ", "-").lower(),
                    "engine": db["type"].replace("postgresql", "postgres"),
                    "engine_version": db.get("engine_version", "14.7"),
                    "instance_class": random.choice(["db.t3.micro", "db.t3.small", "db.r5.large"]),
                    "allocated_storage": random.randint(20, 500),
                    "database_name": db["name"].replace(" ", "_").lower(),
                    "tags": {
                        "Environment": "production",
                        "Service": db["owner"],
                        "Team": team,
                        "DisplayName": db["name"],
                    },
                },
            }],
            "owner_service": db["owner"],
            "team": team,
        }

    def _generate_cache(self, cache: Dict[str, Any]) -> Dict[str, Any]:
        team = self.state.get_team_for_service(cache["owner"])
        return {
            "module": "module.cache",
            "mode": "managed",
            "type": "aws_elasticache_cluster",
            "name": cache["name"].replace("-", "_").replace(" ", "_").lower(),
            "instances": [{
                "attributes": {
                    "cluster_id": cache["name"].replace(" ", "-").lower(),
                    "engine": "redis",
                    "engine_version": "7.0",
                    "node_type": random.choice(["cache.t3.micro", "cache.t3.small"]),
                    "num_cache_nodes": cache["cluster_size"],
                    "tags": {
                        "Environment": "production",
                        "Service": cache["owner"],
                        "Team": team,
                        "DisplayName": cache["name"],
                    },
                },
            }],
            "owner_service": cache["owner"],
            "team": team,
        }

    def _generate_queue(self, queue: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "module": "module.messaging",
            "mode": "managed",
            "type": "aws_msk_topic",
            "name": queue["name"].replace("-", "_").replace(".", "_"),
            "instances": [{
                "attributes": {
                    "name": queue["name"],
                    "partitions": queue["partitions"],
                    "replication_factor": 3,
                    "tags": {
                        "Environment": "production",
                        "DisplayName": queue["name"],
                    },
                },
            }],
            "publishers": queue["publishers"],
            "consumers": queue["consumers"],
        }

    def _generate_table(self, table: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "table",
            "name": table["name"],
            "schema_name": "public",
            "database_name": table["database"],
            "owner_service": table["owner"],
            "database_ref": table["database"],
            "row_count": random.randint(100_000, 10_000_000),
            "is_partitioned": random.random() > 0.7,
        }

    def _generate_secret(self, secret: Dict[str, Any]) -> Dict[str, Any]:
        secret_display_names = {
            "jwt-signing-key": "JWT Signing Key",
            "stripe-api-key": "Stripe API Key",
            "sendgrid-api-key": "SendGrid API Key",
            "db-credentials": "Database Credentials",
            "kafka-credentials": "Kafka SASL Credentials",
            "feature-flags": "Feature Flags",
        }
        display_name = secret_display_names.get(secret["name"], secret["name"])
        return {
            "module": "module.secrets",
            "mode": "managed",
            "type": "aws_secretsmanager_secret",
            "name": secret["name"].replace("-", "_"),
            "instances": [{
                "attributes": {
                    "name": display_name,
                    "description": f"Secret for {', '.join(secret['services'])}",
                    "tags": {
                        "Environment": "production",
                        "Provider": secret["provider"],
                    },
                },
            }],
            "services": secret["services"],
        }


    def _generate_service_call_trace(self, source: str, target: str) -> Dict[str, Any]:
        team = self.state.get_team_for_service(source)
        libraries = self.state.get_libraries_for_service(source)
        library_name = libraries[0] if libraries else "fastapi"

        lib_lang_map = {
            "fastapi": "python", "SQLAlchemy": "python", "Pydantic": "python",
            "Express.js": "javascript", "gRPC (Go)": "go", "kafka-go": "go",
            "Spring Boot": "java",
        }
        library_language = lib_lang_map.get(library_name, "python")

        trace_id = _random_trace_id()
        span_id = _random_span_id()
        start_time = _now_ns() - random.randint(1_000_000, 100_000_000)
        end_time = start_time + random.randint(1_000_000, 50_000_000)

        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": source}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": library_name}},
                    ],
                },
                "scopeSpans": [{
                    "scope": {"name": source},
                    "spans": [{
                        "traceId": trace_id,
                        "spanId": span_id,
                        "name": f"{source} -> {target}",
                        "kind": 2,
                        "startTimeUnixNano": start_time,
                        "endTimeUnixNano": end_time,
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": source}},
                            {"key": "service.version", "value": {"stringValue": f"v{random.randint(1, 10)}.{random.randint(0, 99)}"}},
                            {"key": "deployment.environment", "value": {"stringValue": "production"}},
                            {"key": "telemetry.sdk.name", "value": {"stringValue": library_name}},
                            {"key": "telemetry.sdk.language", "value": {"stringValue": library_language}},
                            {"key": "peer.service", "value": {"stringValue": target}},
                            {"key": "http.method", "value": {"stringValue": random.choice(["GET", "POST", "PUT", "DELETE"])}},
                            {"key": "http.status_code", "value": {"intValue": 200}},
                            {"key": "team", "value": {"stringValue": team}},
                        ],
                        "status": {"code": 1},
                    }],
                }],
            }],
        }

    def _generate_db_trace(self, service: str, db: Dict[str, Any]) -> Dict[str, Any]:
        team = self.state.get_team_for_service(service)
        libraries = self.state.get_libraries_for_service(service)
        library_name = libraries[0] if libraries else "fastapi"

        tables = self.state.get_tables_for_service(service)
        table_name = tables[0]["name"] if tables else "unknown_table"

        trace_id = _random_trace_id()
        span_id = _random_span_id()
        start_time = _now_ns() - random.randint(1_000_000, 100_000_000)
        end_time = start_time + random.randint(1_000_000, 50_000_000)

        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": service}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": library_name}},
                    ],
                },
                "scopeSpans": [{
                    "scope": {"name": service},
                    "spans": [{
                        "traceId": trace_id,
                        "spanId": span_id,
                        "name": f"{service} -> {db['name']}",
                        "kind": 2,
                        "startTimeUnixNano": start_time,
                        "endTimeUnixNano": end_time,
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": service}},
                            {"key": "db.system", "value": {"stringValue": db["type"]}},
                            {"key": "db.name", "value": {"stringValue": db["name"]}},
                            {"key": "db.table", "value": {"stringValue": table_name}},
                            {"key": "team", "value": {"stringValue": team}},
                        ],
                        "status": {"code": 1},
                    }],
                }],
            }],
        }

    def _generate_cache_trace(self, service: str, cache: Dict[str, Any]) -> Dict[str, Any]:
        team = self.state.get_team_for_service(service)
        libraries = self.state.get_libraries_for_service(service)
        library_name = libraries[0] if libraries else "fastapi"

        trace_id = _random_trace_id()
        span_id = _random_span_id()
        start_time = _now_ns() - random.randint(1_000_000, 100_000_000)
        end_time = start_time + random.randint(100_000, 10_000_000)

        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": service}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": library_name}},
                    ],
                },
                "scopeSpans": [{
                    "scope": {"name": service},
                    "spans": [{
                        "traceId": trace_id,
                        "spanId": span_id,
                        "name": f"{service} -> {cache['name']}",
                        "kind": 2,
                        "startTimeUnixNano": start_time,
                        "endTimeUnixNano": end_time,
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": service}},
                            {"key": "cache.name", "value": {"stringValue": cache["name"]}},
                            {"key": "team", "value": {"stringValue": team}},
                        ],
                        "status": {"code": 1},
                    }],
                }],
            }],
        }

    def _generate_publish_trace(self, service: str, queue: Dict[str, Any]) -> Dict[str, Any]:
        team = self.state.get_team_for_service(service)
        libraries = self.state.get_libraries_for_service(service)
        library_name = libraries[0] if libraries else "kafka-go"

        trace_id = _random_trace_id()
        span_id = _random_span_id()
        start_time = _now_ns() - random.randint(1_000_000, 100_000_000)
        end_time = start_time + random.randint(100_000, 10_000_000)

        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": service}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": library_name}},
                    ],
                },
                "scopeSpans": [{
                    "scope": {"name": service},
                    "spans": [{
                        "traceId": trace_id,
                        "spanId": span_id,
                        "name": f"{service} -> {queue['name']}",
                        "kind": 2,
                        "startTimeUnixNano": start_time,
                        "endTimeUnixNano": end_time,
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": service}},
                            {"key": "messaging.publishes_to", "value": {"stringValue": queue["name"]}},
                            {"key": "messaging.destination", "value": {"stringValue": queue["name"]}},
                            {"key": "team", "value": {"stringValue": team}},
                        ],
                        "status": {"code": 1},
                    }],
                }],
            }],
        }

    def _generate_consume_trace(self, service: str, queue: Dict[str, Any]) -> Dict[str, Any]:
        team = self.state.get_team_for_service(service)
        libraries = self.state.get_libraries_for_service(service)
        library_name = libraries[0] if libraries else "kafka-go"

        trace_id = _random_trace_id()
        span_id = _random_span_id()
        start_time = _now_ns() - random.randint(1_000_000, 100_000_000)
        end_time = start_time + random.randint(100_000, 10_000_000)

        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": service}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": library_name}},
                    ],
                },
                "scopeSpans": [{
                    "scope": {"name": service},
                    "spans": [{
                        "traceId": trace_id,
                        "spanId": span_id,
                        "name": f"{service} <- {queue['name']}",
                        "kind": 2,
                        "startTimeUnixNano": start_time,
                        "endTimeUnixNano": end_time,
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": service}},
                            {"key": "messaging.consumes_from", "value": {"stringValue": queue["name"]}},
                            {"key": "messaging.destination", "value": {"stringValue": queue["name"]}},
                            {"key": "team", "value": {"stringValue": team}},
                        ],
                        "status": {"code": 1},
                    }],
                }],
            }],
        }

    def _generate_external_api_trace(self, service: str, ext_api: Dict[str, Any]) -> Dict[str, Any]:
        team = self.state.get_team_for_service(service)
        libraries = self.state.get_libraries_for_service(service)
        library_name = libraries[0] if libraries else "fastapi"

        trace_id = _random_trace_id()
        span_id = _random_span_id()
        start_time = _now_ns() - random.randint(1_000_000, 100_000_000)
        end_time = start_time + random.randint(1_000_000, 50_000_000)

        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": service}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": library_name}},
                    ],
                },
                "scopeSpans": [{
                    "scope": {"name": service},
                    "spans": [{
                        "traceId": trace_id,
                        "spanId": span_id,
                        "name": f"{service} -> {ext_api['name']}",
                        "kind": 2,
                        "startTimeUnixNano": start_time,
                        "endTimeUnixNano": end_time,
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": service}},
                            {"key": "external_api", "value": {"stringValue": ext_api["name"]}},
                            {"key": "http.method", "value": {"stringValue": "POST"}},
                            {"key": "http.status_code", "value": {"intValue": 200}},
                            {"key": "team", "value": {"stringValue": team}},
                        ],
                        "status": {"code": 1},
                    }],
                }],
            }],
        }


    def _generate_slo(self, slo: Dict[str, Any]) -> Dict[str, Any]:
        service_name = slo["service"]
        current = slo["target"] * random.uniform(0.95, 1.05)

        return {
            "type": "slo-metric",
            "name": f"slo_{service_name}_{slo['metric'].replace('-', '_')}",
            "slo_name": slo["name"],
            "service": service_name,
            "metric_name": slo["metric"],
            "target": slo["target"],
            "current": round(current, 4),
            "metrics": {
                "slo_target": slo["target"],
                "slo_current": current,
                "slo_error_budget_remaining": random.uniform(50, 100),
                "slo_burn_rate": random.uniform(0.1, 2.0),
            },
            "labels": {
                "slo": slo["name"],
                "service": service_name,
                "metric": slo["metric"],
            },
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
        }

    def _generate_prometheus_metrics(self, service: str) -> Dict[str, Any]:
        team = self.state.get_team_for_service(service)
        return {
            "metrics": {
                "process_cpu_seconds_total": random.uniform(100, 10000),
                "process_open_fds": random.randint(10, 100),
                "process_resident_memory_bytes": random.randint(50_000_000, 500_000_000),
                "http_requests_total": random.randint(10000, 1000000),
                "http_request_duration_seconds_sum": random.uniform(10, 1000),
                "http_request_duration_seconds_count": random.randint(1000, 100000),
            },
            "labels": {
                "job": service,
                "instance": f"{service}-0:9090",
                "namespace": "production",
                "service": service,
                "team": team,
            },
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
        }

    def _generate_otel_metrics(self, service: str) -> Dict[str, Any]:
        base_time = _now_ns()
        return {
            "resourceMetrics": [{
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": service}}],
                },
                "scopeMetrics": [{
                    "scope": {"name": service},
                    "metrics": [
                        {
                            "name": "process_cpu_utilization",
                            "gauge": {
                                "dataPoints": [{
                                    "attributes": [{"key": "service.name", "value": {"stringValue": service}}],
                                    "timeUnixNano": base_time,
                                    "asDouble": random.uniform(0.1, 0.9),
                                }],
                            },
                        },
                        {
                            "name": "process_memory_usage",
                            "gauge": {
                                "dataPoints": [{
                                    "attributes": [{"key": "service.name", "value": {"stringValue": service}}],
                                    "timeUnixNano": base_time,
                                    "asInt": random.randint(100_000_000, 1_000_000_000),
                                }],
                            },
                        },
                    ],
                }],
            }],
        }


    def _generate_endpoint(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        service_name = endpoint["service"]
        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": f"{service_name}-ingress",
                "namespace": "production",
                "annotations": {
                    "kubernetes.io/ingress.class": "nginx",
                    "cert-manager.io/cluster-issuer": "letsencrypt-prod",
                },
            },
            "spec": {
                "rules": [{
                    "host": "api.example.com",
                    "http": {
                        "paths": [{
                            "path": endpoint["path"],
                            "pathType": "Prefix",
                            "backend": {
                                "service": {
                                    "name": service_name,
                                    "port": {"number": 8080},
                                },
                            },
                        }],
                    },
                }],
                "tls": [{
                    "hosts": ["api.example.com"],
                    "secretName": f"{service_name}-tls",
                }],
            },
        }


    def _generate_argocd_app(self, service: str) -> Dict[str, Any]:
        team = self.state.get_team_for_service(service)
        libraries = self.state.get_libraries_for_service(service)
        library = libraries[0] if libraries else None

        return {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Application",
            "metadata": {
                "name": service,
                "namespace": "argocd",
                "labels": {
                    "team": team,
                    "service": service,
                },
            },
            "spec": {
                "project": "default",
                "source": {
                    "repoURL": "https://gitlab.example.com/platform/services.git",
                    "targetRevision": "main",
                    "path": f"deploy/{service}",
                },
                "destination": {
                    "server": "https://kubernetes.default.svc",
                    "namespace": "production",
                },
                "syncPolicy": {
                    "automated": {"prune": True, "selfHeal": True},
                },
            },
            "status": {
                "health": {"status": "Healthy"},
                "sync": {"status": "Synced"},
                "team": team,
                "library": library,
            },
        }


    def _generate_istio_log(self, source: str, target: str) -> Dict[str, Any]:
        method = random.choice(["GET", "POST", "PUT", "DELETE"])
        path = random.choice(["/api/v1/users", "/api/v1/orders", "/api/v1/products", "/api/v1/cart"])
        status = 200
        duration = random.randint(1, 500)

        return {
            "timestamp": _now(),
            "method": method,
            "path": path,
            "protocol": "HTTP/1.1",
            "responseCode": status,
            "responseFlags": "-",
            "responseCodeDetails": "via_upstream",
            "upstreamCluster": f"outbound|8080||{target}.production.svc.cluster.local",
            "upstreamServiceTime": f"{duration}ms",
            "requestId": str(uuid.uuid4()),
            "duration": duration * 1_000_000,
            "is_external_call": False,
            "source": {
                "workload": source,
                "namespace": "production",
                "principal": f"cluster.local/ns/production/sa/{source}",
                "app": source,
            },
            "destination": {
                "workload": target,
                "namespace": "production",
                "principal": f"cluster.local/ns/production/sa/{target}",
                "app": target,
            },
        }

    def _generate_istio_metrics(self, source: str, target: str) -> Dict[str, Any]:
        return {
            "metric_samples": [
                {
                    "name": "istio_requests_total",
                    "labels": {
                        "source_workload": source,
                        "source_namespace": "production",
                        "destination_workload": target,
                        "destination_namespace": "production",
                        "response_code": "200",
                    },
                    "value": random.randint(1000, 50000),
                    "timestamp": int(datetime.now(timezone.utc).timestamp()),
                },
                {
                    "name": "istio_request_duration_milliseconds",
                    "labels": {
                        "source_workload": source,
                        "destination_workload": target,
                    },
                    "value": random.randint(10, 500),
                },
            ],
        }

    def generate_minimal(self) -> Dict[str, List[Dict[str, Any]]]:
        result = {
            "kubernetes-api": [],
            "terraform-state": [],
            "opentelemetry-traces": [],
            "prometheus-slo": [],
            "argocd": [],
        }

        result["kubernetes-api"].extend(self._generate_nodes())
        result["kubernetes-api"].append(self._generate_cluster())

        key_services = ["api-gateway", "auth-service", "user-service", "order-service", "payment-service"]

        for service in key_services:
            if service in self.state.services:
                result["kubernetes-api"].append(self._generate_deployment(service))
                result["kubernetes-api"].append(self._generate_service(service))

        for pod_info in self.state.pods:
            if pod_info["service"] in key_services:
                result["kubernetes-api"].append({
                    "apiVersion": "v1",
                    "kind": "Pod",
                    "metadata": {
                        "name": pod_info["name"],
                        "namespace": pod_info["namespace"],
                        "uid": str(uuid.uuid4()),
                        "labels": {
                            "app": pod_info["service"],
                            "deployment": pod_info["deployment"],
                        },
                    },
                    "spec": {
                        "nodeName": pod_info["node"],
                    },
                    "status": {
                        "phase": "Running",
                    },
                })

        for db in self.state.databases:
            if db["owner"] in key_services:
                result["terraform-state"].append(self._generate_database(db))

        for cache in self.state.caches:
            if cache["owner"] in key_services:
                result["terraform-state"].append(self._generate_cache(cache))

        for source, target in self.state.service_calls:
            if source in key_services:
                result["opentelemetry-traces"].append(self._generate_service_call_trace(source, target))

        for db in self.state.databases:
            if db["owner"] in key_services:
                result["opentelemetry-traces"].append(self._generate_db_trace(db["owner"], db))

        for cache in self.state.caches:
            if cache["owner"] in key_services:
                result["opentelemetry-traces"].append(self._generate_cache_trace(cache["owner"], cache))

        for ext_api in self.state.external_apis:
            if ext_api["owner"] in key_services:
                result["opentelemetry-traces"].append(self._generate_external_api_trace(ext_api["owner"], ext_api))

        for queue in self.state.queues:
            for publisher in queue["publishers"]:
                if publisher in key_services:
                    result["opentelemetry-traces"].append(self._generate_publish_trace(publisher, queue))
            for consumer in queue["consumers"]:
                if consumer in key_services:
                    result["opentelemetry-traces"].append(self._generate_consume_trace(consumer, queue))

        for slo in self.state.slo_configs:
            if slo["service"] in key_services:
                result["prometheus-slo"].append(self._generate_slo(slo))

        for service in key_services:
            if service in self.state.services:
                result["argocd"].append(self._generate_argocd_app(service))

        return result
