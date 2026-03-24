import type { GraphEdge, GraphNode } from "../types";
import { makeEdgeId } from "./cytoHelpers";

export interface LocalPathOptions {
    direction?: "directed" | "undirected";
    maxDepth?: number;
    allowedEdgeTypes?: Set<string>;
}

export interface LocalPathResult {
    nodeIds: string[];
    edgeIds: string[];
    hops: number;
}

interface AdjacencyItem {
    nextId: string;
    edge: GraphEdge;
}

export function findShortestPathLocal(
    nodes: GraphNode[],
    edges: GraphEdge[],
    sourceId: string,
    targetId: string,
    options: LocalPathOptions = {},
): LocalPathResult | null {
    const validation = validatePathEndpoints(nodes, sourceId, targetId);
    if (!validation.valid) return null;
    if (validation.isSameNode) return { nodeIds: [sourceId], edgeIds: [], hops: 0 };

    const adjacency = buildAdjacency(
        edges,
        options.direction ?? "directed",
        options.allowedEdgeTypes,
    );

    return bfsShortestPath(
        sourceId,
        targetId,
        adjacency,
        options.maxDepth ?? Number.POSITIVE_INFINITY,
    );
}

export function collectNeighborhood(
    nodes: GraphNode[],
    edges: GraphEdge[],
    centerId: string,
    depth: number,
    direction: "incoming" | "outgoing" | "both" = "both",
): { nodeIds: Set<string>; edgeIds: Set<string> } {
    const nodeIds = new Set(nodes.map((n) => n.id));
    if (!nodeIds.has(centerId) || depth < 0) {
        return { nodeIds: new Set<string>(), edgeIds: new Set<string>() };
    }

    const visited = new Set<string>([centerId]);
    const inScopeEdges = new Set<string>();
    let frontier = new Set<string>([centerId]);

    for (let d = 0; d < depth; d += 1) {
        const nextFrontier = new Set<string>();

        edges.forEach((edge) => {
            const edgeId = makeEdgeId(edge);
            const fromActive = frontier.has(edge.source_id);
            const toActive = frontier.has(edge.target_id);

            if (direction !== "incoming" && fromActive) {
                nextFrontier.add(edge.target_id);
                inScopeEdges.add(edgeId);
            }

            if (direction !== "outgoing" && toActive) {
                nextFrontier.add(edge.source_id);
                inScopeEdges.add(edgeId);
            }
        });

        nextFrontier.forEach((id) => visited.add(id));
        frontier = nextFrontier;

        if (frontier.size === 0) break;
    }

    return { nodeIds: visited, edgeIds: inScopeEdges };
}

export function computeGraphInsights(nodes: GraphNode[], edges: GraphEdge[]) {
    const nodeCount = nodes.length;
    const edgeCount = edges.length;
    const avgOutDegree = nodeCount > 0 ? edgeCount / nodeCount : 0;

    const degreeMap = new Map<string, number>();
    nodes.forEach((n) => degreeMap.set(n.id, 0));
    edges.forEach((e) => {
        degreeMap.set(e.source_id, (degreeMap.get(e.source_id) ?? 0) + 1);
        degreeMap.set(e.target_id, (degreeMap.get(e.target_id) ?? 0) + 1);
    });

    const topByDegree = [...degreeMap.entries()]
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([id, degree]) => ({ id, degree }));

    const weaklyConnectedComponents = countWeaklyConnectedComponents(nodes, edges);

    return {
        nodeCount,
        edgeCount,
        avgOutDegree,
        weaklyConnectedComponents,
        topByDegree,
    };
}

function buildAdjacency(
    edges: GraphEdge[],
    direction: "directed" | "undirected",
    allowedEdgeTypes?: Set<string>,
): Map<string, AdjacencyItem[]> {
    const adjacency = new Map<string, AdjacencyItem[]>();

    const add = (from: string, to: string, edge: GraphEdge) => {
        const arr = adjacency.get(from);
        if (arr) {
            arr.push({ nextId: to, edge });
        } else {
            adjacency.set(from, [{ nextId: to, edge }]);
        }
    };

    edges.forEach((edge) => {
        if (allowedEdgeTypes && allowedEdgeTypes.size > 0 && !allowedEdgeTypes.has(edge.type)) {
            return;
        }

        add(edge.source_id, edge.target_id, edge);
        if (direction === "undirected") {
            add(edge.target_id, edge.source_id, edge);
        }
    });

    return adjacency;
}

