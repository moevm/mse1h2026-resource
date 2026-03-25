from __future__ import annotations

from typing import Any, Dict

KUBERNETES_API_SAMPLE: Dict[str, Any] = {
    "apiVersion": "v1",
    "kind": "Node",
    "metadata": {
        "name": "ip-10-0-1-101",
        "uid": "node-ip-10-0-1-101-test",
        "labels": {
            "kubernetes.io/arch": "amd64",
            "kubernetes.io/os": "linux",
            "node-role.kubernetes.io/worker": "true",
            "topology.kubernetes.io/zone": "eu-central-1a",
            "node.kubernetes.io/instance-type": "m6i.2xlarge",
        },
    },
    "spec": {
        "podCIDR": "10.200.0.0/24",
        "providerID": "aws:///eu-central-1a/i-testnode101",
    },
    "status": {
        "capacity": {
            "cpu": "8",
            "memory": "32Gi",
            "pods": "110",
        },
        "nodeInfo": {
            "kubeletVersion": "v1.28.4",
            "osImage": "Ubuntu 22.04.3 LTS",
        },
    },
}

KUBERNETES_API_POD_SAMPLE: Dict[str, Any] = {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
        "name": "api-gateway-0-test",
        "namespace": "production",
        "uid": "pod-test-001",
        "labels": {
            "app": "api-gateway",
            "deployment": "api-gateway",
        },
    },
    "spec": {
        "nodeName": "ip-10-0-1-101",
        "serviceAccountName": "default",
        "containers": [{
            "name": "api-gateway",
            "image": "myregistry.io/api-gateway:v1.0.0",
        }],
    },
    "status": {
        "phase": "Running",
        "podIP": "10.200.0.50",
    },
}

KUBERNETES_API_DEPLOYMENT_SAMPLE: Dict[str, Any] = {
    "apiVersion": "apps/v1",
    "kind": "Deployment",
    "metadata": {
        "name": "api-gateway",
        "namespace": "production",
        "uid": "deploy-test-001",
        "labels": {"app": "api-gateway", "cluster": "prod-ecommerce"},
        "annotations": {
            "deployment.kubernetes.io/revision": "1",
            "team": "Platform Engineering",
        },
    },
    "spec": {
        "replicas": 3,
        "selector": {"matchLabels": {"app": "api-gateway"}},
    },
    "status": {
        "replicas": 3,
        "readyReplicas": 3,
    },
}

KUBERNETES_API_CLUSTER_SAMPLE: Dict[str, Any] = {
    "apiVersion": "cluster.k8s.io/v1alpha1",
    "kind": "Cluster",
    "metadata": {
        "name": "prod-ecommerce",
        "uid": "cluster-test-001",
        "labels": {
            "region": "eu-central-1",
            "provider": "aws",
        },
    },
    "spec": {
        "region": "eu-central-1",
        "provider": "aws",
        "cluster_id": "prod-ecommerce",
    },
}

OTEL_TRACES_SERVICE_CALL_SAMPLE: Dict[str, Any] = {
    "resourceSpans": [{
        "resource": {
            "attributes": [
                {"key": "service.name", "value": {"stringValue": "api-gateway"}},
                {"key": "telemetry.sdk.name", "value": {"stringValue": "gRPC (Go)"}},
                {"key": "telemetry.sdk.language", "value": {"stringValue": "go"}},
            ],
        },
        "scopeSpans": [{
            "scope": {"name": "api-gateway"},
            "spans": [{
                "traceId": "0123456789abcdef0123456789abcdef",
                "spanId": "0123456789abcdef",
                "name": "api-gateway -> auth-service",
                "kind": 2,
                "startTimeUnixNano": 1700000000000000000,
                "endTimeUnixNano": 1700000000100000000,
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "api-gateway"}},
                    {"key": "service.version", "value": {"stringValue": "v1.0.0"}},
                    {"key": "deployment.environment", "value": {"stringValue": "production"}},
                    {"key": "peer.service", "value": {"stringValue": "auth-service"}},
                    {"key": "http.method", "value": {"stringValue": "POST"}},
                    {"key": "http.status_code", "value": {"intValue": 200}},
                    {"key": "team", "value": {"stringValue": "Platform Engineering"}},
                ],
                "status": {"code": 1},
            }],
        }],
    }],
}

