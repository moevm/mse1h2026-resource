from __future__ import annotations

import random
import string
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mocker.shared_state import SharedState


def _now_ns() -> int:
    now = datetime.now(timezone.utc)
    return int(now.timestamp() * 1_000_000_000)


def _random_hex(length: int = 16) -> str:
    return ''.join(random.choices('0123456789abcdef', k=length))


def _random_span_id() -> str:
    return _random_hex(16)


def _random_trace_id() -> str:
    return _random_hex(32)



def generate_k8s_pod(state: "SharedState", t: int) -> Dict[str, Any]:
    pod_info = state.get_random_pod()
    uid = str(uuid.uuid4())

    return {
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
            "creationTimestamp": datetime.now(timezone.utc).isoformat(),
        },
        "spec": {
            "nodeName": pod_info["node"],
            "serviceAccountName": "default",
            "containers": [
                {
                    "name": pod_info["service"],
                    "image": f"myregistry.io/{pod_info['service']}:v{random.randint(1, 10)}.{random.randint(0, 99)}",
                    "ports": [{"containerPort": 8080, "protocol": "TCP"}],
                    "resources": {
                        "requests": {"cpu": "100m", "memory": "256Mi"},
                        "limits": {"cpu": "500m", "memory": "512Mi"},
                    },
                }
            ],
        },
        "status": {
            "phase": random.choice(["Running", "Running", "Running", "Running", "Pending"]),
            "podIP": f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
            "hostIP": f"192.168.{random.randint(1, 10)}.{random.randint(1, 254)}",
            "conditions": [
                {"type": "Ready", "status": "True"},
                {"type": "ContainersReady", "status": "True"},
            ],
        },
    }


def generate_k8s_node(state: "SharedState", t: int) -> Dict[str, Any]:
    node_info = state.get_random_node()

    return {
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
    }


def generate_k8s_service(state: "SharedState", t: int) -> Dict[str, Any]:
    service_name = state.get_random_service()
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


def generate_k8s_cluster(state: "SharedState", t: int) -> Dict[str, Any]:
    return {
        "apiVersion": "cluster.k8s.io/v1alpha1",
        "kind": "Cluster",
        "metadata": {
            "name": state.cluster["name"],
            "uid": f"cluster-{state.cluster['name']}-{_random_hex(8)}",
            "labels": {
                "region": state.cluster["region"],
                "provider": state.cluster["provider"],
            },
        },
        "spec": {
            "region": state.cluster["region"],
            "provider": state.cluster["provider"],
            "cluster_id": state.cluster["name"],
        },
    }


def generate_k8s_deployment(state: "SharedState", t: int) -> Dict[str, Any]:
    deployment_info = state.get_random_deployment()
    uid = str(uuid.uuid4())
    ready = deployment_info["replicas"]

    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": deployment_info["name"],
            "namespace": "production",
            "uid": uid,
            "labels": {"app": deployment_info["name"]},
            "annotations": {
                "deployment.kubernetes.io/revision": "1",
                "team": deployment_info["team"],
            },
        },
        "spec": {
            "replicas": deployment_info["replicas"],
            "selector": {"matchLabels": {"app": deployment_info["name"]}},
            "template": {
                "metadata": {"labels": {"app": deployment_info["name"]}},
                "spec": {
                    "containers": [{
                        "name": deployment_info["name"],
                        "image": f"myregistry.io/{deployment_info['name']}:latest",
                    }]
                },
            },
        },
        "status": {
            "replicas": deployment_info["replicas"],
            "readyReplicas": ready,
            "availableReplicas": ready,
            "conditions": [
                {"type": "Progressing", "status": "True"},
                {"type": "Available", "status": "True"},
            ],
        },
    }



