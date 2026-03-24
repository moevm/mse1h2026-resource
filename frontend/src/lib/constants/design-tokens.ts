// Централизованные design tokens для всего приложения

export const NODE_COLORS = {
    Service: "#3b82f6",
    Endpoint: "#8b5cf6",
    Deployment: "#06b6d4",
    Pod: "#14b8a6",
    Node: "#64748b",
    Database: "#f59e0b",
    Table: "#d97706",
    QueueTopic: "#ec4899",
    Cache: "#ef4444",
    ExternalAPI: "#a855f7",
    SecretConfig: "#6366f1",
    Library: "#84cc16",
    TeamOwner: "#22c55e",
    SLASLO: "#f97316",
    RegionCluster: "#0ea5e9",
} as const;

export const EDGE_COLORS = {
    calls: "#60a5fa",
    publishesto: "#f472b6",
    consumesfrom: "#e879f9",
    reads: "#fbbf24",
    writes: "#fb923c",
    dependson: "#94a3b8",
    deployedon: "#22d3ee",
    ownedby: "#4ade80",
    authenticatesvia: "#818cf8",
    ratelimitedby: "#f87171",
    fails_over_to: "#ef4444",
} as const;

export const NODE_SHAPES = {
    Service: "roundrectangle",
    Endpoint: "diamond",
    Deployment: "hexagon",
    Pod: "ellipse",
    Node: "rectangle",
    Database: "barrel",
    Table: "rectangle",
    QueueTopic: "pentagon",
    Cache: "octagon",
    ExternalAPI: "star",
    SecretConfig: "vee",
    Library: "round-triangle",
    TeamOwner: "ellipse",
    SLASLO: "tag",
    RegionCluster: "round-rectangle",
} as const;

export const STATUS_COLORS = {
    active: "#22c55e",
    degraded: "#f59e0b",
    down: "#ef4444",
    error: "#ef4444",
    unknown: "#64748b",
} as const;

export type NodeType = keyof typeof NODE_COLORS;
export type EdgeType = keyof typeof EDGE_COLORS;
export type NodeStatus = keyof typeof STATUS_COLORS;
