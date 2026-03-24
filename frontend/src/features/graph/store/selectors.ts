import { useMemo } from "react";
import { useGraphDataStore } from "./graphDataStore";
import { useGraphFilterStore } from "./graphFilterStore";
import { useGraphUiStore } from "./graphUiStore";

export function useGraphNodes() {
    return useGraphDataStore((s) => s.nodes);
}

export function useGraphEdges() {
    return useGraphDataStore((s) => s.edges);
}

export function useVisibleNodes() {
    const nodes = useGraphDataStore((s) => s.nodes);
    const hiddenNodeTypes = useGraphFilterStore((s) => s.hiddenNodeTypes);
    const searchQuery = useGraphFilterStore((s) => s.searchQuery);

    return useMemo(() => {
        const query = searchQuery.trim().toLowerCase();
        return nodes.filter((node) => {
            if (hiddenNodeTypes.has(node.type)) {
                return false;
            }
            if (!query) {
                return true;
            }
            return (
                node.name.toLowerCase().includes(query) ||
                node.id.toLowerCase().includes(query) ||
                node.type.toLowerCase().includes(query)
            );
        });
    }, [nodes, hiddenNodeTypes, searchQuery]);
}

export function useSelectedNode() {
    const selectedNodeId = useGraphUiStore((s) => s.selectedNodeId);
    const nodes = useGraphDataStore((s) => s.nodes);

    return useMemo(() => {
        if (!selectedNodeId) {
            return null;
        }
        return nodes.find((node) => node.id === selectedNodeId) ?? null;
    }, [nodes, selectedNodeId]);
}

export function useNodeEdges(nodeId: string | null) {
    const edges = useGraphDataStore((s) => s.edges);

    return useMemo(() => {
        if (!nodeId) {
            return { incoming: [], outgoing: [] };
        }

        const incoming = edges.filter((edge) => edge.target_id === nodeId);
        const outgoing = edges.filter((edge) => edge.source_id === nodeId);
        return { incoming, outgoing };
    }, [edges, nodeId]);
}