def generate_otel_trace(state: "SharedState", t: int) -> Dict[str, Any]:
    source_service = state.get_random_service()

    libraries = state.get_libraries_for_service(source_service)
    library_name = libraries[0] if libraries else "fastapi"
    library_language = "python"
    lib_lang_map = {
        "fastapi": "python",
        "SQLAlchemy": "python",
        "Pydantic": "python",
        "Express.js": "javascript",
        "gRPC (Go)": "go",
        "kafka-go": "go",
        "Spring Boot": "java",
    }
    library_language = lib_lang_map.get(library_name, "python")

    team = state.get_team_for_service(source_service)

    if random.random() > 0.85:
        ext_api = state.get_external_api_for_service(source_service)
        dest_service = ext_api["name"] if ext_api else "unknown-external"
        is_external = True
    else:
        dest_service = random.choice([s for s in state.services if s != source_service])
        is_external = False

    trace_id = _random_trace_id()
    span_id = _random_span_id()
    start_time = _now_ns() - random.randint(1_000_000, 100_000_000)
    end_time = start_time + random.randint(1_000_000, 50_000_000)

    attributes = [
        {"key": "service.name", "value": {"stringValue": source_service}},
        {"key": "service.version", "value": {"stringValue": f"v{random.randint(1, 10)}.{random.randint(0, 99)}"}},
        {"key": "deployment.environment", "value": {"stringValue": "production"}},
        {"key": "telemetry.sdk.name", "value": {"stringValue": library_name}},
        {"key": "telemetry.sdk.language", "value": {"stringValue": library_language}},
        {"key": "peer.service", "value": {"stringValue": dest_service}},
        {"key": "http.method", "value": {"stringValue": random.choice(["GET", "POST", "PUT", "DELETE"])}},
        {"key": "http.status_code", "value": {"intValue": random.choice([200, 200, 200, 201, 400, 500])}},
    ]

    if team:
        attributes.append({"key": "team", "value": {"stringValue": team}})

    if is_external:
        attributes.append({"key": "external_api", "value": {"stringValue": dest_service}})

    db = state.get_database_for_service(source_service)
    if db and random.random() > 0.5:
        attributes.extend([
            {"key": "db.system", "value": {"stringValue": db["type"]}},
            {"key": "db.name", "value": {"stringValue": db["name"]}},
        ])
        tables = state.get_tables_for_service(source_service)
        if tables:
            table = random.choice(tables)
            attributes.append({"key": "db.table", "value": {"stringValue": table["name"]}})

    cache = state.get_cache_for_service(source_service)
    if cache and random.random() > 0.7:
        attributes.append({"key": "cache.name", "value": {"stringValue": cache["name"]}})

    for queue in state.queues:
        if source_service in queue["publishers"] and random.random() > 0.8:
            attributes.append({"key": "messaging.publishes_to", "value": {"stringValue": queue["name"]}})
            attributes.append({"key": "messaging.destination", "value": {"stringValue": queue["name"]}})
            break
        elif source_service in queue["consumers"] and random.random() > 0.8:
            attributes.append({"key": "messaging.consumes_from", "value": {"stringValue": queue["name"]}})
            attributes.append({"key": "messaging.destination", "value": {"stringValue": queue["name"]}})
            break

    secrets = state.get_secrets_for_service(source_service)
    if secrets and random.random() > 0.7:
        auth_secret = secrets[0]
        attributes.append({"key": "auth_secret", "value": {"stringValue": auth_secret}})

    if secrets and random.random() > 0.8:
        rate_limit_secret = secrets[-1]
        attributes.append({"key": "rate_limit_config", "value": {"stringValue": rate_limit_secret}})

    failover = state.get_failover_for_service(source_service)
    if failover and random.random() > 0.9:
        attributes.append({"key": "failover_service", "value": {"stringValue": failover}})

    span = {
        "traceId": trace_id,
        "spanId": span_id,
        "name": f"{source_service} -> {dest_service}",
        "kind": 2,
        "startTimeUnixNano": start_time,
        "endTimeUnixNano": end_time,
        "attributes": attributes,
        "status": {"code": 1},
    }

    return {
        "resourceSpans": [{
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": source_service}},
                    {"key": "telemetry.sdk.name", "value": {"stringValue": library_name}},
                ],
            },
            "scopeSpans": [{
                "scope": {"name": source_service},
                "spans": [span],
            }],
        }],
    }


def generate_otel_metrics(state: "SharedState", t: int) -> Dict[str, Any]:
    service_name = state.get_random_service()
    base_time = _now_ns()

    metrics = [
        {
            "name": "process_cpu_utilization",
            "gauge": {
                "dataPoints": [{
                    "attributes": [{"key": "service.name", "value": {"stringValue": service_name}}],
                    "timeUnixNano": base_time,
                    "asDouble": random.uniform(0.1, 0.9),
                }],
            },
        },
        {
            "name": "process_memory_usage",
            "gauge": {
                "dataPoints": [{
                    "attributes": [{"key": "service.name", "value": {"stringValue": service_name}}],
                    "timeUnixNano": base_time,
                    "asInt": random.randint(100_000_000, 1_000_000_000),
                }],
            },
        },
        {
            "name": "http_server_requests",
            "sum": {
                "dataPoints": [{
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": service_name}},
                        {"key": "http.method", "value": {"stringValue": "GET"}},
                    ],
                    "timeUnixNano": base_time,
                    "asInt": random.randint(1000, 10000),
                }],
            },
        },
    ]

    return {
        "resourceMetrics": [{
            "resource": {
                "attributes": [{"key": "service.name", "value": {"stringValue": service_name}}],
            },
            "scopeMetrics": [{
                "scope": {"name": service_name},
                "metrics": metrics,
            }],
        }],
    }



