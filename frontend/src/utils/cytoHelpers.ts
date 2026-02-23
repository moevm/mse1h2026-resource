import type { Core, ElementDefinition } from "cytoscape";
import type { GraphNode, GraphEdge } from "../types";

const CYTO_RESERVED_NODE = new Set(["id", "label", "parent", "source", "target"]);
const CYTO_RESERVED_EDGE = new Set(["id", "source", "target"]);

export function makeEdgeId(e: GraphEdge): string {
    return `${e.source_id}::${e.target_id}::${e.type}`;
}

function buildNodeData(n: GraphNode): Record<string, unknown> {
    const safeProps: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(n.properties)) {
        if (!CYTO_RESERVED_NODE.has(k)) safeProps[k] = v;
    }
    return {
        id: n.id,
        label: n.name,
        type: n.type,
        status: n.status ?? "active",
        environment: n.environment ?? "",
        ...safeProps,
    };
}

function buildEdgeData(e: GraphEdge): Record<string, unknown> {
    const safeProps: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(e.properties)) {
        if (!CYTO_RESERVED_EDGE.has(k)) safeProps[k] = v;
    }
    return {
        id: makeEdgeId(e),
        source: e.source_id,
        target: e.target_id,
        type: e.type,
        status: e.status ?? "active",
        ...safeProps,
    };
}

export function toCytoscapeElements(nodes: GraphNode[], edges: GraphEdge[]): ElementDefinition[] {
    return [
        ...nodes.map((n) => ({ group: "nodes" as const, data: buildNodeData(n) })),
        ...edges.map((e) => ({ group: "edges" as const, data: buildEdgeData(e) })),
    ];
}

export interface GraphDiff {
    toAdd: ElementDefinition[];
    toRemoveIds: string[];
    toUpdateNodes: Array<{ id: string; data: Record<string, unknown> }>;
    toUpdateEdges: Array<{ id: string; data: Record<string, unknown> }>;
    newNodeIds: Set<string>;
}

export function diffCytoscapeGraph(cy: Core, nodes: GraphNode[], edges: GraphEdge[]): GraphDiff {
    const newNodeMap = new Map(nodes.map((n) => [n.id, n]));
    const newEdgeMap = new Map(edges.map((e) => [makeEdgeId(e), e]));

    const existingNodeIds = new Set<string>();
    cy.nodes().forEach((n) => {
        existingNodeIds.add(n.id());
    });

    const existingEdgeIds = new Set<string>();
    cy.edges().forEach((e) => {
        existingEdgeIds.add(e.id());
    });

    const toAddNodes: ElementDefinition[] = [];
    const toUpdateNodes: GraphDiff["toUpdateNodes"] = [];
    const newNodeIds = new Set<string>();

    for (const [id, node] of newNodeMap) {
        if (existingNodeIds.has(id)) {
            toUpdateNodes.push({ id, data: buildNodeData(node) });
        } else {
            newNodeIds.add(id);
            toAddNodes.push({ group: "nodes", data: buildNodeData(node) });
        }
    }

    const toAddEdges: ElementDefinition[] = [];
    const toUpdateEdges: GraphDiff["toUpdateEdges"] = [];

    for (const [id, edge] of newEdgeMap) {
        if (existingEdgeIds.has(id)) {
            toUpdateEdges.push({ id, data: buildEdgeData(edge) });
        } else {
            toAddEdges.push({ group: "edges", data: buildEdgeData(edge) });
        }
    }

    const toRemoveIds: string[] = [];
    existingNodeIds.forEach((id) => {
        if (!newNodeMap.has(id)) toRemoveIds.push(id);
    });
    existingEdgeIds.forEach((id) => {
        if (!newEdgeMap.has(id)) toRemoveIds.push(id);
    });

    return {
        toAdd: [...toAddNodes, ...toAddEdges],
        toRemoveIds,
        toUpdateNodes,
        toUpdateEdges,
        newNodeIds,
    };
}

export function filterDanglingEdges(nodes: GraphNode[], edges: GraphEdge[]): GraphEdge[] {
    const nodeIds = new Set(nodes.map((n) => n.id));
    return edges.filter((e) => nodeIds.has(e.source_id) && nodeIds.has(e.target_id));
}
