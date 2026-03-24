import { useEffect, useState, useCallback } from "react";
import { useGraph } from "../../hooks/useGraph";
import { useGraphStore } from "../../store/graphStore";
import { useLogStore } from "../../store/logStore";
import { AppLayout } from "../layout/AppLayout";
import { GraphCanvas } from "../graph/GraphCanvas";
import { GraphControls } from "../graph/GraphControls";
import { NodeDetail } from "../graph/NodeDetail";
import { FilterPanel } from "../panels/FilterPanel";
import { QueryPanel } from "../panels/QueryPanel";
import GraphInsightsPanel from "../panels/GraphInsightsPanel";
import { LogPanel } from "../panels/LogPanel";
import ExportPanel from "../panels/ExportPanel";
import TraversalPanel from "../panels/TraversalPanel";
import { CytoscapeProvider } from "../../context/CytoscapeContext";
import { Input } from "../common/Input";
import { Button } from "../common/Button";
import { IconSearch, IconRefresh, IconPanel, IconX } from "../icons";
import type { GraphResponse } from "../../types";

type RightPanel = "detail" | "filter" | "query" | "insights" | "export" | "traversal" | "log";

const PANEL_CONFIG: Array<{ id: RightPanel; label: string; shortLabel: string }> = [
    { id: "detail", label: "Node Detail", shortLabel: "Detail" },
    { id: "filter", label: "Filter", shortLabel: "Filter" },
    { id: "query", label: "Query", shortLabel: "Query" },
    { id: "insights", label: "Insights", shortLabel: "Insights" },
    { id: "traversal", label: "Traversal", shortLabel: "Traverse" },
    { id: "export", label: "Export", shortLabel: "Export" },
    { id: "log", label: "Activity Log", shortLabel: "Log" },
];

