"""Built-in automatic edge creation rules.

These rules define how edges are automatically created between nodes
based on their field values. For example, a Pod with a 'node_name' field
will automatically get a 'deployedon' edge to the Node with matching 'name'.

All 11 edge types are covered:
- deployedon, ownedby, calls, reads, writes
- publishesto, consumesfrom, dependson
- authenticatesvia, ratelimitedby, fails_over_to
"""

from __future__ import annotations

from typing import List

from app.models.mapper.mapping import AutoEdgeRule


BUILTIN_EDGE_RULES: List[AutoEdgeRule] = [
    # ========== DEPLOYEDON (resource placement) ==========
    # Pod → Node (which node the pod runs on)
    AutoEdgeRule(
        id="pod-to-node",
        source_type="Pod",
        source_field="node_name",
        target_type="Node",
        target_field="name",
        edge_type="deployedon",
    ),
    # Service → Deployment (via deployment_name)
    AutoEdgeRule(
        id="service-to-deployment",
        source_type="Service",
        source_field="deployment_name",
        target_type="Deployment",
        target_field="name",
        edge_type="deployedon",
    ),
    # Deployment → RegionCluster (which cluster)
    AutoEdgeRule(
        id="deployment-to-cluster",
        source_type="Deployment",
        source_field="cluster_id",
        target_type="RegionCluster",
        target_field="cluster_id",
        edge_type="deployedon",
    ),
    # Pod → Deployment (which deployment owns this pod)
    AutoEdgeRule(
        id="pod-to-deployment",
        source_type="Pod",
        source_field="deployment_name",
        target_type="Deployment",
        target_field="name",
        edge_type="deployedon",
    ),

    # ========== OWNEDBY (resource ownership) ==========
    # Service → TeamOwner
    AutoEdgeRule(
        id="service-to-team",
        source_type="Service",
        source_field="team",
        target_type="TeamOwner",
        target_field="name",
        edge_type="ownedby",
    ),
    # Database → TeamOwner
    AutoEdgeRule(
        id="database-to-team",
        source_type="Database",
        source_field="team",
        target_type="TeamOwner",
        target_field="name",
        edge_type="ownedby",
    ),
    # QueueTopic → TeamOwner
    AutoEdgeRule(
        id="queue-to-team",
        source_type="QueueTopic",
        source_field="team",
        target_type="TeamOwner",
        target_field="name",
        edge_type="ownedby",
    ),
    # Cache → TeamOwner
    AutoEdgeRule(
        id="cache-to-team",
        source_type="Cache",
        source_field="team",
        target_type="TeamOwner",
        target_field="name",
        edge_type="ownedby",
    ),
    # Endpoint → Service (service owns endpoint)
    AutoEdgeRule(
        id="endpoint-to-service",
        source_type="Endpoint",
        source_field="service_name",
        target_type="Service",
        target_field="name",
        edge_type="ownedby",
    ),

    # ========== CALLS (HTTP/gRPC calls) ==========
    # Service → Service (via calls_services - array of service names)
    AutoEdgeRule(
        id="service-calls-service",
        source_type="Service",
        source_field="calls_services",
        target_type="Service",
        target_field="name",
        edge_type="calls",
    ),
    # Service → ExternalAPI
    AutoEdgeRule(
        id="service-calls-external",
        source_type="Service",
        source_field="external_apis",
        target_type="ExternalAPI",
        target_field="name",
        edge_type="calls",
    ),
    # Service → Endpoint
    AutoEdgeRule(
        id="service-calls-endpoint",
        source_type="Service",
        source_field="calls_endpoints",
        target_type="Endpoint",
        target_field="path",
        edge_type="calls",
    ),

    # ========== READS (data reading) ==========
    # Service → Database
    AutoEdgeRule(
        id="service-reads-database",
        source_type="Service",
        source_field="reads_databases",
        target_type="Database",
        target_field="name",
        edge_type="reads",
    ),
    # Service → Table
    AutoEdgeRule(
        id="service-reads-table",
        source_type="Service",
        source_field="reads_tables",
        target_type="Table",
        target_field="name",
        edge_type="reads",
    ),
    # Service → Cache
    AutoEdgeRule(
        id="service-reads-cache",
        source_type="Service",
        source_field="reads_caches",
        target_type="Cache",
        target_field="name",
        edge_type="reads",
    ),

    # ========== WRITES (data writing) ==========
    # Service → Database
    AutoEdgeRule(
        id="service-writes-database",
        source_type="Service",
        source_field="writes_databases",
        target_type="Database",
        target_field="name",
        edge_type="writes",
    ),
    # Service → Table
    AutoEdgeRule(
        id="service-writes-table",
        source_type="Service",
        source_field="writes_tables",
        target_type="Table",
        target_field="name",
        edge_type="writes",
    ),
    # Service → Cache
    AutoEdgeRule(
        id="service-writes-cache",
        source_type="Service",
        source_field="writes_caches",
        target_type="Cache",
        target_field="name",
        edge_type="writes",
    ),

    # ========== PUBISHESTO (message publishing) ==========
    # Service → QueueTopic
    AutoEdgeRule(
        id="service-publishes-queue",
        source_type="Service",
        source_field="publishes_to",
        target_type="QueueTopic",
        target_field="name",
        edge_type="publishesto",
    ),

    # ========== CONSUMESFROM (message consumption) ==========
    # Service → QueueTopic
    AutoEdgeRule(
        id="service-consumes-queue",
        source_type="Service",
        source_field="consumes_from",
        target_type="QueueTopic",
        target_field="name",
        edge_type="consumesfrom",
    ),

    # ========== DEPENDSON (infrastructure dependencies) ==========
    # Service → Database
    AutoEdgeRule(
        id="service-depends-database",
        source_type="Service",
        source_field="depends_on_databases",
        target_type="Database",
        target_field="name",
        edge_type="dependson",
    ),
    # Service → Cache
    AutoEdgeRule(
        id="service-depends-cache",
        source_type="Service",
        source_field="depends_on_caches",
        target_type="Cache",
        target_field="name",
        edge_type="dependson",
    ),
    # Service → Library
    AutoEdgeRule(
        id="service-depends-library",
        source_type="Service",
        source_field="libraries",
        target_type="Library",
        target_field="name",
        edge_type="dependson",
    ),

    # ========== AUTHENTICATESVIA (authentication) ==========
    # Service → SecretConfig
    AutoEdgeRule(
        id="service-auth-secret",
        source_type="Service",
        source_field="auth_secret",
        target_type="SecretConfig",
        target_field="name",
        edge_type="authenticatesvia",
    ),
    # Pod → SecretConfig (service account)
    AutoEdgeRule(
        id="pod-auth-secret",
        source_type="Pod",
        source_field="service_account",
        target_type="SecretConfig",
        target_field="name",
        edge_type="authenticatesvia",
    ),

    # ========== RATELIMITEDBY (rate limiting) ==========
    # Service → SecretConfig
    AutoEdgeRule(
        id="service-ratelimit-secret",
        source_type="Service",
        source_field="rate_limit_config",
        target_type="SecretConfig",
        target_field="name",
        edge_type="ratelimitedby",
    ),
    # Endpoint → SecretConfig
    AutoEdgeRule(
        id="endpoint-ratelimit-secret",
        source_type="Endpoint",
        source_field="rate_limit_config",
        target_type="SecretConfig",
        target_field="name",
        edge_type="ratelimitedby",
    ),

    # ========== FAILS_OVER_TO (failover) ==========
    # Service → Service (backup service)
    AutoEdgeRule(
        id="service-failover",
        source_type="Service",
        source_field="failover_service",
        target_type="Service",
        target_field="name",
        edge_type="fails_over_to",
    ),
]


def get_rules_for_source_type(source_type: str) -> List[AutoEdgeRule]:
    """Get all rules that apply to a specific source node type."""
    return [rule for rule in BUILTIN_EDGE_RULES if rule.source_type == source_type]


def get_rules_for_edge_type(edge_type: str) -> List[AutoEdgeRule]:
    """Get all rules that create a specific edge type."""
    return [rule for rule in BUILTIN_EDGE_RULES if rule.edge_type == edge_type]
