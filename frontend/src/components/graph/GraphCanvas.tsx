import { useState, useCallback } from "react";
import { useCyContext } from "../../context/CytoscapeContext";
import { useGraphStore } from "../../store/graphStore";
import { Spinner } from "../common/Spinner";
import { Badge } from "../common/Badge";
import { getStatusColor } from "../../utils/colors";

export function GraphCanvas() {
    const { containerRef } = useCyContext();

    const loading = useGraphStore((s) => s.loading);
    const nodes = useGraphStore((s) => s.nodes);
    const hoveredNodeId = useGraphStore((s) => s.hoveredNodeId);

    const hoveredNode = hoveredNodeId ? nodes.find((n) => n.id === hoveredNodeId) : null;

    const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
    const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        const rect = e.currentTarget.getBoundingClientRect();
        setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    }, []);

    return (
        <div
            className="relative w-full h-full"
            role="application"
            aria-label="Graph visualization canvas"
            onMouseMove={handleMouseMove}
        >
            {loading && (
                <div className="absolute inset-0 z-20 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm">
                    <Spinner size="lg" />
                </div>
            )}

            {!loading && nodes.length === 0 && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center text-slate-500">
                    <svg
                        className="w-16 h-16 mb-4 opacity-30"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={1}
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125v-3.75"
                        />
                    </svg>
                    <p className="text-sm">No graph data loaded</p>
                    <p className="text-xs text-slate-600 mt-1">
                        Use the Reload button or run an analysis query
                    </p>
                </div>
            )}

            <div ref={containerRef} className="w-full h-full cursor-default" />

            {hoveredNode && <NodeTooltip node={hoveredNode} x={mousePos.x} y={mousePos.y} />}
        </div>
    );
}

interface TooltipNode {
    id: string;
    name: string;
    type: string;
    status?: string;
    environment?: string;
    properties: Record<string, unknown>;
}

function NodeTooltip({
    node,
    x,
    y,
}: Readonly<{
    node: TooltipNode;
    x: number;
    y: number;
}>) {
    const preview = Object.entries(node.properties)
        .filter(([, v]) => v !== null && v !== undefined && v !== "")
        .slice(0, 3);

    const OFFSET = 14;
    const style: React.CSSProperties = {
        left: x + OFFSET,
        top: y + OFFSET,
        maxWidth: 240,
    };

    return (
        <div
            className="absolute z-50 pointer-events-none bg-slate-800/95 border border-slate-700 rounded-xl shadow-2xl p-3 text-xs backdrop-blur-sm"
            style={style}
        >
            <div className="flex items-center gap-2 mb-2">
                <Badge label={node.type} nodeType={node.type} />
                <span
                    className="h-1.5 w-1.5 rounded-full shrink-0"
                    style={{ backgroundColor: getStatusColor(node.status) }}
                />
            </div>
            <p className="text-slate-100 font-semibold truncate">{node.name}</p>
            <p className="text-slate-500 font-mono text-[10px] mt-0.5 truncate">{node.id}</p>
            {preview.length > 0 && (
                <div className="mt-2 pt-2 border-t border-slate-700 space-y-0.5">
                    {preview.map(([k, v]) => (
                        <div key={k} className="flex justify-between gap-3">
                            <span className="text-slate-500">{k}</span>
                            <span className="text-slate-300 font-mono truncate max-w-30">
                                {String(v)}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
