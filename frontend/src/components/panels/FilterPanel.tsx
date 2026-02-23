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
                className="pt-10"
            />
        );
    }

    return (
        <div className="flex flex-col overflow-y-auto max-h-full">
            <div className="px-4 pt-4 pb-3 border-b border-slate-800/70">
                <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2.5">
                    Hidden elements
                </p>
                <div className="flex rounded-lg overflow-hidden border border-slate-700/60 bg-slate-900">
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
                        desc="Remove from graph"
                    />
                </div>
            </div>

            {nodeTypes.length > 0 && (
                <section className="px-4 pt-3.5 pb-3">
                    <div className="flex items-center justify-between mb-2">
                        <h3 className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                            Nodes
                        </h3>
                        <div className="flex gap-1">
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
                    <div className="space-y-0.5">
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

            {nodeTypes.length > 0 && edgeTypes.length > 0 && (
                <div className="border-t border-slate-800/60 mx-4" />
            )}

            {edgeTypes.length > 0 && (
                <section className="px-4 pt-3.5 pb-4">
                    <div className="flex items-center justify-between mb-2">
                        <h3 className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                            Edges
                        </h3>
                        <div className="flex gap-1">
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
                    <div className="space-y-0.5">
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
                "flex-1 py-2.5 px-3 text-left transition-colors",
                active ? "bg-blue-600/15" : "hover:bg-slate-800/50",
            ].join(" ")}
        >
            <p
                className={`text-xs font-semibold leading-tight ${active ? "text-blue-300" : "text-slate-400"}`}
            >
                {label}
            </p>
            <p className="text-[10px] text-slate-600 leading-tight mt-0.5">{desc}</p>
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
                "text-[10px] px-2 py-0.5 rounded transition-colors font-medium",
                active
                    ? "bg-slate-700 text-slate-300"
                    : "text-slate-600 hover:text-slate-400 hover:bg-slate-800/60",
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
        <label className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-slate-800/70 cursor-pointer transition-colors">
            <span
                className="h-2.5 w-2.5 rounded-sm shrink-0 ring-1 ring-inset ring-black/25 transition-opacity"
                style={{ backgroundColor: color, opacity: checked ? 1 : 0.3 }}
            />
            <input type="checkbox" checked={checked} onChange={onToggle} className="sr-only" />
            <span
                className={`flex-1 text-xs leading-tight transition-colors ${checked ? "text-slate-200" : "text-slate-500"}`}
            >
                {label}
            </span>
            <span
                className={`text-[10px] tabular-nums font-mono ${checked ? "text-slate-500" : "text-slate-700"}`}
            >
                {count}
            </span>
        </label>
    );
}
