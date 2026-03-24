import { create } from "zustand";
import type { GraphAnalytics, GraphEdge, GraphNode, GraphStats } from "../../../types";

export interface QueryHistoryEntry {
    id: string;
    timestamp: string;
    type: "full" | "subgraph" | "path" | "impact" | "layout";
    params: Record<string, unknown>;
    nodeCount: number;
    edgeCount: number;
}

interface GraphDataState {
    nodes: GraphNode[];
    edges: GraphEdge[];
    stats: GraphStats | null;
    analytics: GraphAnalytics | null;
    queryHistory: QueryHistoryEntry[];
    lastRefreshedAt: string | null;

    setGraph: (nodes: GraphNode[], edges: GraphEdge[]) => void;
    setStats: (stats: GraphStats) => void;
    setAnalytics: (analytics: GraphAnalytics) => void;
    addQueryHistory: (entry: Omit<QueryHistoryEntry, "id" | "timestamp">) => void;
    setLastRefreshed: () => void;
    reset: () => void;
}

const initialState = {
    nodes: [] as GraphNode[],
    edges: [] as GraphEdge[],
    stats: null as GraphStats | null,
    analytics: null as GraphAnalytics | null,
    queryHistory: [] as QueryHistoryEntry[],
    lastRefreshedAt: null as string | null,
};

export const useGraphDataStore = create<GraphDataState>((set) => ({
    ...initialState,
    setGraph: (nodes, edges) =>
        set({
            nodes,
            edges,
        }),
    setStats: (stats) => set({ stats }),
    setAnalytics: (analytics) => set({ analytics }),
    addQueryHistory: (entry) =>
        set((s) => {
            const newEntry: QueryHistoryEntry = {
                ...entry,
                id: `qh-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                timestamp: new Date().toISOString(),
            };
            return { queryHistory: [newEntry, ...s.queryHistory].slice(0, 50) };
        }),
    setLastRefreshed: () => set({ lastRefreshedAt: new Date().toISOString() }),
    reset: () => set(initialState),
}));
