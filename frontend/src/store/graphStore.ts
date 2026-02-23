import { create } from "zustand";
import type { GraphNode, GraphEdge, GraphStats, GraphAnalytics } from "../types";

export interface QueryHistoryEntry {
    id: string;
    timestamp: string;
    type: "full" | "subgraph" | "path" | "impact" | "layout";
    params: Record<string, unknown>;
    nodeCount: number;
    edgeCount: number;
}

export interface GraphState {
    nodes: GraphNode[];
    edges: GraphEdge[];
    stats: GraphStats | null;
    analytics: GraphAnalytics | null;

    selectedNodeId: string | null;
    hoveredNodeId: string | null;
    highlightedNodeIds: Set<string>;
    loading: boolean;
    error: string | null;

    hiddenNodeTypes: Set<string>;
    hiddenEdgeTypes: Set<string>;
    filterMode: "ghost" | "exclude";
    searchQuery: string;

    queryHistory: QueryHistoryEntry[];

    backendStatus: "connected" | "disconnected" | "checking";
    lastRefreshedAt: string | null;

    nodePositions: Record<string, { x: number; y: number }>;

    setGraph: (nodes: GraphNode[], edges: GraphEdge[]) => void;
    setStats: (stats: GraphStats) => void;
    setAnalytics: (analytics: GraphAnalytics) => void;
    selectNode: (id: string | null) => void;
    hoverNode: (id: string | null) => void;
    setHighlightedNodes: (ids: Set<string>) => void;
    setLoading: (v: boolean) => void;
    setError: (msg: string | null) => void;
    toggleNodeType: (type: string) => void;
    toggleEdgeType: (type: string) => void;
    setHiddenNodeTypes: (types: string[]) => void;
    setHiddenEdgeTypes: (types: string[]) => void;
    setFilterMode: (mode: "ghost" | "exclude") => void;
    setSearchQuery: (q: string) => void;
    addQueryHistory: (entry: Omit<QueryHistoryEntry, "id" | "timestamp">) => void;
    setBackendStatus: (s: "connected" | "disconnected" | "checking") => void;
    setLastRefreshed: () => void;
    setNodePositions: (positions: Record<string, { x: number; y: number }>) => void;
    clearNodePositions: () => void;
    reset: () => void;
}

const initialState = {
    nodes: [] as GraphNode[],
    edges: [] as GraphEdge[],
    stats: null as GraphStats | null,
    analytics: null as GraphAnalytics | null,
    selectedNodeId: null as string | null,
    hoveredNodeId: null as string | null,
    highlightedNodeIds: new Set<string>(),
    loading: false,
    error: null as string | null,
    hiddenNodeTypes: new Set<string>(),
    nodePositions: {} as Record<string, { x: number; y: number }>,
    hiddenEdgeTypes: new Set<string>(),
    filterMode: "ghost" as const,
    searchQuery: "",
    queryHistory: [] as QueryHistoryEntry[],
    backendStatus: "checking" as const,
    lastRefreshedAt: null as string | null,
};

export const useGraphStore = create<GraphState>((set) => ({
    ...initialState,

    setGraph: (nodes, edges) =>
        set({
            nodes,
            edges,
            error: null,
        }),

    setStats: (stats) => set({ stats }),

    setAnalytics: (analytics) => set({ analytics }),

    selectNode: (id) => set({ selectedNodeId: id }),

    hoverNode: (id) => set({ hoveredNodeId: id }),

    setHighlightedNodes: (ids) => set({ highlightedNodeIds: ids }),

    setLoading: (v) => set({ loading: v }),

    setError: (msg) => set({ error: msg, loading: false }),

    toggleNodeType: (type) =>
        set((s) => {
            const next = new Set(s.hiddenNodeTypes);
            if (next.has(type)) next.delete(type);
            else next.add(type);
            return { hiddenNodeTypes: next };
        }),

    toggleEdgeType: (type) =>
        set((s) => {
            const next = new Set(s.hiddenEdgeTypes);
            if (next.has(type)) next.delete(type);
            else next.add(type);
            return { hiddenEdgeTypes: next };
        }),

    setHiddenNodeTypes: (types) => set({ hiddenNodeTypes: new Set(types) }),

    setHiddenEdgeTypes: (types) => set({ hiddenEdgeTypes: new Set(types) }),

    setFilterMode: (mode) => set({ filterMode: mode }),

    setSearchQuery: (q) => set({ searchQuery: q }),

    addQueryHistory: (entry) =>
        set((s) => {
            const newEntry: QueryHistoryEntry = {
                ...entry,
                id: `qh-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                timestamp: new Date().toISOString(),
            };
            return { queryHistory: [newEntry, ...s.queryHistory].slice(0, 50) };
        }),

    setBackendStatus: (s) => set({ backendStatus: s }),

    setLastRefreshed: () => set({ lastRefreshedAt: new Date().toISOString() }),

    setNodePositions: (positions) => set({ nodePositions: positions }),

    clearNodePositions: () => set({ nodePositions: {} }),

    reset: () => set(initialState),
}));
