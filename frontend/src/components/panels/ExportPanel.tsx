import { useState, useEffect, useCallback, useMemo } from "react";
import { fetchExportFormats, downloadExport } from "../../api/graphApi";
import type { ExportFormat, ExportFormatInfo } from "../../types";
import { useGraphStore } from "../../store/graphStore";
import { Button } from "../common/Button";
import { Section } from "../common/Card";
import { IconDownload } from "../icons";

export default function ExportPanel() {
    const [formats, setFormats] = useState<ExportFormatInfo[]>([]);
    const [selectedFormat, setSelectedFormat] = useState<ExportFormat>("json");
    const [includeProperties, setIncludeProperties] = useState(true);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const nodes = useGraphStore((s) => s.nodes);
    const edges = useGraphStore((s) => s.edges);
    const hiddenNodeTypes = useGraphStore((s) => s.hiddenNodeTypes);
    const hiddenEdgeTypes = useGraphStore((s) => s.hiddenEdgeTypes);

    const { nodeTypes, edgeTypes } = useMemo(() => {
        const allNodeTypes = [...new Set(nodes.map((n) => n.type))];
        const allEdgeTypes = [...new Set(edges.map((e) => e.type))];
        const visibleNodes = allNodeTypes.filter((t) => !hiddenNodeTypes.has(t));
        const visibleEdges = allEdgeTypes.filter((t) => !hiddenEdgeTypes.has(t));
        return {
            nodeTypes:
                hiddenNodeTypes.size > 0 && visibleNodes.length !== allNodeTypes.length
                    ? visibleNodes
                    : [],
            edgeTypes:
                hiddenEdgeTypes.size > 0 && visibleEdges.length !== allEdgeTypes.length
                    ? visibleEdges
                    : [],
        };
    }, [nodes, edges, hiddenNodeTypes, hiddenEdgeTypes]);

    useEffect(() => {
        fetchExportFormats()
            .then(setFormats)
            .catch(() => {
                setFormats([
                    { format: "json", label: "JSON", description: "JSON", extension: ".json" },
                    {
                        format: "graphml",
                        label: "GraphML",
                        description: "GraphML (XML)",
                        extension: ".graphml",
                    },
                    {
                        format: "gexf",
                        label: "GEXF",
                        description: "GEXF (Gephi)",
                        extension: ".gexf",
                    },
                    {
                        format: "dot",
                        label: "DOT",
                        description: "DOT (Graphviz)",
                        extension: ".dot",
                    },
                    {
                        format: "cytoscape_json",
                        label: "Cytoscape JSON",
                        description: "Cytoscape JSON",
                        extension: ".cyjs",
                    },
                    {
                        format: "csv",
                        label: "CSV",
                        description: "CSV (zipped)",
                        extension: ".zip",
                    },
                ]);
            });
    }, []);

    const handleDownload = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const blob = await downloadExport({
                format: selectedFormat,
                node_types: nodeTypes.length > 0 ? nodeTypes : undefined,
                edge_types: edgeTypes.length > 0 ? edgeTypes : undefined,
                include_properties: includeProperties,
            });

            const ext =
                formats.find((f) => f.format === selectedFormat)?.extension ?? `.${selectedFormat}`;
            const filename = `topology-export${ext}`;

            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Export failed");
        } finally {
            setLoading(false);
        }
    }, [selectedFormat, nodeTypes, edgeTypes, includeProperties, formats]);

    const filterSummary =
        hiddenNodeTypes.size === 0 && hiddenEdgeTypes.size === 0
            ? "All node and edge types are included. Use the Filter tab to narrow the export."
            : `Using filters from the Filter tab — ${hiddenNodeTypes.size} node type(s) and ${hiddenEdgeTypes.size} edge type(s) excluded.`;

    return (
        <div className="flex flex-col gap-4 p-4 text-sm">
            <Section title="Export Graph">
                <div>
                    <p className="mb-1 text-xs text-slate-400">Format</p>
                    <div className="grid grid-cols-2 gap-1.5">
                        {formats.map((f) => (
                            <button
                                key={f.format}
                                onClick={() => setSelectedFormat(f.format)}
                                className={`rounded-md px-2.5 py-1.5 text-xs font-medium transition-all ${
                                    selectedFormat === f.format
                                        ? "bg-blue-600/30 text-blue-300 ring-1 ring-blue-500/50"
                                        : "bg-slate-800/60 text-slate-400 hover:bg-slate-700/60 hover:text-slate-300"
                                }`}
                            >
                                {f.description}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="space-y-2 mt-3">
                    <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer select-none">
                        <input
                            type="checkbox"
                            checked={includeProperties}
                            onChange={(e) => setIncludeProperties(e.target.checked)}
                            className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500/30"
                        />
                        <span>Include all properties</span>
                    </label>
                </div>
            </Section>

            <p className="rounded-md bg-slate-800/40 px-2.5 py-2 text-xs text-slate-400">
                {filterSummary}
            </p>

            {error && (
                <p className="rounded-md bg-red-900/30 px-2.5 py-1.5 text-xs text-red-400">
                    {error}
                </p>
            )}

            <Button
                onClick={() => {
                    void handleDownload();
                }}
                loading={loading}
                icon={<IconDownload className="w-3.5 h-3.5" />}
                className="w-full"
            >
                Download
            </Button>
        </div>
    );
}