function bfsShortestPath(
    sourceId: string,
    targetId: string,
    adjacency: Map<string, AdjacencyItem[]>,
    maxDepth: number,
): LocalPathResult | null {
    const queue: string[] = [sourceId];
    const depthByNode = new Map<string, number>([[sourceId, 0]]);
    const prevByNode = new Map<string, { prev: string; edgeId: string }>();

    while (queue.length > 0) {
        const current = queue.shift();
        if (!current) continue;

        const currentDepth = depthByNode.get(current) ?? 0;
        if (currentDepth >= maxDepth) continue;

        const neighbors = adjacency.get(current) ?? [];
        const found = visitNeighbors(
            current,
            currentDepth,
            neighbors,
            targetId,
            queue,
            depthByNode,
            prevByNode,
        );

        if (found) {
            return buildPathResult(sourceId, targetId, prevByNode);
        }
    }

    return null;
}

function visitNeighbors(
    current: string,
    currentDepth: number,
    neighbors: AdjacencyItem[],
    targetId: string,
    queue: string[],
    depthByNode: Map<string, number>,
    prevByNode: Map<string, { prev: string; edgeId: string }>,
): boolean {
    for (const { nextId, edge } of neighbors) {
        if (depthByNode.has(nextId)) continue;

        depthByNode.set(nextId, currentDepth + 1);
        prevByNode.set(nextId, { prev: current, edgeId: makeEdgeId(edge) });

        if (nextId === targetId) {
            return true;
        }

        queue.push(nextId);
    }

    return false;
}

function validatePathEndpoints(
    nodes: GraphNode[],
    sourceId: string,
    targetId: string,
): { valid: boolean; isSameNode: boolean } {
    if (!sourceId || !targetId) {
        return { valid: false, isSameNode: false };
    }

    const nodeIds = new Set(nodes.map((n) => n.id));
    if (!nodeIds.has(sourceId) || !nodeIds.has(targetId)) {
        return { valid: false, isSameNode: false };
    }

    return { valid: true, isSameNode: sourceId === targetId };
}

function buildPathResult(
    sourceId: string,
    targetId: string,
    prevByNode: Map<string, { prev: string; edgeId: string }>,
): LocalPathResult {
    const nodeIds: string[] = [targetId];
    const edgeIds: string[] = [];

    let cursor = targetId;
    while (cursor !== sourceId) {
        const step = prevByNode.get(cursor);
        if (!step) break;
        edgeIds.push(step.edgeId);
        nodeIds.push(step.prev);
        cursor = step.prev;
    }

    nodeIds.reverse();
    edgeIds.reverse();

    return {
        nodeIds,
        edgeIds,
        hops: edgeIds.length,
    };
}

function countWeaklyConnectedComponents(nodes: GraphNode[], edges: GraphEdge[]): number {
    if (nodes.length === 0) return 0;

    const adjacency = new Map<string, Set<string>>();
    nodes.forEach((n) => adjacency.set(n.id, new Set<string>()));

    edges.forEach((e) => {
        adjacency.get(e.source_id)?.add(e.target_id);
        adjacency.get(e.target_id)?.add(e.source_id);
    });

    const visited = new Set<string>();
    let components = 0;

    nodes.forEach((node) => {
        if (visited.has(node.id)) return;

        components += 1;
        const stack = [node.id];
        visited.add(node.id);

        while (stack.length > 0) {
            const current = stack.pop();
            if (!current) continue;

            adjacency.get(current)?.forEach((neighbor) => {
                if (visited.has(neighbor)) return;
                visited.add(neighbor);
                stack.push(neighbor);
            });
        }
    });

    return components;
}