OTEL_TRACES_DB_SAMPLE: Dict[str, Any] = {
    "resourceSpans": [{
        "resource": {
            "attributes": [
                {"key": "service.name", "value": {"stringValue": "user-service"}},
                {"key": "telemetry.sdk.name", "value": {"stringValue": "SQLAlchemy"}},
            ],
        },
        "scopeSpans": [{
            "scope": {"name": "user-service"},
            "spans": [{
                "traceId": "abcdef0123456789abcdef0123456789",
                "spanId": "abcdef0123456789",
                "name": "user-service -> Users DB",
                "kind": 2,
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "user-service"}},
                    {"key": "db.system", "value": {"stringValue": "postgresql"}},
                    {"key": "db.name", "value": {"stringValue": "Users DB"}},
                    {"key": "db.table", "value": {"stringValue": "public.users"}},
                    {"key": "team", "value": {"stringValue": "Identity & Access"}},
                ],
                "status": {"code": 1},
            }],
        }],
    }],
}

OTEL_TRACES_EXTERNAL_SAMPLE: Dict[str, Any] = {
    "resourceSpans": [{
        "resource": {
            "attributes": [
                {"key": "service.name", "value": {"stringValue": "payment-service"}},
                {"key": "telemetry.sdk.name", "value": {"stringValue": "Spring Boot"}},
            ],
        },
        "scopeSpans": [{
            "scope": {"name": "payment-service"},
            "spans": [{
                "traceId": "fedcba9876543210fedcba9876543210",
                "spanId": "fedcba9876543210",
                "name": "payment-service -> Stripe API",
                "kind": 2,
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "payment-service"}},
                    {"key": "external_api", "value": {"stringValue": "Stripe API"}},
                    {"key": "team", "value": {"stringValue": "Payments Team"}},
                ],
                "status": {"code": 1},
            }],
        }],
    }],
}

OTEL_TRACES_MESSAGING_SAMPLE: Dict[str, Any] = {
    "resourceSpans": [{
        "resource": {
            "attributes": [
                {"key": "service.name", "value": {"stringValue": "order-service"}},
                {"key": "telemetry.sdk.name", "value": {"stringValue": "kafka-go"}},
            ],
        },
        "scopeSpans": [{
            "scope": {"name": "order-service"},
            "spans": [{
                "traceId": "11112222333344445555666677778888",
                "spanId": "1111222233334444",
                "name": "order-service -> prod.orders.events",
                "kind": 2,
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": "order-service"}},
                    {"key": "messaging.publishes_to", "value": {"stringValue": "prod.orders.events"}},
                    {"key": "messaging.destination", "value": {"stringValue": "prod.orders.events"}},
                    {"key": "team", "value": {"stringValue": "Order Management"}},
                ],
                "status": {"code": 1},
            }],
        }],
    }],
}

OTEL_METRICS_SAMPLE: Dict[str, Any] = {
    "resourceMetrics": [{
        "resource": {
            "attributes": [{"key": "service.name", "value": {"stringValue": "api-gateway"}}],
        },
        "scopeMetrics": [{
            "scope": {"name": "api-gateway"},
            "metrics": [
                {
                    "name": "process_cpu_utilization",
                    "gauge": {
                        "dataPoints": [{
                            "attributes": [{"key": "service.name", "value": {"stringValue": "api-gateway"}}],
                            "timeUnixNano": 1700000000000000000,
                            "asDouble": 0.45,
                        }],
                    },
                },
            ],
        }],
    }],
}