def generate_istio_access_log(state: "SharedState", t: int) -> Dict[str, Any]:
    source_service = state.get_random_service()

    if random.random() > 0.85:
        ext_api = state.get_external_api_for_service(source_service)
        dest_service = ext_api["name"] if ext_api else "unknown-external"
        is_external = True
    else:
        dest_service = random.choice([s for s in state.services if s != source_service])
        is_external = False

    method = random.choice(["GET", "POST", "PUT", "DELETE"])
    path = random.choice(["/api/v1/users", "/api/v1/orders", "/api/v1/products", "/api/v1/cart"])
    status = random.choice([200, 200, 200, 201, 400, 500, 503])
    duration = random.randint(1, 500)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": method,
        "path": path,
        "protocol": "HTTP/1.1",
        "responseCode": status,
        "responseFlags": "-",
        "responseCodeDetails": "via_upstream",
        "upstreamCluster": f"outbound|8080||{dest_service}.production.svc.cluster.local",
        "upstreamServiceTime": f"{duration}ms",
        "requestId": str(uuid.uuid4()),
        "duration": duration * 1_000_000,
        "is_external_call": is_external,
        "external_api_name": dest_service if is_external else None,
        "source": {
            "workload": source_service,
            "namespace": "production",
            "principal": f"cluster.local/ns/production/sa/{source_service}",
            "app": source_service,
        },
        "destination": {
            "workload": dest_service,
            "namespace": "production" if not is_external else "external",
            "principal": f"cluster.local/ns/production/sa/{dest_service}" if not is_external else "external",
            "app": dest_service,
        },
    }


def generate_istio_metrics(state: "SharedState", t: int) -> Dict[str, Any]:
    source_service = state.get_random_service()
    dest_service = random.choice([s for s in state.services if s != source_service])

    return {
        "metric_samples": [
            {
                "name": "istio_requests_total",
                "labels": {
                    "source_workload": source_service,
                    "source_namespace": "production",
                    "destination_workload": dest_service,
                    "destination_namespace": "production",
                    "response_code": str(random.choice([200, 200, 200, 400, 500])),
                },
                "value": random.randint(1000, 50000),
                "timestamp": int(datetime.now(timezone.utc).timestamp()),
            },
            {
                "name": "istio_request_duration_milliseconds",
                "labels": {
                    "source_workload": source_service,
                    "destination_workload": dest_service,
                },
                "value": random.randint(10, 500),
            },
        ],
    }



def generate_prometheus_metrics(state: "SharedState", t: int) -> Dict[str, Any]:
    service_name = state.get_random_service()
    team = state.get_team_for_service(service_name)

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
            "job": service_name,
            "instance": f"{service_name}-0:9090",
            "namespace": "production",
            "service": service_name,
            "team": team,
        },
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
    }


def generate_prometheus_slo(state: "SharedState", t: int) -> Dict[str, Any]:
    slo = state.get_random_slo()
    service_name = slo["service"]

    if slo["metric"] == "availability":
        current = min(100.0, slo["target"] + random.uniform(-0.1, 0.05))
        error_budget_remaining = (current - (100 - (100 - slo["target"]))) / (100 - slo["target"]) * 100
    else:
        current = slo["target"] * random.uniform(0.8, 1.2)
        error_budget_remaining = 100.0 if current <= slo["target"] else 0.0

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
            "slo_error_budget_remaining": error_budget_remaining,
            "slo_burn_rate": random.uniform(0.1, 2.0),
        },
        "labels": {
            "slo": slo["name"],
            "service": service_name,
            "metric": slo["metric"],
        },
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
    }



def generate_terraform_db(state: "SharedState", t: int) -> Dict[str, Any]:
    db = state.get_random_database()
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
                    "Team": state.get_team_for_service(db["owner"]),
                    "DisplayName": db["name"],
                },
            },
        }],
    }


def generate_terraform_cache(state: "SharedState", t: int) -> Dict[str, Any]:
    cache = state.get_random_cache()
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
                    "DisplayName": cache["name"],
                },
            },
        }],
    }


def generate_terraform_queue(state: "SharedState", t: int) -> Dict[str, Any]:
    queue = state.get_random_queue()
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
                },
            },
        }],
        "publishers": queue["publishers"],
        "consumers": queue["consumers"],
    }


def generate_terraform_state(state: "SharedState", t: int) -> Dict[str, Any]:
    choice = random.choice(["db", "cache", "queue", "secret", "sqs", "sns", "table"])
    if choice == "db":
        return generate_terraform_db(state, t)
    elif choice == "cache":
        return generate_terraform_cache(state, t)
    elif choice == "queue":
        return generate_terraform_queue(state, t)
    elif choice == "secret":
        return generate_terraform_secret(state, t)
    elif choice == "sqs":
        return generate_terraform_sqs(state, t)
    elif choice == "sns":
        return generate_terraform_sns(state, t)
    else:
        return generate_table(state, t)



