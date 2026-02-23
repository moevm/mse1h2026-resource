import { useState, useEffect, useRef, useCallback, type RefObject } from "react";
import cytoscape, { type Core, type EventObject } from "cytoscape";
import { useGraphStore } from "../store/graphStore";
import { toCytoscapeElements, filterDanglingEdges, diffCytoscapeGraph } from "../utils/cytoHelpers";
import { buildCytoscapeStyles } from "../utils/cytoscapeStyles";

function isAlive(cy: Core | null): cy is Core {
    return cy !== null && !cy.destroyed();
}

const COSE_BASE: Record<string, unknown> = {
    name: "cose",
    nodeRepulsion: () => 14000,
    idealEdgeLength: () => 90,
    gravity: 0.5,
    nodeDimensionsIncludeLabels: true,
    padding: 40,
};

export function useCytoscape(containerRef: RefObject<HTMLDivElement | null>) {
    const cyRef = useRef<Core | null>(null);
    const layoutRef = useRef<cytoscape.Layouts | null>(null);

    const [cyGen, setCyGen] = useState(0);

    const {
        nodes,
        edges,
        hiddenNodeTypes,
        hiddenEdgeTypes,
        filterMode,
        searchQuery,
        selectedNodeId,
        highlightedNodeIds,
        nodePositions,
        selectNode,
        hoverNode,
        setNodePositions,
    } = useGraphStore();

    const nodePositionsRef = useRef(nodePositions);
    nodePositionsRef.current = nodePositions;
    const setNodePositionsRef = useRef(setNodePositions);
    setNodePositionsRef.current = setNodePositions;
    const filterModeRef = useRef(filterMode);
    filterModeRef.current = filterMode;
    const hiddenNodeTypesRef = useRef(hiddenNodeTypes);
    hiddenNodeTypesRef.current = hiddenNodeTypes;
    const hiddenEdgeTypesRef = useRef(hiddenEdgeTypes);
    hiddenEdgeTypesRef.current = hiddenEdgeTypes;
    const selectNodeRef = useRef(selectNode);
    selectNodeRef.current = selectNode;
    const hoverNodeRef = useRef(hoverNode);
    hoverNodeRef.current = hoverNode;

    const savePositions = useCallback(() => {
        const cy = cyRef.current;
        if (!isAlive(cy)) return;
        const pos: Record<string, { x: number; y: number }> = {};
        cy.nodes().forEach((n) => {
            pos[n.id()] = { ...n.position() };
        });
        setNodePositionsRef.current(pos);
    }, []);

    const stopLayout = useCallback(() => {
        layoutRef.current?.stop();
        layoutRef.current = null;
        if (isAlive(cyRef.current)) cyRef.current.stop(true, true);
    }, []);

    const runCose = useCallback(
        (opts: Record<string, unknown>) => {
            stopLayout();
            if (!isAlive(cyRef.current)) return;
            layoutRef.current = cyRef.current.layout({
                ...COSE_BASE,
                ...opts,
            } as unknown as cytoscape.LayoutOptions);
            layoutRef.current.run();
        },
        [stopLayout],
    );

    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        const cy = cytoscape({
            container,
            elements: [],
            style: buildCytoscapeStyles(
                hiddenNodeTypesRef.current,
                hiddenEdgeTypesRef.current,
                filterModeRef.current,
            ),
            layout: { name: "preset" },
            minZoom: 0.05,
            maxZoom: 6,
            wheelSensitivity: 0.6,
            boxSelectionEnabled: false,
        });

        cy.on("tap", "node", (e: EventObject) => selectNodeRef.current(e.target.id() as string));
        cy.on("tap", (e: EventObject) => {
            if (e.target === cy) selectNodeRef.current(null);
        });
        cy.on("mouseover", "node", (e: EventObject) =>
            hoverNodeRef.current(e.target.id() as string),
        );
        cy.on("mouseout", "node", () => hoverNodeRef.current(null));

        cyRef.current = cy;
        setCyGen((g) => g + 1);

        return () => {
            layoutRef.current?.stop();
            layoutRef.current = null;
            cy.stop(true, true);
            cy.destroy();
            cyRef.current = null;
        };
    }, []);

    useEffect(() => {
        const cy = cyRef.current;
        if (!isAlive(cy)) return;

        if (nodes.length === 0) {
            stopLayout();
            cy.batch(() => cy.elements().remove());
            return;
        }

        const safeEdges = filterDanglingEdges(nodes, edges);

        if (cy.elements().length === 0) {
            const elements = toCytoscapeElements(nodes, safeEdges);
            cy.batch(() => cy.add(elements));

            const saved = nodePositionsRef.current;
            if (Object.keys(saved).length > 0) {
                cy.nodes().forEach((n) => {
                    const p = saved[n.id()];
                    if (p) n.position(p);
                });
                cy.fit(undefined, 40);
            } else {
                runCose({ animate: false, numIter: 1500, fit: true });
            }
            savePositions();
            return;
        }

        const diff = diffCytoscapeGraph(cy, nodes, safeEdges);

        const hasAdditions = diff.toAdd.length > 0;
        const hasRemovals = diff.toRemoveIds.length > 0;
        const hasUpdates = diff.toUpdateNodes.length > 0 || diff.toUpdateEdges.length > 0;

        cy.batch(() => {
            if (hasRemovals) {
                diff.toRemoveIds.forEach((id) => cy.getElementById(id).remove());
            }
            diff.toUpdateNodes.forEach(({ id, data }) => cy.getElementById(id).data(data));
            diff.toUpdateEdges.forEach(({ id, data }) => cy.getElementById(id).data(data));
            if (hasAdditions) {
                cy.add(diff.toAdd);
            }
        });

        if (diff.newNodeIds.size > 0) {
            const existingNodes = cy.nodes().filter((n) => !diff.newNodeIds.has(n.id()));
            existingNodes.lock();
            runCose({ animate: false, numIter: 1000, fit: false });
            existingNodes.unlock();
            savePositions();
        } else if (hasRemovals && !hasUpdates) {
            cy.fit(undefined, 40);
        }
    }, [nodes, edges, cyGen]);

    useEffect(() => {
        const cy = cyRef.current;
        if (!isAlive(cy)) return;

        const style = buildCytoscapeStyles(hiddenNodeTypes, hiddenEdgeTypes, filterMode);
        cy.style(style as unknown as string);

        if (filterMode === "exclude") {
            stopLayout();
            const visibleEles = cy.elements(":visible");
            layoutRef.current = visibleEles.layout({
                ...COSE_BASE,
                name: "cose",
                animate: false,
                numIter: 500,
                fit: true,
            } as unknown as cytoscape.LayoutOptions);
            layoutRef.current.run();
        }
    }, [hiddenNodeTypes, hiddenEdgeTypes, filterMode, cyGen]);

    useEffect(() => {
        const cy = cyRef.current;
        if (!isAlive(cy)) return;

        cy.elements().removeClass("faded highlighted");

        if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase();
            const matched = cy.nodes().filter((n) => {
                const label = ((n.data("label") as string) ?? "").toLowerCase();
                const id = ((n.data("id") as string) ?? "").toLowerCase();
                return label.includes(q) || id.includes(q);
            });
            if (matched.length) {
                cy.elements().addClass("faded");
                matched.removeClass("faded").addClass("highlighted");
                matched.connectedEdges().removeClass("faded");
            }
        }
    }, [searchQuery, cyGen]);

    useEffect(() => {
        const cy = cyRef.current;
        if (!isAlive(cy)) return;

        cy.elements().removeClass("highlighted");
        if (highlightedNodeIds.size > 0) {
            highlightedNodeIds.forEach((id) => cy.getElementById(id).addClass("highlighted"));
        }
    }, [highlightedNodeIds, cyGen]);

    useEffect(() => {
        const cy = cyRef.current;
        if (!isAlive(cy)) return;

        cy.nodes().unselect();
        if (selectedNodeId) cy.getElementById(selectedNodeId).select();
    }, [selectedNodeId, cyGen]);

    const fitGraph = useCallback(() => {
        if (isAlive(cyRef.current)) cyRef.current.fit(undefined, 40);
    }, []);

    const runLayout = useCallback(
        (name = "cose") => {
            const cy = cyRef.current;
            if (!isAlive(cy)) return;

            let opts: Record<string, unknown>;
            if (name === "circle") {
                opts = {
                    name: "circle",
                    spacingFactor: 0.55,
                    padding: 20,
                    animate: true,
                    animationDuration: 500,
                };
            } else if (name === "grid") {
                opts = {
                    name: "grid",
                    spacingFactor: 0.8,
                    padding: 20,
                    animate: true,
                    animationDuration: 400,
                };
            } else {
                opts = {
                    ...COSE_BASE,
                    name,
                    animate: true,
                    animationDuration: 600,
                    numIter: 1500,
                    fit: true,
                };
            }

            stopLayout();
            layoutRef.current = cy.layout(opts as unknown as cytoscape.LayoutOptions);
            layoutRef.current.run();
        },
        [stopLayout],
    );

    const zoomIn = useCallback(() => {
        const cy = cyRef.current;
        if (!isAlive(cy)) return;
        cy.zoom({
            level: cy.zoom() * 1.3,
            renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
        });
    }, []);

    const zoomOut = useCallback(() => {
        const cy = cyRef.current;
        if (!isAlive(cy)) return;
        cy.zoom({
            level: cy.zoom() / 1.3,
            renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
        });
    }, []);

    const centerOn = useCallback((nodeId: string) => {
        const cy = cyRef.current;
        if (!isAlive(cy)) return;
        const node = cy.getElementById(nodeId);
        if (node.length) cy.animate({ center: { eles: node }, zoom: 1.5 }, { duration: 400 });
    }, []);

    return { cyRef, fitGraph, runLayout, zoomIn, zoomOut, centerOn };
}
