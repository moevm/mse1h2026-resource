from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SharedState:
    nodes: List[Dict] = field(default_factory=list)
    cluster: Dict = field(default_factory=dict)

    services: List[str] = field(default_factory=list)
    pods: List[Dict] = field(default_factory=list)
    deployments: List[Dict] = field(default_factory=list)

    databases: List[Dict] = field(default_factory=list)
    caches: List[Dict] = field(default_factory=list)
    queues: List[Dict] = field(default_factory=list)

    external_apis: List[Dict] = field(default_factory=list)
    endpoints: List[Dict] = field(default_factory=list)

    teams: List[str] = field(default_factory=list)
    team_ownerships: Dict[str, str] = field(default_factory=dict)

    tables: List[Dict] = field(default_factory=list)
    libraries: List[Dict] = field(default_factory=list)
    slo_configs: List[Dict] = field(default_factory=list)
    secrets: List[Dict] = field(default_factory=list)
    service_calls: List[tuple] = field(default_factory=list)

    def __post_init__(self):
        self._init_infrastructure()
        self._init_services()
        self._init_data_layer()
        self._init_external()
        self._init_org()

    def _init_infrastructure(self):
        self.cluster = {
            "name": "prod-ecommerce",
            "region": "eu-central-1",
            "provider": "aws",
        }

        self.nodes = [
            {"name": "ip-10-0-1-101", "zone": "eu-central-1a", "instance_type": "m6i.2xlarge", "capacity_cpu": "8", "capacity_memory": "32Gi"},
            {"name": "ip-10-0-2-102", "zone": "eu-central-1b", "instance_type": "m6i.2xlarge", "capacity_cpu": "8", "capacity_memory": "32Gi"},
            {"name": "ip-10-0-3-103", "zone": "eu-central-1c", "instance_type": "m6i.2xlarge", "capacity_cpu": "8", "capacity_memory": "32Gi"},
            {"name": "ip-10-0-1-104", "zone": "eu-central-1a", "instance_type": "c6i.xlarge", "capacity_cpu": "4", "capacity_memory": "8Gi"},
            {"name": "ip-10-0-2-105", "zone": "eu-central-1b", "instance_type": "c6i.xlarge", "capacity_cpu": "4", "capacity_memory": "8Gi"},
        ]

    def _init_services(self):
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

        self.deployments = [
            {
                "name": service,
                "replicas": random.randint(2, 4),
                "team": self.team_ownerships.get(service, "platform"),
            }
            for service in self.services
        ]

        self._generate_pods()

    def _generate_pods(self):
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
        self.databases = [
            {
                "name": "Users DB",
                "type": "postgresql",
                "engine_version": "16.2",
                "owner": "user-service",
                "tables": ["users", "sessions"],
            },
            {
                "name": "Orders DB",
                "type": "postgresql",
                "engine_version": "16.2",
                "owner": "order-service",
                "tables": ["orders", "order_items"],
            },
            {
                "name": "Payments DB",
                "type": "postgresql",
                "engine_version": "16.2",
                "owner": "payment-service",
                "tables": ["transactions", "refunds"],
            },
            {
                "name": "Inventory DB",
                "type": "postgresql",
                "engine_version": "16.2",
                "owner": "inventory-service",
                "tables": ["stock_levels"],
            },
            {
                "name": "Products DB",
                "type": "mongodb",
                "engine_version": "7.0.5",
                "owner": "product-service",
                "collections": ["products", "categories"],
            },
        ]

        self.caches = [
            {
                "name": "Session Cache",
                "owner": "auth-service",
                "type": "redis",
                "cluster_size": 3,
            },
            {
                "name": "Product Cache",
                "owner": "product-service",
                "type": "redis",
                "cluster_size": 5,
            },
            {
                "name": "Cart Cache",
                "owner": "cart-service",
                "type": "redis",
                "cluster_size": 3,
            },
            {
                "name": "Rate Limit Store",
                "owner": "api-gateway",
                "type": "redis",
                "cluster_size": 2,
            },
            {
                "name": "Search Cache",
                "owner": "search-service",
                "type": "redis",
                "cluster_size": 3,
            },
        ]

        self.queues = [
            {
                "name": "prod.orders.events",
                "type": "kafka",
                "partitions": 12,
                "publishers": ["order-service", "cart-service"],
                "consumers": ["inventory-service", "notification-service", "payment-service", "recommendation-service"],
            },
            {
                "name": "prod.payments.events",
                "type": "kafka",
                "partitions": 6,
                "publishers": ["payment-service"],
                "consumers": ["notification-service", "order-service"],
            },
            {
                "name": "prod.notifications.events",
                "type": "kafka",
                "partitions": 6,
                "publishers": ["notification-service"],
                "consumers": [],
            },
            {
                "name": "prod.inventory.events",
                "type": "kafka",
                "partitions": 8,
                "publishers": ["inventory-service"],
                "consumers": [],
            },
        ]

    def _init_external(self):
        self.external_apis = [
            {"name": "Stripe API", "owner": "payment-service", "type": "payment"},
            {"name": "SendGrid API", "owner": "notification-service", "type": "email"},
            {"name": "Twilio API", "owner": "notification-service", "type": "sms"},
            {"name": "Cloudflare CDN", "owner": "api-gateway", "type": "cdn"},
            {"name": "Elastic Cloud", "owner": "search-service", "type": "search"},
        ]

        self.endpoints = [
            {"path": "/api/v1/auth/login", "service": "auth-service", "method": "POST"},
            {"path": "/api/v1/users/me", "service": "user-service", "method": "GET"},
            {"path": "/api/v1/orders", "service": "order-service", "method": "POST"},
            {"path": "/api/v1/orders", "service": "order-service", "method": "GET"},
            {"path": "/api/v1/products", "service": "product-service", "method": "GET"},
            {"path": "/api/v1/cart", "service": "cart-service", "method": "POST"},
            {"path": "/api/v1/payments", "service": "payment-service", "method": "POST"},
            {"path": "/api/v1/search", "service": "search-service", "method": "GET"},
        ]

    def _init_org(self):
        self.teams = [
            "Platform Engineering",
            "Payments Team",
            "Identity & Access",
            "Order Management",
            "Product Catalog",
            "Search & Discovery",
        ]

        self.team_ownerships = {
            "api-gateway": "Platform Engineering",
            "auth-service": "Identity & Access",
            "user-service": "Identity & Access",
            "order-service": "Order Management",
            "cart-service": "Order Management",
            "inventory-service": "Order Management",
            "payment-service": "Payments Team",
            "notification-service": "Platform Engineering",
            "product-service": "Product Catalog",
            "search-service": "Search & Discovery",
            "recommendation-service": "Search & Discovery",
        }

        self.libraries = [
            {"name": "gRPC (Go)", "language": "go", "services": ["api-gateway"]},
            {"name": "SQLAlchemy", "language": "python", "services": ["user-service", "search-service"]},
            {"name": "kafka-go", "language": "go", "services": ["order-service"]},
            {"name": "Spring Boot", "language": "java", "services": ["order-service", "payment-service"]},
            {"name": "Express.js", "language": "nodejs", "services": ["cart-service", "product-service"]},
            {"name": "Pydantic", "language": "python", "services": ["user-service", "search-service", "notification-service", "recommendation-service"]},
        ]

        self.slo_configs = [
            {"name": "API Gateway  Availability", "service": "api-gateway", "metric": "availability", "target": 99.95},
            {"name": "API Gateway  Latency P99", "service": "api-gateway", "metric": "latency_p99", "target": 200.0},
            {"name": "Payment Service  Availability", "service": "payment-service", "metric": "availability", "target": 99.99},
            {"name": "Payment Service  Latency P99", "service": "payment-service", "metric": "latency_p99", "target": 500.0},
            {"name": "Order Service  Latency P99", "service": "order-service", "metric": "latency_p99", "target": 300.0},
            {"name": "Search  Latency P99", "service": "search-service", "metric": "latency_p99", "target": 150.0},
        ]

        self.secrets = [
            {"name": "JWT Signing Key", "services": ["api-gateway", "auth-service"], "provider": "hashicorp_vault"},
            {"name": "Stripe API Key", "services": ["payment-service"], "provider": "hashicorp_vault"},
            {"name": "SendGrid API Key", "services": ["notification-service"], "provider": "hashicorp_vault"},
            {"name": "Database Credentials", "services": ["user-service", "order-service", "payment-service"], "provider": "hashicorp_vault"},
            {"name": "Kafka SASL Credentials", "services": ["order-service", "inventory-service", "notification-service"], "provider": "hashicorp_vault"},
            {"name": "Feature Flags", "services": ["api-gateway", "product-service", "recommendation-service"], "provider": "consul"},
        ]

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

        self.failover_services = {
            "payment-service": "order-service",
            "recommendation-service": "search-service",
        }

        self.tables = [
            {"name": "public.users", "database": "Users DB", "owner": "user-service"},
            {"name": "public.sessions", "database": "Users DB", "owner": "auth-service"},
            {"name": "public.orders", "database": "Orders DB", "owner": "order-service"},
            {"name": "public.order_items", "database": "Orders DB", "owner": "order-service"},
            {"name": "public.transactions", "database": "Payments DB", "owner": "payment-service"},
            {"name": "public.refunds", "database": "Payments DB", "owner": "payment-service"},
            {"name": "public.stock_levels", "database": "Inventory DB", "owner": "inventory-service"},
        ]


    def get_random_node(self) -> Dict:
        return random.choice(self.nodes)

    def get_random_service(self) -> str:
        return random.choice(self.services)

    def get_random_pod(self) -> Dict:
        return random.choice(self.pods)

    def get_random_deployment(self) -> Dict:
        return random.choice(self.deployments)

    def get_random_database(self) -> Dict:
        return random.choice(self.databases)

    def get_random_cache(self) -> Dict:
        return random.choice(self.caches)

    def get_random_queue(self) -> Dict:
        return random.choice(self.queues)

    def get_random_external_api(self) -> Dict:
        return random.choice(self.external_apis)

    def get_random_endpoint(self) -> Dict:
        return random.choice(self.endpoints)

    def get_random_team(self) -> str:
        return random.choice(self.teams)


    def get_pods_for_service(self, service_name: str) -> List[Dict]:
        return [p for p in self.pods if p["service"] == service_name]

    def get_pods_for_node(self, node_name: str) -> List[Dict]:
        return [p for p in self.pods if p["node"] == node_name]

    def get_database_for_service(self, service_name: str) -> Optional[Dict]:
        for db in self.databases:
            if db["owner"] == service_name:
                return db
        return None

    def get_cache_for_service(self, service_name: str) -> Optional[Dict]:
        for cache in self.caches:
            if cache["owner"] == service_name:
                return cache
        return None

    def get_team_for_service(self, service_name: str) -> str:
        return self.team_ownerships.get(service_name, "platform")

    def get_publishers_for_queue(self, queue_name: str) -> List[str]:
        for q in self.queues:
            if q["name"] == queue_name:
                return q["publishers"]
        return []

    def get_consumers_for_queue(self, queue_name: str) -> List[str]:
        for q in self.queues:
            if q["name"] == queue_name:
                return q["consumers"]
        return []

    def get_endpoints_for_service(self, service_name: str) -> List[Dict]:
        return [e for e in self.endpoints if e["service"] == service_name]

    def get_external_api_for_service(self, service_name: str) -> Optional[Dict]:
        for api in self.external_apis:
            if api["owner"] == service_name:
                return api
        if self.external_apis:
            return random.choice(self.external_apis)
        return None


    def get_random_table(self) -> Dict:
        return random.choice(self.tables)

    def get_random_library(self) -> Dict:
        return random.choice(self.libraries)

    def get_random_slo(self) -> Dict:
        return random.choice(self.slo_configs)

    def get_random_secret(self) -> Dict:
        return random.choice(self.secrets)

    def get_calls_for_service(self, service_name: str) -> List[str]:
        return [target for src, target in self.service_calls if src == service_name]

    def get_libraries_for_service(self, service_name: str) -> List[str]:
        return [
            lib["name"] for lib in self.libraries
            if service_name in lib["services"]
        ]

    def get_slos_for_service(self, service_name: str) -> List[str]:
        return [
            slo["name"] for slo in self.slo_configs
            if slo["service"] == service_name
        ]

    def get_secrets_for_service(self, service_name: str) -> List[str]:
        return [
            secret["name"] for secret in self.secrets
            if service_name in secret["services"]
        ]

    def get_tables_for_service(self, service_name: str) -> List[Dict]:
        return [t for t in self.tables if t["owner"] == service_name]

    def get_failover_for_service(self, service_name: str) -> Optional[str]:
        return self.failover_services.get(service_name)

    def get_table_for_database(self, db_name: str) -> List[Dict]:
        return [t for t in self.tables if t["database"] == db_name]


    def get_stats(self) -> Dict:
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
