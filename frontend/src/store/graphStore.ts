import { useMemo } from "react";
import type { GraphAnalytics, GraphEdge, GraphNode, GraphStats } from "../types";
import {
    useGraphDataStore,
    useGraphFilterStore,
    useGraphUiStore,
    type QueryHistoryEntry,
} from "../features/graph/store";

export type { QueryHistoryEntry } from "../features/graph/store";

export interface GraphState {
    nodes: GraphNode[];
    edges: GraphEdge[];
    stats: GraphStats | null;
    analytics: GraphAnalytics | null;

    selectedNodeId: string | null;
    hoveredNodeId: string | null;
    highlightedNodeIds: Set<string>;
    highlightedEdgeIds: Set<string>;
    focusedNodeIds: Set<string>;
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
    setHighlightedEdges: (ids: Set<string>) => void;
    setFocusedNodes: (ids: Set<string>) => void;
    clearVisualFocus: () => void;
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

function getCombinedState(): GraphState {
    const dataState = useGraphDataStore.getState();
    const uiState = useGraphUiStore.getState();
    const filterState = useGraphFilterStore.getState();

    return {
        ...dataState,
        ...uiState,
        ...filterState,
        reset: () => {
            useGraphDataStore.getState().reset();
            useGraphUiStore.getState().reset();
            useGraphFilterStore.getState().reset();
        },
    };
}

interface UseGraphStore {
    (): GraphState;
    <T>(selector: (state: GraphState) => T): T;
    getState: () => GraphState;
}

export const useGraphStore: UseGraphStore = ((selector?: (state: GraphState) => unknown) => {
    const dataState = useGraphDataStore();
    const uiState = useGraphUiStore();
    const filterState = useGraphFilterStore();

    const state = useMemo(
        () => ({
            ...dataState,
            ...uiState,
            ...filterState,
            reset: () => {
                useGraphDataStore.getState().reset();
                useGraphUiStore.getState().reset();
                useGraphFilterStore.getState().reset();
            },
        }),
        [dataState, uiState, filterState],
    );

    return selector ? selector(state) : state;
}) as UseGraphStore;

useGraphStore.getState = getCombinedState;