export function GraphPage() {
    const { loadFullGraph, checkHealth } = useGraph();
    const nodes = useGraphStore((s) => s.nodes);
    const searchQuery = useGraphStore((s) => s.searchQuery);
    const setSearchQuery = useGraphStore((s) => s.setSearchQuery);
    const error = useGraphStore((s) => s.error);
    const lastRefreshedAt = useGraphStore((s) => s.lastRefreshedAt);
    const logCount = useLogStore((s) => s.entries.length);

    const [rightPanel, setRightPanel] = useState<RightPanel>("detail");
    const [limitInput, setLimitInput] = useState(500);
    const [showRightPanel, setShowRightPanel] = useState(false);

    const handleTraversalResult = useCallback((data: GraphResponse) => {
        useGraphStore.getState().setGraph(data.nodes, data.edges);
    }, []);

    useEffect(() => {
        void checkHealth();
        if (nodes.length === 0) {
            void loadFullGraph(limitInput);
        }
    }, []);

    const headerContent = (
        <div className="flex items-center gap-3 flex-1 min-w-0">
            <Input
                icon={<IconSearch />}
                placeholder="Search nodes…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                wrapperClassName="flex-1 min-w-0 max-w-sm"
            />

            <div className="flex items-center gap-2 shrink-0">
                <label htmlFor="graph-limit" className="text-xs text-slate-500 whitespace-nowrap">
                    Limit
                </label>
                <input
                    id="graph-limit"
                    type="number"
                    min={1}
                    max={5000}
                    className="w-20 bg-slate-800/80 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    value={limitInput}
                    onChange={(e) => setLimitInput(Number(e.target.value))}
                />
                <Button
                    variant="primary"
                    size="sm"
                    icon={<IconRefresh className="w-3.5 h-3.5" />}
                    onClick={() => {
                        void loadFullGraph(limitInput);
                    }}
                >
                    Reload
                </Button>
            </div>

            {lastRefreshedAt && (
                <span className="text-[10px] text-slate-600 hidden 2xl:inline whitespace-nowrap">
                    Updated: {new Date(lastRefreshedAt).toLocaleTimeString()}
                </span>
            )}
        </div>
    );

    return (
        <AppLayout headerContent={headerContent}>
            <CytoscapeProvider>
                <div className="flex h-full overflow-hidden relative">
                    <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
                        <div className="flex-1 relative min-w-0">
                            {error && (
                                <div className="absolute top-3 left-1/2 -translate-x-1/2 z-40 bg-red-900/90 text-red-200 text-xs px-4 py-2 rounded-lg border border-red-700/60 shadow-lg backdrop-blur-sm">
                                    {error}
                                </div>
                            )}
                            <GraphCanvas />
                            <GraphControls />

                            {/* Mobile toggle for right panel */}
                            <button
                                onClick={() => setShowRightPanel(true)}
                                className="lg:hidden absolute top-3 right-3 z-30 p-2.5 rounded-xl bg-slate-800/90 backdrop-blur-sm border border-slate-700/60 shadow-lg"
                                aria-label="Show panel"
                            >
                                <IconPanel className="w-5 h-5 text-slate-300" />
                            </button>
                        </div>
                        <GraphStatsBar />
                    </div>

                    {/* Overlay for mobile drawer */}
                    {showRightPanel && (
                        <button
                            type="button"
                            className="lg:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm animate-fade-in"
                            onClick={() => setShowRightPanel(false)}
                            aria-label="Close panel"
                        />
                    )}

                    {/* Right panel - drawer on mobile, static on desktop */}
                    <aside
                        className={[
                            "bg-slate-950/95 backdrop-blur-sm border-l border-slate-800/70 shrink-0 flex flex-col overflow-hidden",
                            "lg:relative lg:w-72 xl:w-80",
                            "fixed lg:static top-0 right-0 h-full w-80 max-w-[85vw] z-50",
                            "transform transition-transform duration-300 ease-out",
                            showRightPanel ? "translate-x-0" : "translate-x-full lg:translate-x-0",
                        ].join(" ")}
                    >
                        {/* Close button on mobile */}
                        <button
                            onClick={() => setShowRightPanel(false)}
                            className="lg:hidden absolute top-2.5 right-2.5 z-10 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
                            aria-label="Close panel"
                        >
                            <IconX className="w-4 h-4 text-slate-400" />
                        </button>

                        <div className="flex border-b border-slate-800/70 shrink-0 overflow-x-auto scrollbar-none">
                            {PANEL_CONFIG.map(({ id, shortLabel }) => (
                                <button
                                    key={id}
                                    onClick={() => setRightPanel(id)}
                                    className={[
                                        "flex-1 py-2.5 px-1.5 text-[11px] font-medium whitespace-nowrap transition-colors relative",
                                        rightPanel === id
                                            ? "text-blue-400 border-b-2 border-blue-500"
                                            : "text-slate-500 hover:text-slate-300",
                                    ].join(" ")}
                                >
                                    {shortLabel}
                                    {id === "log" && logCount > 0 && (
                                        <span className="absolute top-1.5 right-0.5 h-3.5 min-w-3.5 flex items-center justify-center rounded-full bg-blue-600 text-white text-[8px] px-0.5">
                                            {logCount > 99 ? "99+" : logCount}
                                        </span>
                                    )}
                                </button>
                            ))}
                        </div>

                        <div className="flex-1 overflow-y-auto">
                            {rightPanel === "detail" && <NodeDetail />}
                            {rightPanel === "filter" && <FilterPanel />}
                            {rightPanel === "query" && <QueryPanel />}
                            {rightPanel === "insights" && <GraphInsightsPanel />}
                            {rightPanel === "export" && <ExportPanel />}
                            {rightPanel === "traversal" && (
                                <TraversalPanel onResult={handleTraversalResult} />
                            )}
                            {rightPanel === "log" && <LogPanel />}
                        </div>
                    </aside>
                </div>
            </CytoscapeProvider>
        </AppLayout>
    );
}

function GraphStatsBar() {
    const nodes = useGraphStore((s) => s.nodes);
    const edges = useGraphStore((s) => s.edges);
    const selectedId = useGraphStore((s) => s.selectedNodeId);

    const nodeTypes = new Set(nodes.map((n) => n.type)).size;
    const edgeTypes = new Set(edges.map((e) => e.type)).size;

    return (
        <div className="flex items-center gap-4 px-4 py-1.5 bg-slate-950/70 border-t border-slate-800/70 shrink-0">
            <Stat label="Nodes" value={nodes.length} />
            <div className="h-3 w-px bg-slate-800" />
            <Stat label="Edges" value={edges.length} />
            <div className="h-3 w-px bg-slate-800" />
            <Stat label="Types" value={nodeTypes} />
            <div className="h-3 w-px bg-slate-800" />
            <Stat label="Edge types" value={edgeTypes} />
            {selectedId && (
                <span className="ml-auto text-blue-400 truncate max-w-xs font-mono text-[10px]">
                    {selectedId}
                </span>
            )}
        </div>
    );
}

function Stat({ label, value }: Readonly<{ label: string; value: number }>) {
    return (
        <span className="text-[11px]">
            <span className="text-slate-600">{label}: </span>
            <span className="text-slate-300 tabular-nums font-medium">
                {value.toLocaleString()}
            </span>
        </span>
    );
}
