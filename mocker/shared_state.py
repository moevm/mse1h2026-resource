"""
Shared state for consistent mock data generation.

All generators use this shared state to ensure that:
- Pods reference existing Nodes
- Service calls reference existing Services
- Database references are consistent
- No dangling references in the generated graph
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SharedState:
    """Shared state for consistent data generation across all source types."""

    # Infrastructure
    nodes: List[Dict] = field(default_factory=list)
    cluster: Dict = field(default_factory=dict)

    # Application layer
    services: List[str] = field(default_factory=list)
    pods: List[Dict] = field(default_factory=list)
    deployments: List[Dict] = field(default_factory=list)

    # Data layer
    databases: List[Dict] = field(default_factory=list)
    caches: List[Dict] = field(default_factory=list)
    queues: List[Dict] = field(default_factory=list)

    # External
    external_apis: List[Dict] = field(default_factory=list)
    endpoints: List[Dict] = field(default_factory=list)

    # Org
    teams: List[str] = field(default_factory=list)
    team_ownerships: Dict[str, str] = field(default_factory=dict)

    # NEW: Additional entities for richer graph
    tables: List[Dict] = field(default_factory=list)
    libraries: List[Dict] = field(default_factory=list)
    slo_configs: List[Dict] = field(default_factory=list)
    secrets: List[Dict] = field(default_factory=list)
    service_calls: List[tuple] = field(default_factory=list)  # (source, target)

    def __post_init__(self):
        """Initialize all shared state."""
        self._init_infrastructure()
        self._init_services()
        self._init_data_layer()
        self._init_external()
        self._init_org()

    def _init_infrastructure(self):
        """Initialize nodes and cluster."""
        self.cluster = {
            "name": "prod-cluster",
            "region": "us-east-1",
            "provider": "aws",
        }

        # 5 worker nodes across 3 availability zones
        zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
        self.nodes = [
            {
                "name": f"worker-node-{i}",
                "zone": zones[(i - 1) % len(zones)],
                "instance_type": random.choice(["m5.large", "m5.xlarge", "c5.2xlarge"]),
                "capacity_cpu": random.choice(["4", "8", "16"]),
                "capacity_memory": random.choice(["16Gi", "32Gi", "64Gi"]),
            }
            for i in range(1, 6)
        ]

    def _init_services(self):
        """Initialize services, pods, and deployments."""
        # 11 microservices matching old generator
        self.services = [
            "api-gateway",
            "auth-service",
            "user-service",
            "cart-service",
            "order-service",
            "payment-service",
            "notification-service",
            "product-service",
            "inventory-service",
            "search-service",
            "recommendation-service",
        ]

        # Assign team ownership
        team_assignments = [
            ("api-gateway", "platform"),
            ("auth-service", "platform"),
            ("user-service", "user-eng"),
            ("cart-service", "checkout"),
            ("order-service", "checkout"),
            ("payment-service", "payments"),
            ("notification-service", "platform"),
            ("product-service", "catalog"),
            ("inventory-service", "catalog"),
            ("search-service", "search"),
            ("recommendation-service", "search"),
        ]
        for service, team in team_assignments:
            self.team_ownerships[service] = team

        # Generate deployments (one per service)
        self.deployments = [
            {
                "name": service,
                "replicas": random.randint(2, 4),
                "team": self.team_ownerships.get(service, "platform"),
            }
            for service in self.services
        ]

        # Generate pods - distribute across nodes
        self._generate_pods()

    def _generate_pods(self):
        """Generate pods with consistent service->node mapping."""
        self.pods = []
        node_idx = 0

        for deployment in self.deployments:
            service_name = deployment["name"]
            replicas = deployment["replicas"]

            for replica_idx in range(replicas):
                node = self.nodes[node_idx % len(self.nodes)]
                pod_name = f"{service_name}-{replica_idx}-{random.randint(1000, 9999)}"

                self.pods.append({
                    "name": pod_name,
                    "service": service_name,
                    "deployment": service_name,
                    "node": node["name"],
                    "namespace": "production",
                    "node_zone": node["zone"],
                })
                node_idx += 1

    def _init_data_layer(self):
        """Initialize databases, caches, and queues."""
        # Databases - each owned by specific service (matching topology.py)
        self.databases = [
            {
                "name": "postgres-users",
                "type": "postgresql",
                "engine_version": "16.2",
                "owner": "user-service",
                "tables": ["users", "sessions"],
            },
            {
                "name": "postgres-orders",
                "type": "postgresql",
                "engine_version": "16.2",
                "owner": "order-service",
                "tables": ["orders", "order_items"],
            },
            {
                "name": "postgres-payment",
                "type": "postgresql",
                "engine_version": "16.2",
                "owner": "payment-service",
                "tables": ["transactions", "refunds"],
            },
            {
                "name": "postgres-inventory",
                "type": "postgresql",
                "engine_version": "16.2",
                "owner": "inventory-service",
                "tables": ["stock_levels"],
            },
            {
                "name": "mongodb-products",
                "type": "mongodb",
                "engine_version": "7.0.5",
                "owner": "product-service",
                "collections": ["products", "categories"],
            },
        ]

        # Caches
        self.caches = [
            {
                "name": "redis-sessions",
                "owner": "auth-service",
                "type": "redis",
                "cluster_size": 3,
            },
            {
                "name": "redis-products",
                "owner": "product-service",
                "type": "redis",
                "cluster_size": 5,
            },
            {
                "name": "redis-cart",
                "owner": "cart-service",
                "type": "redis",
                "cluster_size": 3,
            },
        ]

        # Kafka topics
        self.queues = [
            {
                "name": "orders-created",
                "type": "kafka",
                "partitions": 12,
                "publishers": ["order-service"],
                "consumers": ["inventory-service", "notification-service", "search-service"],
            },
            {
                "name": "user-events",
                "type": "kafka",
                "partitions": 6,
                "publishers": ["user-service", "api-gateway"],
                "consumers": ["recommendation-service", "notification-service"],
            },
            {
                "name": "product-updates",
                "type": "kafka",
                "partitions": 6,
                "publishers": ["product-service"],
                "consumers": ["search-service", "recommendation-service", "inventory-service"],
            },
        ]

    def _init_external(self):
        """Initialize external APIs and endpoints."""
        # External APIs
        self.external_apis = [
            {"name": "stripe", "owner": "payment-service", "type": "payment"},
            {"name": "sendgrid", "owner": "notification-service", "type": "email"},
            {"name": "twilio", "owner": "notification-service", "type": "sms"},
            {"name": "cloudflare", "owner": "api-gateway", "type": "cdn"},
            {"name": "aws-s3", "owner": "product-service", "type": "storage"},
        ]

        # API Endpoints
        self.endpoints = [
            {"path": "/api/v1/users", "service": "user-service", "method": "GET"},
            {"path": "/api/v1/users/{id}", "service": "user-service", "method": "GET"},
            {"path": "/api/v1/orders", "service": "order-service", "method": "POST"},
            {"path": "/api/v1/orders/{id}", "service": "order-service", "method": "GET"},
            {"path": "/api/v1/products", "service": "product-service", "method": "GET"},
            {"path": "/api/v1/products/{id}", "service": "product-service", "method": "GET"},
            {"path": "/api/v1/cart", "service": "cart-service", "method": "GET"},
            {"path": "/api/v1/cart/items", "service": "cart-service", "method": "POST"},
            {"path": "/api/v1/payments", "service": "payment-service", "method": "POST"},
            {"path": "/api/v1/search", "service": "search-service", "method": "GET"},
            {"path": "/api/v1/recommendations", "service": "recommendation-service", "method": "GET"},
        ]

    def _init_org(self):
        """Initialize teams, libraries, SLOs, secrets, and service calls."""
        self.teams = ["platform", "payments", "identity", "orders", "product", "search"]

        # Team ownerships (matching topology.py)
        self.team_ownerships = {
            "api-gateway": "platform",
            "auth-service": "identity",
            "user-service": "identity",
            "order-service": "orders",
            "cart-service": "orders",
            "inventory-service": "orders",
            "payment-service": "payments",
            "notification-service": "platform",
            "product-service": "product",
            "search-service": "search",
            "recommendation-service": "search",
        }

        # Libraries per language/framework (matching topology.py)
        self.libraries = [
            {"name": "grpc-go", "language": "go", "services": ["api-gateway"]},
            {"name": "gin", "language": "go", "services": ["auth-service", "inventory-service"]},
            {"name": "spring-boot", "language": "java", "services": ["order-service", "payment-service"]},
            {"name": "kafka-go", "language": "go", "services": ["order-service"]},
            {"name": "express", "language": "nodejs", "services": ["cart-service", "product-service"]},
            {"name": "fastapi", "language": "python", "services": ["user-service", "search-service", "notification-service", "recommendation-service"]},
            {"name": "sqlalchemy", "language": "python", "services": ["user-service", "search-service"]},
            {"name": "pydantic", "language": "python", "services": ["user-service", "search-service", "notification-service", "recommendation-service"]},
        ]

        # SLO configs (matching topology.py)
        self.slo_configs = [
            {"name": "api-gateway-availability", "service": "api-gateway", "metric": "availability", "target": 99.95},
            {"name": "api-gateway-latency", "service": "api-gateway", "metric": "latency_p99", "target": 200.0},
            {"name": "payment-availability", "service": "payment-service", "metric": "availability", "target": 99.99},
            {"name": "payment-latency", "service": "payment-service", "metric": "latency_p99", "target": 500.0},
            {"name": "order-latency", "service": "order-service", "metric": "latency_p99", "target": 300.0},
            {"name": "search-latency", "service": "search-service", "metric": "latency_p99", "target": 150.0},
        ]

        # Secrets (matching topology.py)
        self.secrets = [
            {"name": "jwt-signing-key", "services": ["api-gateway", "auth-service"], "provider": "hashicorp_vault"},
            {"name": "stripe-api-key", "services": ["payment-service"], "provider": "hashicorp_vault"},
            {"name": "sendgrid-api-key", "services": ["notification-service"], "provider": "hashicorp_vault"},
            {"name": "db-credentials", "services": ["user-service", "order-service", "payment-service"], "provider": "hashicorp_vault"},
            {"name": "kafka-credentials", "services": ["order-service", "inventory-service", "notification-service"], "provider": "hashicorp_vault"},
            {"name": "feature-flags", "services": ["api-gateway"], "provider": "consul"},
        ]

        # Service calls (who calls whom - matching topology.py)
        self.service_calls = [
            ("api-gateway", "auth-service"),
            ("api-gateway", "user-service"),
            ("api-gateway", "cart-service"),
            ("api-gateway", "order-service"),
            ("api-gateway", "product-service"),
            ("api-gateway", "search-service"),
            ("order-service", "payment-service"),
            ("order-service", "inventory-service"),
            ("order-service", "notification-service"),
            ("cart-service", "product-service"),
            ("cart-service", "inventory-service"),
            ("product-service", "recommendation-service"),
        ]

        # Tables (linked to databases)
        self.tables = [
            {"name": "users", "database": "postgres-users", "owner": "user-service"},
            {"name": "sessions", "database": "postgres-users", "owner": "auth-service"},
            {"name": "orders", "database": "postgres-orders", "owner": "order-service"},
            {"name": "order_items", "database": "postgres-orders", "owner": "order-service"},
            {"name": "transactions", "database": "postgres-orders", "owner": "payment-service"},
            {"name": "refunds", "database": "postgres-orders", "owner": "payment-service"},
            {"name": "stock_levels", "database": "postgres-inventory", "owner": "inventory-service"},
        ]

    # --- Getters for random data ---

    def get_random_node(self) -> Dict:
        """Get a random node."""
        return random.choice(self.nodes)

    def get_random_service(self) -> str:
        """Get a random service name."""
        return random.choice(self.services)

    def get_random_pod(self) -> Dict:
        """Get a random pod."""
        return random.choice(self.pods)

    def get_random_deployment(self) -> Dict:
        """Get a random deployment."""
        return random.choice(self.deployments)

    def get_random_database(self) -> Dict:
        """Get a random database."""
        return random.choice(self.databases)

    def get_random_cache(self) -> Dict:
        """Get a random cache."""
        return random.choice(self.caches)

    def get_random_queue(self) -> Dict:
        """Get a random queue."""
        return random.choice(self.queues)

    def get_random_external_api(self) -> Dict:
        """Get a random external API."""
        return random.choice(self.external_apis)

    def get_random_endpoint(self) -> Dict:
        """Get a random endpoint."""
        return random.choice(self.endpoints)

    def get_random_team(self) -> str:
        """Get a random team."""
        return random.choice(self.teams)

    # --- Getters for relationships ---

    def get_pods_for_service(self, service_name: str) -> List[Dict]:
        """Get all pods for a service."""
        return [p for p in self.pods if p["service"] == service_name]

    def get_pods_for_node(self, node_name: str) -> List[Dict]:
        """Get all pods running on a node."""
        return [p for p in self.pods if p["node"] == node_name]

    def get_database_for_service(self, service_name: str) -> Optional[Dict]:
        """Get the database owned by a service."""
        for db in self.databases:
            if db["owner"] == service_name:
                return db
        return None

    def get_cache_for_service(self, service_name: str) -> Optional[Dict]:
        """Get the cache used by a service."""
        for cache in self.caches:
            if cache["owner"] == service_name:
                return cache
        return None

    def get_team_for_service(self, service_name: str) -> str:
        """Get the team that owns a service."""
        return self.team_ownerships.get(service_name, "platform")

    def get_publishers_for_queue(self, queue_name: str) -> List[str]:
        """Get services that publish to a queue."""
        for q in self.queues:
            if q["name"] == queue_name:
                return q["publishers"]
        return []

    def get_consumers_for_queue(self, queue_name: str) -> List[str]:
        """Get services that consume from a queue."""
        for q in self.queues:
            if q["name"] == queue_name:
                return q["consumers"]
        return []

    def get_endpoints_for_service(self, service_name: str) -> List[Dict]:
        """Get all endpoints for a service."""
        return [e for e in self.endpoints if e["service"] == service_name]

    def get_external_api_for_service(self, service_name: str) -> Optional[Dict]:
        """Get external API used by a service."""
        for api in self.external_apis:
            if api["owner"] == service_name:
                return api
        return None

    # --- NEW: Getters for additional entities ---

    def get_random_table(self) -> Dict:
        """Get a random table."""
        return random.choice(self.tables)

    def get_random_library(self) -> Dict:
        """Get a random library."""
        return random.choice(self.libraries)

    def get_random_slo(self) -> Dict:
        """Get a random SLO config."""
        return random.choice(self.slo_configs)

    def get_random_secret(self) -> Dict:
        """Get a random secret."""
        return random.choice(self.secrets)

    def get_calls_for_service(self, service_name: str) -> List[str]:
        """Get services that this service calls."""
        return [target for src, target in self.service_calls if src == service_name]

    def get_libraries_for_service(self, service_name: str) -> List[str]:
        """Get libraries used by a service."""
        return [
            lib["name"] for lib in self.libraries
            if service_name in lib["services"]
        ]

    def get_slos_for_service(self, service_name: str) -> List[str]:
        """Get SLOs for a service."""
        return [
            slo["name"] for slo in self.slo_configs
            if slo["service"] == service_name
        ]

    def get_secrets_for_service(self, service_name: str) -> List[str]:
        """Get secrets used by a service."""
        return [
            secret["name"] for secret in self.secrets
            if service_name in secret["services"]
        ]

    def get_tables_for_service(self, service_name: str) -> List[Dict]:
        """Get tables owned by a service."""
        return [t for t in self.tables if t["owner"] == service_name]

    def get_table_for_database(self, db_name: str) -> List[Dict]:
        """Get tables in a database."""
        return [t for t in self.tables if t["database"] == db_name]

    # --- Statistics ---

    def get_stats(self) -> Dict:
        """Get statistics about the shared state."""
        return {
            "services": len(self.services),
            "nodes": len(self.nodes),
            "pods": len(self.pods),
            "deployments": len(self.deployments),
            "databases": len(self.databases),
            "caches": len(self.caches),
            "queues": len(self.queues),
            "external_apis": len(self.external_apis),
            "endpoints": len(self.endpoints),
            "teams": len(self.teams),
            "tables": len(self.tables),
            "libraries": len(self.libraries),
            "slo_configs": len(self.slo_configs),
            "secrets": len(self.secrets),
            "service_calls": len(self.service_calls),
        }
