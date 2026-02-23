import type { StylesheetStyle } from "cytoscape";

type Stylesheet = StylesheetStyle;
import { getNodeColor, getNodeShape, getEdgeColor, getStatusColor } from "./colors";

export function buildCytoscapeStyles(
    hiddenNodeTypes: Set<string>,
    hiddenEdgeTypes: Set<string>,
    filterMode: "ghost" | "exclude" = "ghost",
): Stylesheet[] {
    return [
        {
            selector: "node",
            style: {
                label: "data(label)",
                "text-valign": "bottom",
                "text-halign": "center",
                "font-size": "11px",
                color: "#cbd5e1",
                "text-margin-y": 6,
                "text-outline-color": "#0f172a",
                "text-outline-width": 2,
                "background-color": "#64748b",
                width: 40,
                height: 40,
                "border-width": 2,
                "border-color": "#475569",
                "overlay-padding": 6,
                "transition-property": "background-color, border-color, opacity, width, height",
                "transition-duration": 200,
            } as unknown as Record<string, string | number>,
        },

        ...buildNodeTypeStyles(hiddenNodeTypes, filterMode),

        ...buildNodeStatusStyles(),

        {
            selector: "node[cpu_usage_m]",
            style: {
                width: "mapData(cpu_usage_m, 0, 1000, 35, 65)",
                height: "mapData(cpu_usage_m, 0, 1000, 35, 65)",
            } as unknown as Record<string, string | number>,
        },

        {
            selector: "node:selected",
            style: {
                "border-color": "#f1f5f9",
                "border-width": 3,
                width: 50,
                height: 50,
                "z-index": 999,
            } as unknown as Record<string, string | number>,
        },

        {
            selector: "node.highlighted",
            style: {
                "border-color": "#fbbf24",
                "border-width": 3,
                width: 50,
                height: 50,
            } as unknown as Record<string, string | number>,
        },

        {
            selector: "node.faded",
            style: {
                opacity: 0.15,
            } as unknown as Record<string, string | number>,
        },

        {
            selector: "edge",
            style: {
                label: "data(type)",
                "font-size": "9px",
                color: "#64748b",
                "text-rotation": "autorotate",
                "text-margin-y": -8,
                "text-outline-color": "#0f172a",
                "text-outline-width": 1.5,
                width: 2,
                "line-color": "#475569",
                "target-arrow-color": "#475569",
                "target-arrow-shape": "triangle",
                "curve-style": "bezier",
                opacity: 0.7,
                "arrow-scale": 0.8,
                "transition-property": "line-color, opacity, width",
                "transition-duration": 200,
            } as unknown as Record<string, string | number>,
        },

        ...buildEdgeTypeStyles(hiddenEdgeTypes, filterMode),

        ...buildCallsEdgeMetricStyles(),

        {
            selector: "edge:selected",
            style: {
                width: 3,
                opacity: 1,
                "z-index": 999,
                label: "data(type)",
                "font-size": "10px",
                color: "#f1f5f9",
            } as unknown as Record<string, string | number>,
        },

        {
            selector: "edge.faded",
            style: {
                opacity: 0.08,
            } as unknown as Record<string, string | number>,
        },

        {
            selector: "edge.highlighted",
            style: {
                width: 3,
                opacity: 1,
                "line-color": "#fbbf24",
                "target-arrow-color": "#fbbf24",
            } as unknown as Record<string, string | number>,
        },
    ];
}

function buildNodeTypeStyles(
    hiddenTypes: Set<string>,
    filterMode: "ghost" | "exclude",
): Stylesheet[] {
    const allTypes = [
        "Service",
        "Endpoint",
        "Deployment",
        "Pod",
        "Node",
        "Database",
        "Table",
        "QueueTopic",
        "Cache",
        "ExternalAPI",
        "SecretConfig",
        "Library",
        "TeamOwner",
        "SLASLO",
        "RegionCluster",
    ];
    return allTypes.map((type) => {
        const visible = !hiddenTypes.has(type);
        return {
            selector: `node[type="${type}"]`,
            style: {
                "background-color": getNodeColor(type),
                shape: getNodeShape(type),
                ...(visible
                    ? { opacity: 1 }
                    : filterMode === "exclude"
                      ? { display: "none" }
                      : { opacity: 0.06 }),
            } as unknown as Record<string, string | number>,
        };
    });
}

function buildNodeStatusStyles(): Stylesheet[] {
    const statuses = ["active", "degraded", "down", "error"];
    return statuses.map((status) => ({
        selector: `node[status="${status}"]`,
        style: {
            "border-color": getStatusColor(status),
            "border-width": status === "active" ? 2 : 3,
        } as unknown as Record<string, string | number>,
    }));
}

function buildEdgeTypeStyles(
    hiddenTypes: Set<string>,
    filterMode: "ghost" | "exclude",
): Stylesheet[] {
    const allTypes = [
        "calls",
        "publishesto",
        "consumesfrom",
        "reads",
        "writes",
        "dependson",
        "deployedon",
        "ownedby",
        "authenticatesvia",
        "ratelimitedby",
        "fails_over_to",
    ];
    return allTypes.map((type) => {
        const visible = !hiddenTypes.has(type);
        return {
            selector: `edge[type="${type}"]`,
            style: {
                "line-color": getEdgeColor(type),
                "target-arrow-color": getEdgeColor(type),
                ...(visible
                    ? { opacity: 0.7 }
                    : filterMode === "exclude"
                      ? { display: "none" }
                      : { opacity: 0.04 }),
            } as unknown as Record<string, string | number>,
        };
    });
}

function buildCallsEdgeMetricStyles(): Stylesheet[] {
    return [
        {
            selector: 'edge[type="calls"][rps]',
            style: {
                width: "mapData(rps, 0, 800, 1.5, 6)",
            } as unknown as Record<string, string | number>,
        },
        {
            selector: "edge[error_rate_percent > 5]",
            style: {
                "line-color": "#ef4444",
                "target-arrow-color": "#ef4444",
                "line-style": "dashed",
                opacity: 0.9,
            } as unknown as Record<string, string | number>,
        },
        {
            selector: "edge[error_rate_percent > 1][error_rate_percent <= 5]",
            style: {
                "line-color": "#f59e0b",
                "target-arrow-color": "#f59e0b",
                opacity: 0.85,
            } as unknown as Record<string, string | number>,
        },
        {
            selector: "edge[latency_p99_ms > 500]",
            style: {
                "line-style": "dashed",
            } as unknown as Record<string, string | number>,
        },
    ];
}
