export const NodeType = {
    Service: "Service",
    Endpoint: "Endpoint",
    Deployment: "Deployment",
    Pod: "Pod",
    Node: "Node",
    Database: "Database",
    Table: "Table",
    QueueTopic: "QueueTopic",
    Cache: "Cache",
    ExternalAPI: "ExternalAPI",
    SecretConfig: "SecretConfig",
    Library: "Library",
    TeamOwner: "TeamOwner",
    SLASLO: "SLASLO",
    RegionCluster: "RegionCluster",
} as const;

export type NodeTypeValue = (typeof NodeType)[keyof typeof NodeType];

export const EdgeType = {
    Calls: "calls",
    PublishesTo: "publishesto",
    ConsumesFrom: "consumesfrom",
    Reads: "reads",
    Writes: "writes",
    DependsOn: "dependson",
    DeployedOn: "deployedon",
    OwnedBy: "ownedby",
    AuthenticatesVia: "authenticatesvia",
    RateLimitedBy: "ratelimitedby",
    FailsOverTo: "fails_over_to",
} as const;

export type EdgeTypeValue = (typeof EdgeType)[keyof typeof EdgeType];

export const LayoutAlgorithm = {
    Spring: "spring",
    KamadaKawai: "kamada_kawai",
    Circular: "circular",
    Shell: "shell",
} as const;

export type LayoutAlgorithmValue = (typeof LayoutAlgorithm)[keyof typeof LayoutAlgorithm];

export const ImpactDirection = {
    Upstream: "upstream",
    Downstream: "downstream",
    Both: "both",
} as const;

export type ImpactDirectionValue = (typeof ImpactDirection)[keyof typeof ImpactDirection];
