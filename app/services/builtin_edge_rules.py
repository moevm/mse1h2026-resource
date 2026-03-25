from __future__ import annotations

from typing import List

from app.models.mapper.mapping import AutoEdgeRule


BUILTIN_EDGE_RULES: List[AutoEdgeRule] = [
    AutoEdgeRule(
        id="pod-to-node",
        source_type="Pod",
        source_field="node_name",
        target_type="Node",
        target_field="name",
        edge_type="deployedon",
    ),
    AutoEdgeRule(
        id="service-to-deployment",
        source_type="Service",
        source_field="deployment_name",
        target_type="Deployment",
        target_field="name",
        edge_type="deployedon",
    ),
    AutoEdgeRule(
        id="deployment-to-cluster",
        source_type="Deployment",
        source_field="cluster_id",
        target_type="RegionCluster",
        target_field="cluster_id",
        edge_type="deployedon",
    ),
    AutoEdgeRule(
        id="pod-to-deployment",
        source_type="Pod",
        source_field="deployment_name",
        target_type="Deployment",
        target_field="name",
        edge_type="deployedon",
    ),

    AutoEdgeRule(
        id="service-to-team",
        source_type="Service",
        source_field="team",
        target_type="TeamOwner",
        target_field="name",
        edge_type="ownedby",
    ),
    AutoEdgeRule(
        id="database-to-team",
        source_type="Database",
        source_field="team",
        target_type="TeamOwner",
        target_field="name",
        edge_type="ownedby",
    ),
    AutoEdgeRule(
        id="queue-to-team",
        source_type="QueueTopic",
        source_field="team",
        target_type="TeamOwner",
        target_field="name",
        edge_type="ownedby",
    ),
    AutoEdgeRule(
        id="cache-to-team",
        source_type="Cache",
        source_field="team",
        target_type="TeamOwner",
        target_field="name",
        edge_type="ownedby",
    ),
    AutoEdgeRule(
        id="endpoint-to-service",
        source_type="Endpoint",
        source_field="service_name",
        target_type="Service",
        target_field="name",
        edge_type="ownedby",
    ),

    AutoEdgeRule(
        id="service-calls-service",
        source_type="Service",
        source_field="calls_services",
        target_type="Service",
        target_field="name",
        edge_type="calls",
    ),
    AutoEdgeRule(
        id="service-calls-external",
        source_type="Service",
        source_field="external_apis",
        target_type="ExternalAPI",
        target_field="name",
        edge_type="calls",
    ),
    AutoEdgeRule(
        id="service-calls-endpoint",
        source_type="Service",
        source_field="calls_endpoints",
        target_type="Endpoint",
        target_field="path",
        edge_type="calls",
    ),

    AutoEdgeRule(
        id="service-reads-database",
        source_type="Service",
        source_field="reads_databases",
        target_type="Database",
        target_field="name",
        edge_type="reads",
    ),
    AutoEdgeRule(
        id="service-reads-table",
        source_type="Service",
        source_field="reads_tables",
        target_type="Table",
        target_field="name",
        edge_type="reads",
    ),
    AutoEdgeRule(
        id="service-reads-cache",
        source_type="Service",
        source_field="reads_caches",
        target_type="Cache",
        target_field="name",
        edge_type="reads",
    ),

    AutoEdgeRule(
        id="service-writes-database",
        source_type="Service",
        source_field="writes_databases",
        target_type="Database",
        target_field="name",
        edge_type="writes",
    ),
    AutoEdgeRule(
        id="service-writes-table",
        source_type="Service",
        source_field="writes_tables",
        target_type="Table",
        target_field="name",
        edge_type="writes",
    ),
    AutoEdgeRule(
        id="service-writes-cache",
        source_type="Service",
        source_field="writes_caches",
        target_type="Cache",
        target_field="name",
        edge_type="writes",
    ),

    AutoEdgeRule(
        id="service-publishes-queue",
        source_type="Service",
        source_field="publishes_to",
        target_type="QueueTopic",
        target_field="name",
        edge_type="publishesto",
    ),

    AutoEdgeRule(
        id="service-consumes-queue",
        source_type="Service",
        source_field="consumes_from",
        target_type="QueueTopic",
        target_field="name",
        edge_type="consumesfrom",
    ),

    AutoEdgeRule(
        id="service-depends-database",
        source_type="Service",
        source_field="depends_on_databases",
        target_type="Database",
        target_field="name",
        edge_type="dependson",
    ),
    AutoEdgeRule(
        id="service-depends-cache",
        source_type="Service",
        source_field="depends_on_caches",
        target_type="Cache",
        target_field="name",
        edge_type="dependson",
    ),
    AutoEdgeRule(
        id="service-depends-library",
        source_type="Service",
        source_field="libraries",
        target_type="Library",
        target_field="name",
        edge_type="dependson",
    ),

    AutoEdgeRule(
        id="service-auth-secret",
        source_type="Service",
        source_field="auth_secret",
        target_type="SecretConfig",
        target_field="name",
        edge_type="authenticatesvia",
    ),
    AutoEdgeRule(
        id="pod-auth-secret",
        source_type="Pod",
        source_field="service_account",
        target_type="SecretConfig",
        target_field="name",
        edge_type="authenticatesvia",
    ),

    AutoEdgeRule(
        id="service-ratelimit-secret",
        source_type="Service",
        source_field="rate_limit_config",
        target_type="SecretConfig",
        target_field="name",
        edge_type="ratelimitedby",
    ),
    AutoEdgeRule(
        id="endpoint-ratelimit-secret",
        source_type="Endpoint",
        source_field="rate_limit_config",
        target_type="SecretConfig",
        target_field="name",
        edge_type="ratelimitedby",
    ),

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
    return [rule for rule in BUILTIN_EDGE_RULES if rule.source_type == source_type]


def get_rules_for_edge_type(edge_type: str) -> List[AutoEdgeRule]:
    return [rule for rule in BUILTIN_EDGE_RULES if rule.edge_type == edge_type]
