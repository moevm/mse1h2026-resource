import { create } from "zustand";

interface GraphUiState {
    selectedNodeId: string | null;
    hoveredNodeId: string | null;
    highlightedNodeIds: Set<string>;
    highlightedEdgeIds: Set<string>;
    focusedNodeIds: Set<string>;
    loading: boolean;
    error: string | null;
    selectedAppId: string | null;
    backendStatus: "connected" | "disconnected" | "checking";
    nodePositions: Record<string, { x: number; y: number }>;

    selectNode: (id: string | null) => void;
    hoverNode: (id: string | null) => void;
    setHighlightedNodes: (ids: Set<string>) => void;
    setHighlightedEdges: (ids: Set<string>) => void;
    setFocusedNodes: (ids: Set<string>) => void;
    clearVisualFocus: () => void;
    setLoading: (v: boolean) => void;
    setError: (msg: string | null) => void;
    setSelectedAppId: (id: string | null) => void;
    setBackendStatus: (s: "connected" | "disconnected" | "checking") => void;
    setNodePositions: (positions: Record<string, { x: number; y: number }>) => void;
    clearNodePositions: () => void;
    reset: () => void;
}

const initialState = {
    selectedNodeId: null as string | null,
    hoveredNodeId: null as string | null,
    highlightedNodeIds: new Set<string>(),
    highlightedEdgeIds: new Set<string>(),
    focusedNodeIds: new Set<string>(),
    loading: false,
    error: null as string | null,
    selectedAppId: null as string | null,
    backendStatus: "checking" as const,
    nodePositions: {} as Record<string, { x: number; y: number }>,
};

export const useGraphUiStore = create<GraphUiState>((set) => ({
    ...initialState,
    selectNode: (id) => set({ selectedNodeId: id }),
    hoverNode: (id) => set({ hoveredNodeId: id }),
    setHighlightedNodes: (ids) => set({ highlightedNodeIds: ids }),
    setHighlightedEdges: (ids) => set({ highlightedEdgeIds: ids }),
    setFocusedNodes: (ids) => set({ focusedNodeIds: ids }),
    clearVisualFocus: () =>
        set({
            highlightedNodeIds: new Set<string>(),
            highlightedEdgeIds: new Set<string>(),
            focusedNodeIds: new Set<string>(),
        }),
    setLoading: (v) => set({ loading: v }),
    setError: (msg) => set({ error: msg, loading: false }),
    setSelectedAppId: (id) => set({ selectedAppId: id }),
    setBackendStatus: (s) => set({ backendStatus: s }),
    setNodePositions: (positions) => set({ nodePositions: positions }),
    clearNodePositions: () => set({ nodePositions: {} }),
    reset: () => set(initialState),
}));