ISTIO_ACCESS_LOGS_SAMPLE: Dict[str, Any] = {
    "timestamp": "2024-01-01T12:00:00.000Z",
    "method": "POST",
    "path": "/api/v1/auth/login",
    "protocol": "HTTP/1.1",
    "responseCode": 200,
    "responseFlags": "-",
    "responseCodeDetails": "via_upstream",
    "upstreamCluster": "outbound|8080||auth-service.production.svc.cluster.local",
    "upstreamServiceTime": "50ms",
    "requestId": "req-test-001",
    "duration": 50000000,
    "is_external_call": False,
    "source": {
        "workload": "api-gateway",
        "namespace": "production",
        "principal": "cluster.local/ns/production/sa/api-gateway",
        "app": "api-gateway",
    },
    "destination": {
        "workload": "auth-service",
        "namespace": "production",
        "principal": "cluster.local/ns/production/sa/auth-service",
        "app": "auth-service",
    },
}

ISTIO_METRICS_SAMPLE: Dict[str, Any] = {
    "metric_samples": [
        {
            "name": "istio_requests_total",
            "labels": {
                "source_workload": "api-gateway",
                "source_namespace": "production",
                "destination_workload": "auth-service",
                "destination_namespace": "production",
                "response_code": "200",
            },
            "value": 15000,
            "timestamp": 1700000000,
        },
        {
            "name": "istio_request_duration_milliseconds",
            "labels": {
                "source_workload": "api-gateway",
                "destination_workload": "auth-service",
            },
            "value": 50,
        },
    ],
}

PROMETHEUS_SAMPLE: Dict[str, Any] = {
    "metrics": {
        "process_cpu_seconds_total": 5000.5,
        "process_open_fds": 45,
        "process_resident_memory_bytes": 250000000,
        "http_requests_total": 500000,
        "http_request_duration_seconds_sum": 500.5,
        "http_request_duration_seconds_count": 50000,
    },
    "labels": {
        "job": "api-gateway",
        "instance": "api-gateway-0:9090",
        "namespace": "production",
        "service": "api-gateway",
        "team": "Platform Engineering",
    },
    "timestamp": 1700000000,
}

PROMETHEUS_SLO_SAMPLE: Dict[str, Any] = {
    "type": "slo-metric",
    "name": "slo_api_gateway_availability",
    "slo_name": "API Gateway Availability",
    "service": "api-gateway",
    "metric_name": "availability",
    "target": 99.95,
    "current": 99.97,
    "metrics": {
        "slo_target": 99.95,
        "slo_current": 99.97,
        "slo_error_budget_remaining": 85.5,
        "slo_burn_rate": 0.5,
    },
    "labels": {
        "slo": "API Gateway Availability",
        "service": "api-gateway",
        "metric": "availability",
    },
    "timestamp": 1700000000,
}

TERRAFORM_STATE_DB_SAMPLE: Dict[str, Any] = {
    "module": "module.database",
    "mode": "managed",
    "type": "aws_db_instance",
    "name": "users_db",
    "instances": [{
        "attributes": {
            "identifier": "users-db",
            "engine": "postgres",
            "engine_version": "16.2",
            "instance_class": "db.t3.small",
            "allocated_storage": 100,
            "database_name": "users_db",
            "tags": {
                "Environment": "production",
                "Service": "user-service",
                "Team": "Identity & Access",
                "DisplayName": "Users DB",
            },
        },
    }],
    "owner_service": "user-service",
    "team": "Identity & Access",
}

TERRAFORM_STATE_CACHE_SAMPLE: Dict[str, Any] = {
    "module": "module.cache",
    "mode": "managed",
    "type": "aws_elasticache_cluster",
    "name": "session_cache",
    "instances": [{
        "attributes": {
            "cluster_id": "session-cache",
            "engine": "redis",
            "engine_version": "7.0",
            "node_type": "cache.t3.micro",
            "num_cache_nodes": 3,
            "tags": {
                "Environment": "production",
                "Service": "auth-service",
                "Team": "Identity & Access",
                "DisplayName": "Session Cache",
            },
        },
    }],
    "owner_service": "auth-service",
    "team": "Identity & Access",
}

