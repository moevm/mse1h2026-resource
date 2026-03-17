"""
Mapping configuration for terraform-state source type.

Maps Terraform state resources to Database, Cache, QueueTopic, SecretConfig, Table nodes.
"""

TERRAFORM_STATE_MAPPING = {
    "id": "terraform-mapper-v1",
    "name": "Terraform State Mapper v1.0",
    "source_type": "terraform-state",
    "version": "1.0.0",
    "description": "Maps Terraform state resources to Database/Cache/QueueTopic/SecretConfig/Table nodes",
    "edge_preset_id": "default",
    "field_mappings": [
        # === DATABASE (aws_db_instance) ===
        {
            "id": "db-id",
            "source_path": "instances[0].attributes.identifier",
            "target_field": "id",
            "target_node_type": "Database",
            "transform_type": "template",
            "transform_config": {"template": "urn:database:{value}"},
        },
        {
            "id": "db-name",
            "source_path": "instances[0].attributes.identifier",
            "target_field": "name",
            "target_node_type": "Database",
        },
        {
            "id": "db-engine",
            "source_path": "instances[0].attributes.engine",
            "target_field": "engine",
            "target_node_type": "Database",
        },
        {
            "id": "db-version",
            "source_path": "instances[0].attributes.engine_version",
            "target_field": "version",
            "target_node_type": "Database",
        },
        {
            "id": "db-instance-class",
            "source_path": "instances[0].attributes.instance_class",
            "target_field": "instance_class",
            "target_node_type": "Database",
        },
        {
            "id": "db-storage",
            "source_path": "instances[0].attributes.allocated_storage",
            "target_field": "storage_gb",
            "target_node_type": "Database",
        },
        {
            "id": "db-team",
            "source_path": "instances[0].attributes.tags.Team",
            "target_field": "team",
            "target_node_type": "Database",
            "description": "For ownedby edge to TeamOwner",
        },
        {
            "id": "db-owner",
            "source_path": "instances[0].attributes.tags.Service",
            "target_field": "owner_service",
            "target_node_type": "Database",
            "description": "For reads/writes edges from Service",
        },
        # === CACHE (aws_elasticache_cluster) ===
        {
            "id": "cache-id",
            "source_path": "instances[0].attributes.cluster_id",
            "target_field": "id",
            "target_node_type": "Cache",
            "transform_type": "template",
            "transform_config": {"template": "urn:cache:{value}"},
        },
        {
            "id": "cache-name",
            "source_path": "instances[0].attributes.cluster_id",
            "target_field": "name",
            "target_node_type": "Cache",
        },
        {
            "id": "cache-engine",
            "source_path": "instances[0].attributes.engine",
            "target_field": "engine",
            "target_node_type": "Cache",
        },
        {
            "id": "cache-version",
            "source_path": "instances[0].attributes.engine_version",
            "target_field": "version",
            "target_node_type": "Cache",
        },
        {
            "id": "cache-size",
            "source_path": "instances[0].attributes.num_cache_nodes",
            "target_field": "cluster_size",
            "target_node_type": "Cache",
        },
        {
            "id": "cache-node-type",
            "source_path": "instances[0].attributes.node_type",
            "target_field": "node_type",
            "target_node_type": "Cache",
        },
        {
            "id": "cache-owner",
            "source_path": "instances[0].attributes.tags.Service",
            "target_field": "owner_service",
            "target_node_type": "Cache",
        },
        # === QUEUETOPIC (aws_msk_topic) ===
        {
            "id": "queue-id",
            "source_path": "instances[0].attributes.name",
            "target_field": "id",
            "target_node_type": "QueueTopic",
            "transform_type": "template",
            "transform_config": {"template": "urn:queuetopic:{value}"},
        },
        {
            "id": "queue-name",
            "source_path": "instances[0].attributes.name",
            "target_field": "name",
            "target_node_type": "QueueTopic",
        },
        {
            "id": "queue-partitions",
            "source_path": "instances[0].attributes.partitions",
            "target_field": "partitions",
            "target_node_type": "QueueTopic",
        },
        {
            "id": "queue-replication",
            "source_path": "instances[0].attributes.replication_factor",
            "target_field": "replication_factor",
            "target_node_type": "QueueTopic",
        },
        {
            "id": "queue-publishers",
            "source_path": "instances[0].attributes.tags.Publishers",
            "target_field": "publishers",
            "target_node_type": "QueueTopic",
            "description": "For publishesto edges from Services",
        },
        {
            "id": "queue-consumers",
            "source_path": "instances[0].attributes.tags.Consumers",
            "target_field": "consumers",
            "target_node_type": "QueueTopic",
            "description": "For consumesfrom edges from Services",
        },
        # === SECRETCONFIG (aws_secretsmanager_secret) ===
        {
            "id": "secret-id",
            "source_path": "instances[0].attributes.name",
            "target_field": "id",
            "target_node_type": "SecretConfig",
            "transform_type": "template",
            "transform_config": {"template": "urn:secretconfig:{value}"},
        },
        {
            "id": "secret-name",
            "source_path": "instances[0].attributes.name",
            "target_field": "name",
            "target_node_type": "SecretConfig",
        },
        {
            "id": "secret-description",
            "source_path": "instances[0].attributes.description",
            "target_field": "description",
            "target_node_type": "SecretConfig",
        },
        {
            "id": "secret-services",
            "source_path": "instances[0].attributes.tags.Services",
            "target_field": "services",
            "target_node_type": "SecretConfig",
            "description": "Services that use this secret",
        },
        {
            "id": "secret-provider",
            "source_path": "instances[0].attributes.tags.Provider",
            "target_field": "provider",
            "target_node_type": "SecretConfig",
        },
        # === TABLE ===
        {
            "id": "table-id",
            "source_path": "name",
            "target_field": "id",
            "target_node_type": "Table",
            "transform_type": "template",
            "transform_config": {"template": "urn:table:{value}"},
        },
        {
            "id": "table-name",
            "source_path": "name",
            "target_field": "name",
            "target_node_type": "Table",
        },
        {
            "id": "table-schema",
            "source_path": "schema_name",
            "target_field": "schema_name",
            "target_node_type": "Table",
        },
        {
            "id": "table-database",
            "source_path": "database_name",
            "target_field": "database_ref",
            "target_node_type": "Table",
            "description": "For ownedby edge to Database",
        },
        {
            "id": "table-owner",
            "source_path": "owner_service",
            "target_field": "owner_service",
            "target_node_type": "Table",
            "description": "For writes edge from Service",
        },
        {
            "id": "table-rows",
            "source_path": "row_count",
            "target_field": "row_count",
            "target_node_type": "Table",
        },
        {
            "id": "table-partitioned",
            "source_path": "is_partitioned",
            "target_field": "is_partitioned",
            "target_node_type": "Table",
        },
    ],
    "conditional_rules": [
        {
            "id": "cr-table",
            "condition": "type == 'table'",
            "target_node_type": "Table",
            "priority": 50,
        },
        {
            "id": "cr-database",
            "condition": "type == 'aws_db_instance'",
            "target_node_type": "Database",
            "priority": 40,
        },
        {
            "id": "cr-cache",
            "condition": "type == 'aws_elasticache_cluster'",
            "target_node_type": "Cache",
            "priority": 30,
        },
        {
            "id": "cr-queue",
            "condition": "type == 'aws_msk_topic'",
            "target_node_type": "QueueTopic",
            "priority": 20,
        },
        {
            "id": "cr-secret",
            "condition": "type == 'aws_secretsmanager_secret'",
            "target_node_type": "SecretConfig",
            "priority": 10,
        },
    ],
}
