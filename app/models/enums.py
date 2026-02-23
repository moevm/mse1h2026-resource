from enum import Enum


class NodeType(str, Enum):
    SERVICE = "Service"
    ENDPOINT = "Endpoint"
    DEPLOYMENT = "Deployment"
    POD = "Pod"
    NODE = "Node"
    DATABASE = "Database"
    TABLE = "Table"
    QUEUE_TOPIC = "QueueTopic"
    CACHE = "Cache"
    EXTERNAL_API = "ExternalAPI"
    SECRET_CONFIG = "SecretConfig"
    LIBRARY = "Library"
    TEAM_OWNER = "TeamOwner"
    SLA_SLO = "SLASLO"
    REGION_CLUSTER = "RegionCluster"


class EdgeType(str, Enum):
    CALLS = "calls"
    PUBLISHES_TO = "publishesto"
    CONSUMES_FROM = "consumesfrom"
    READS = "reads"
    WRITES = "writes"
    DEPENDS_ON = "dependson"
    DEPLOYED_ON = "deployedon"
    OWNED_BY = "ownedby"
    AUTHENTICATES_VIA = "authenticatesvia"
    RATE_LIMITED_BY = "ratelimitedby"
    FAILS_OVER_TO = "fails_over_to"
