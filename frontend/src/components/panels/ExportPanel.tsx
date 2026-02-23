import { useState, useEffect, useCallback } from "react";
import { fetchExportFormats, downloadExport } from "../../api/graphApi";
import type { ExportFormat, ExportFormatInfo } from "../../types";
import { NodeType, EdgeType } from "../../types/enums";
import { Button } from "../common/Button";
import { Input } from "../common/Input";
import { Section } from "../common/Card";
import { IconDownload } from "../icons";

const NODE_TYPE_VALUES = Object.values(NodeType);
const EDGE_TYPE_VALUES = Object.values(EdgeType);

export default function ExportPanel() {
    const [formats, setFormats] = useState<ExportFormatInfo[]>([]);
    const [selectedFormat, setSelectedFormat] = useState<ExportFormat>("json");
    const [includeProperties, setIncludeProperties] = useState(true);
    const [limit, setLimit] = useState(0);
    const [nodeTypes, setNodeTypes] = useState<string[]>([]);
    const [edgeTypes, setEdgeTypes] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showNodeFilter, setShowNodeFilter] = useState(false);
    const [showEdgeFilter, setShowEdgeFilter] = useState(false);

    useEffect(() => {
        fetchExportFormats()
            .then(setFormats)
            .catch(() => {
                setFormats([
                    {
                        format: "json",
                        description: "JSON",
                        content_type: "application/json",
                        extension: ".json",
                    },
                    {
                        format: "graphml",
                        description: "GraphML (XML)",
                        content_type: "application/xml",
                        extension: ".graphml",
                    },
                    {
                        format: "gexf",
                        description: "GEXF (Gephi)",
                        content_type: "application/xml",
                        extension: ".gexf",
                    },
                    {
                        format: "dot",
                        description: "DOT (Graphviz)",
                        content_type: "text/vnd.graphviz",
                        extension: ".dot",
                    },
                    {
                        format: "cytoscape_json",
                        description: "Cytoscape JSON",
                        content_type: "application/json",
                        extension: ".cyjs",
                    },
                    {
                        format: "csv",
                        description: "CSV (zipped)",
                        content_type: "application/zip",
                        extension: ".zip",
                    },
                ]);
            });
    }, []);

    const toggleNodeType = (t: string) => {
        setNodeTypes((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));
    };
    const toggleEdgeType = (t: string) => {
        setEdgeTypes((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));
    };

    const handleDownload = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const blob = await downloadExport({
                format: selectedFormat,
                limit: limit > 0 ? limit : undefined,
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
    }, [selectedFormat, limit, nodeTypes, edgeTypes, includeProperties, formats]);

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

                    <Input
                        label="Node limit (0 = all)"
                        type="number"
                        value={limit}
                        onChange={(e) => setLimit(Number(e.target.value))}
                        min={0}
                    />
                </div>
            </Section>

            <div>
                <button
                    onClick={() => setShowNodeFilter(!showNodeFilter)}
                    className="flex w-full items-center justify-between text-xs text-slate-400 hover:text-slate-300"
                >
                    <span>Filter node types {nodeTypes.length > 0 && `(${nodeTypes.length})`}</span>
                    <span>{showNodeFilter ? "▾" : "▸"}</span>
                </button>
                {showNodeFilter && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                        {NODE_TYPE_VALUES.map((t) => (
                            <button
                                key={t}
                                onClick={() => toggleNodeType(t)}
                                className={`rounded px-2 py-0.5 text-[10px] font-medium transition-all ${
                                    nodeTypes.includes(t)
                                        ? "bg-emerald-600/30 text-emerald-300 ring-1 ring-emerald-500/40"
                                        : "bg-slate-800/60 text-slate-500 hover:text-slate-400"
                                }`}
                            >
                                {t}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            <div>
                <button
                    onClick={() => setShowEdgeFilter(!showEdgeFilter)}
                    className="flex w-full items-center justify-between text-xs text-slate-400 hover:text-slate-300"
                >
                    <span>Filter edge types {edgeTypes.length > 0 && `(${edgeTypes.length})`}</span>
                    <span>{showEdgeFilter ? "▾" : "▸"}</span>
                </button>
                {showEdgeFilter && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                        {EDGE_TYPE_VALUES.map((t) => (
                            <button
                                key={t}
                                onClick={() => toggleEdgeType(t)}
                                className={`rounded px-2 py-0.5 text-[10px] font-medium transition-all ${
                                    edgeTypes.includes(t)
                                        ? "bg-amber-600/30 text-amber-300 ring-1 ring-amber-500/40"
                                        : "bg-slate-800/60 text-slate-500 hover:text-slate-400"
                                }`}
                            >
                                {t}
                            </button>
                        ))}
                    </div>
                )}
            </div>

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
