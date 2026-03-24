import { create } from "zustand";

interface GraphFilterState {
    hiddenNodeTypes: Set<string>;
    hiddenEdgeTypes: Set<string>;
    filterMode: "ghost" | "exclude";
    searchQuery: string;

    toggleNodeType: (type: string) => void;
    toggleEdgeType: (type: string) => void;
    setHiddenNodeTypes: (types: string[]) => void;
    setHiddenEdgeTypes: (types: string[]) => void;
    setFilterMode: (mode: "ghost" | "exclude") => void;
    setSearchQuery: (q: string) => void;
    reset: () => void;
}

const initialState = {
    hiddenNodeTypes: new Set<string>(),
    hiddenEdgeTypes: new Set<string>(),
    filterMode: "ghost" as const,
    searchQuery: "",
};

export const useGraphFilterStore = create<GraphFilterState>((set) => ({
    ...initialState,
    toggleNodeType: (type) =>
        set((s) => {
            const next = new Set(s.hiddenNodeTypes);
            if (next.has(type)) {
                next.delete(type);
            } else {
                next.add(type);
            }
            return { hiddenNodeTypes: next };
        }),
    toggleEdgeType: (type) =>
        set((s) => {
            const next = new Set(s.hiddenEdgeTypes);
            if (next.has(type)) {
                next.delete(type);
            } else {
                next.add(type);
            }
            return { hiddenEdgeTypes: next };
        }),
    setHiddenNodeTypes: (types) => set({ hiddenNodeTypes: new Set(types) }),
    setHiddenEdgeTypes: (types) => set({ hiddenEdgeTypes: new Set(types) }),
    setFilterMode: (mode) => set({ filterMode: mode }),
    setSearchQuery: (q) => set({ searchQuery: q }),
    reset: () => set(initialState),
}));
