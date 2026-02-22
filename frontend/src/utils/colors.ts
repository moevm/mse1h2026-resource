const NODE_COLORS: Record<string, string> = {
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
};

const EDGE_COLORS: Record<string, string> = {
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
};

export function getNodeColor(type: string): string {
    return NODE_COLORS[type] ?? "#64748b";
}

export function getEdgeColor(type: string): string {
    return EDGE_COLORS[type] ?? "#475569";
}

const NODE_SHAPES: Record<string, string> = {
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
};

export function getNodeShape(type: string): string {
    return NODE_SHAPES[type] ?? "ellipse";
}

export function getStatusColor(status?: string): string {
    switch (status) {
        case "active":
            return "#22c55e";
        case "degraded":
            return "#f59e0b";
        case "down":
        case "error":
            return "#ef4444";
        default:
            return "#64748b";
    }
}