TERRAFORM_STATE_QUEUE_SAMPLE: Dict[str, Any] = {
    "module": "module.messaging",
    "mode": "managed",
    "type": "aws_msk_topic",
    "name": "orders_events",
    "instances": [{
        "attributes": {
            "name": "prod.orders.events",
            "partitions": 12,
            "replication_factor": 3,
            "tags": {
                "Environment": "production",
                "DisplayName": "prod.orders.events",
            },
        },
    }],
    "publishers": ["order-service", "cart-service"],
    "consumers": ["inventory-service", "notification-service", "payment-service"],
}

TERRAFORM_STATE_SECRET_SAMPLE: Dict[str, Any] = {
    "module": "module.secrets",
    "mode": "managed",
    "type": "aws_secretsmanager_secret",
    "name": "jwt_signing_key",
    "instances": [{
        "attributes": {
            "name": "JWT Signing Key",
            "description": "Secret for api-gateway, auth-service",
            "tags": {
                "Environment": "production",
                "Provider": "hashicorp_vault",
            },
        },
    }],
    "services": ["api-gateway", "auth-service"],
}

TERRAFORM_STATE_TABLE_SAMPLE: Dict[str, Any] = {
    "type": "table",
    "name": "public.users",
    "schema_name": "public",
    "database_name": "Users DB",
    "owner_service": "user-service",
    "database_ref": "Users DB",
    "row_count": 500000,
    "is_partitioned": False,
}

ARGOCD_SAMPLE: Dict[str, Any] = {
    "apiVersion": "argoproj.io/v1alpha1",
    "kind": "Application",
    "metadata": {
        "name": "api-gateway",
        "namespace": "argocd",
        "labels": {
            "team": "Platform Engineering",
            "service": "api-gateway",
        },
    },
    "spec": {
        "project": "default",
        "source": {
            "repoURL": "https://gitlab.example.com/platform/services.git",
            "targetRevision": "main",
            "path": "deploy/api-gateway",
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
        "team": "Platform Engineering",
        "library": "gRPC (Go)",
    },
}

API_GATEWAY_SAMPLE: Dict[str, Any] = {
    "apiVersion": "networking.k8s.io/v1",
    "kind": "Ingress",
    "metadata": {
        "name": "auth-service-ingress",
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
                    "path": "/api/v1/auth/login",
                    "pathType": "Prefix",
                    "backend": {
                        "service": {
                            "name": "auth-service",
                            "port": {"number": 8080},
                        },
                    },
                }],
            },
        }],
    },
}


SAMPLE_DATA_BY_SOURCE_TYPE = {
    "kubernetes-api": [
        KUBERNETES_API_SAMPLE,
        KUBERNETES_API_POD_SAMPLE,
        KUBERNETES_API_DEPLOYMENT_SAMPLE,
        KUBERNETES_API_CLUSTER_SAMPLE,
    ],
    "opentelemetry-traces": [
        OTEL_TRACES_SERVICE_CALL_SAMPLE,
        OTEL_TRACES_DB_SAMPLE,
        OTEL_TRACES_EXTERNAL_SAMPLE,
        OTEL_TRACES_MESSAGING_SAMPLE,
    ],
    "opentelemetry-metrics": [OTEL_METRICS_SAMPLE],
    "istio-access-logs": [ISTIO_ACCESS_LOGS_SAMPLE],
    "istio-metrics": [ISTIO_METRICS_SAMPLE],
    "prometheus": [PROMETHEUS_SAMPLE],
    "prometheus-slo": [PROMETHEUS_SLO_SAMPLE],
    "terraform-state": [
        TERRAFORM_STATE_DB_SAMPLE,
        TERRAFORM_STATE_CACHE_SAMPLE,
        TERRAFORM_STATE_QUEUE_SAMPLE,
        TERRAFORM_STATE_SECRET_SAMPLE,
        TERRAFORM_STATE_TABLE_SAMPLE,
    ],
    "argocd": [ARGOCD_SAMPLE],
    "api-gateway": [API_GATEWAY_SAMPLE],
}

PRIMARY_SAMPLE_BY_SOURCE_TYPE = {
    source_type: samples[0]
    for source_type, samples in SAMPLE_DATA_BY_SOURCE_TYPE.items()
}
