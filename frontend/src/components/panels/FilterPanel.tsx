import { useGraphStore } from "../../store/graphStore";
import { getNodeColor, getEdgeColor } from "../../utils/colors";
import { EmptyState } from "../common/EmptyState";

export function FilterPanel() {
    const nodes = useGraphStore((s) => s.nodes);
    const edges = useGraphStore((s) => s.edges);
    const hiddenNodeTypes = useGraphStore((s) => s.hiddenNodeTypes);
    const hiddenEdgeTypes = useGraphStore((s) => s.hiddenEdgeTypes);
    const filterMode = useGraphStore((s) => s.filterMode);
    const toggleNodeType = useGraphStore((s) => s.toggleNodeType);
    const toggleEdgeType = useGraphStore((s) => s.toggleEdgeType);
    const setHiddenNodeTypes = useGraphStore((s) => s.setHiddenNodeTypes);
    const setHiddenEdgeTypes = useGraphStore((s) => s.setHiddenEdgeTypes);
    const setFilterMode = useGraphStore((s) => s.setFilterMode);

    const nodeTypes = [...new Set(nodes.map((n) => n.type))].sort((a, b) => a.localeCompare(b));
    const edgeTypes = [...new Set(edges.map((e) => e.type))].sort((a, b) => a.localeCompare(b));

    if (nodeTypes.length === 0 && edgeTypes.length === 0) {
        return (
            <EmptyState
                title="No graph loaded"
                description="Load a graph to see type filters."
                className="pt-12"
            />
        );
    }

    return (
        <div className="flex flex-col overflow-y-auto max-h-full">
            {/* Filter Mode Selection */}
            <div className="px-5 pt-5 pb-4 border-b border-slate-800/70">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
                    Filter Mode
                </p>
                <div className="flex rounded-lg overflow-hidden border border-slate-700/70 bg-slate-900">
                    <ModeBtn
                        active={filterMode === "ghost"}
                        onClick={() => setFilterMode("ghost")}
                        label="Ghost"
                        desc="Dim in place"
                    />
                    <span className="w-px bg-slate-700/60 shrink-0" />
                    <ModeBtn
                        active={filterMode === "exclude"}
                        onClick={() => setFilterMode("exclude")}
                        label="Exclude"
                        desc="Hide completely"
                    />
                </div>
            </div>

            {/* Node Type Filters */}
            {nodeTypes.length > 0 && (
                <section className="px-5 pt-4 pb-4">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
                            Node Types
                        </h3>
                        <div className="flex gap-1.5">
                            <BulkBtn
                                label="All"
                                active={hiddenNodeTypes.size === 0}
                                onClick={() => setHiddenNodeTypes([])}
                            />
                            <BulkBtn
                                label="None"
                                active={nodeTypes.every((t) => hiddenNodeTypes.has(t))}
                                onClick={() => setHiddenNodeTypes(nodeTypes)}
                            />
                        </div>
                    </div>
                    <div className="space-y-1">
                        {nodeTypes.map((t) => (
                            <TypeToggle
                                key={t}
                                label={t}
                                color={getNodeColor(t)}
                                checked={!hiddenNodeTypes.has(t)}
                                count={nodes.filter((n) => n.type === t).length}
                                onToggle={() => toggleNodeType(t)}
                            />
                        ))}
                    </div>
                </section>
            )}

            {/* Divider */}
            {nodeTypes.length > 0 && edgeTypes.length > 0 && (
                <div className="border-t border-slate-800/60 mx-5" />
            )}

            {/* Edge Type Filters */}
            {edgeTypes.length > 0 && (
                <section className="px-5 pt-4 pb-5">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
                            Edge Types
                        </h3>
                        <div className="flex gap-1.5">
                            <BulkBtn
                                label="All"
                                active={hiddenEdgeTypes.size === 0}
                                onClick={() => setHiddenEdgeTypes([])}
                            />
                            <BulkBtn
                                label="None"
                                active={edgeTypes.every((t) => hiddenEdgeTypes.has(t))}
                                onClick={() => setHiddenEdgeTypes(edgeTypes)}
                            />
                        </div>
                    </div>
                    <div className="space-y-1">
                        {edgeTypes.map((t) => (
                            <TypeToggle
                                key={t}
                                label={t}
                                color={getEdgeColor(t)}
                                checked={!hiddenEdgeTypes.has(t)}
                                count={edges.filter((e) => e.type === t).length}
                                onToggle={() => toggleEdgeType(t)}
                            />
                        ))}
                    </div>
                </section>
            )}
        </div>
    );
}

function ModeBtn({
    active,
    onClick,
    label,
    desc,
}: Readonly<{ active: boolean; onClick: () => void; label: string; desc: string }>) {
    return (
        <button
            onClick={onClick}
            className={[
                "flex-1 py-3 px-3.5 text-left transition-all duration-200",
                active
                    ? "bg-blue-600/20 border-l-2 border-blue-500"
                    : "hover:bg-slate-800/60 border-l-2 border-transparent",
            ].join(" ")}
        >
            <p
                className={`text-sm font-semibold leading-tight ${active ? "text-blue-300" : "text-slate-400"}`}
            >
                {label}
            </p>
            <p className="text-xs text-slate-500 leading-snug mt-1">{desc}</p>
        </button>
    );
}

function BulkBtn({
    label,
    onClick,
    active,
}: Readonly<{ label: string; onClick: () => void; active: boolean }>) {
    return (
        <button
            onClick={onClick}
            className={[
                "text-xs px-2.5 py-1 rounded-md transition-all duration-150 font-medium",
                active
                    ? "bg-slate-700/80 text-slate-200"
                    : "text-slate-500 hover:text-slate-300 hover:bg-slate-800/60",
            ].join(" ")}
        >
            {label}
        </button>
    );
}

interface TypeToggleProps {
    label: string;
    color: string;
    checked: boolean;
    count: number;
    onToggle: () => void;
}

function TypeToggle({ label, color, checked, count, onToggle }: Readonly<TypeToggleProps>) {
    return (
        <label className="flex items-center gap-3 px-2.5 py-2 rounded-lg hover:bg-slate-800/70 cursor-pointer transition-all duration-150 group">
            <input
                type="checkbox"
                checked={checked}
                onChange={onToggle}
                className="shrink-0"
            />
            <span
                className="h-3 w-3 rounded-sm shrink-0 shadow-sm transition-all duration-150"
                style={{
                    backgroundColor: color,
                    opacity: checked ? 1 : 0.3,
                    boxShadow: checked ? `0 0 8px ${color}60` : "none",
                }}
            />
            <span
                className={`flex-1 text-sm leading-tight transition-colors ${
                    checked ? "text-slate-200 font-medium" : "text-slate-500"
                }`}
            >
                {label}
            </span>
            <span
                className={`text-xs tabular-nums font-mono px-2 py-0.5 rounded ${
                    checked
                        ? "text-slate-400 bg-slate-800/60"
                        : "text-slate-600"
                }`}
            >
                {count}
            </span>
        </label>
    );
}