def generate_argocd_application(state: "SharedState", t: int) -> Dict[str, Any]:
    service_name = state.get_random_service()
    team = state.get_team_for_service(service_name)
    libraries = state.get_libraries_for_service(service_name)
    library = libraries[0] if libraries else None

    return {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Application",
        "metadata": {
            "name": service_name,
            "namespace": "argocd",
            "labels": {
                "team": team,
                "service": service_name,
            },
        },
        "spec": {
            "project": "default",
            "source": {
                "repoURL": "https://gitlab.example.com/platform/services.git",
                "targetRevision": "main",
                "path": f"deploy/{service_name}",
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
            "health": {
                "status": random.choice(["Healthy", "Healthy", "Healthy", "Progressing", "Degraded"]),
            },
            "sync": {
                "status": random.choice(["Synced", "Synced", "Synced", "OutOfSync"]),
            },
            "history": [{
                "revision": f"abc{_random_hex(5)}",
                "deployedAt": datetime.now(timezone.utc).isoformat(),
            }],
            "team": team,
            "library": library,
        },
    }



def generate_api_gateway_route(state: "SharedState", t: int) -> Dict[str, Any]:
    endpoint = state.get_random_endpoint()
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



def generate_table(state: "SharedState", t: int) -> Dict[str, Any]:
    table = state.get_random_table()
    return {
        "type": "table",
        "name": table["name"],
        "schema_name": "public",
        "database_name": table["database"],
        "owner_service": table["owner"],
        "row_count": random.randint(100_000, 10_000_000),
        "is_partitioned": random.random() > 0.7,
    }


def generate_terraform_secret(state: "SharedState", t: int) -> Dict[str, Any]:
    secret = state.get_random_secret()
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


def generate_terraform_sqs(state: "SharedState", t: int) -> Dict[str, Any]:
    queue = state.get_random_queue()
    return {
        "module": "module.messaging",
        "mode": "managed",
        "type": "aws_sqs_queue",
        "name": queue["name"].replace(".", "_"),
        "instances": [{
            "attributes": {
                "name": queue["name"],
                "visibility_timeout_seconds": 30,
                "message_retention_seconds": 1209600,
                "tags": {
                    "Environment": "production",
                    "DisplayName": queue["name"],
                },
            },
        }],
        "publishers": queue["publishers"],
        "consumers": queue["consumers"],
    }


def generate_terraform_sns(state: "SharedState", t: int) -> Dict[str, Any]:
    queue = state.get_random_queue()
    return {
        "module": "module.messaging",
        "mode": "managed",
        "type": "aws_sns_topic",
        "name": queue["name"].replace(".", "_"),
        "instances": [{
            "attributes": {
                "name": queue["name"],
                "tags": {
                    "Environment": "production",
                    "DisplayName": queue["name"],
                },
            },
        }],
        "publishers": queue["publishers"],
        "consumers": queue["consumers"],
    }




RAW_GENERATORS = {
    "kubernetes-api": {
        "pod": generate_k8s_pod,
        "node": generate_k8s_node,
        "service": generate_k8s_service,
        "deployment": generate_k8s_deployment,
        "cluster": generate_k8s_cluster,
    },
    "opentelemetry-traces": {
        "trace": generate_otel_trace,
    },
    "opentelemetry-metrics": {
        "metrics": generate_otel_metrics,
    },
    "istio-access-logs": {
        "log": generate_istio_access_log,
    },
    "istio-metrics": {
        "metrics": generate_istio_metrics,
    },
    "prometheus": {
        "metrics": generate_prometheus_metrics,
    },
    "prometheus-slo": {
        "slo": generate_prometheus_slo,
    },
    "terraform-state": {
        "db": generate_terraform_db,
        "cache": generate_terraform_cache,
        "queue": generate_terraform_queue,
        "secret": generate_terraform_secret,
        "sqs": generate_terraform_sqs,
        "sns": generate_terraform_sns,
        "state": generate_terraform_state,
        "table": generate_table,
    },
    "argocd": {
        "application": generate_argocd_application,
    },
    "api-gateway": {
        "route": generate_api_gateway_route,
    },
}


def generate_raw_data(state: "SharedState", source_type: str, t: int) -> Dict[str, Any]:
    generators = RAW_GENERATORS.get(source_type, {})

    if not generators:
        return generate_k8s_pod(state, t)

    gen_name = random.choice(list(generators.keys()))
    generator = generators[gen_name]

    return generator(state, t)


def generate_raw_batch(state: "SharedState", source_type: str, t: int, count: int = 1) -> List[Dict[str, Any]]:
    generators = RAW_GENERATORS.get(source_type, {})

    if not generators:
        return [generate_k8s_pod(state, t) for _ in range(count)]

    items = []
    for _ in range(count):
        gen_name = random.choice(list(generators.keys()))
        generator = generators[gen_name]
        items.append(generator(state, t))

    return items
