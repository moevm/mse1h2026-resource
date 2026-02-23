import type { ReactNode } from "react";
import { useLogStore } from "../../store/logStore";
import { useGraphStore, type QueryHistoryEntry } from "../../store/graphStore";
import type { LogLevel } from "../../types";
import { Input } from "../common/Input";
import { Button } from "../common/Button";
import { IconInfo, IconCheckCircle, IconExclamation, IconXCircle } from "../icons";

const LEVEL_CONFIG: Record<LogLevel, { icon: ReactNode; color: string; bg: string }> = {
    info: { icon: <IconInfo className="w-3.5 h-3.5" />, color: "#60a5fa", bg: "bg-blue-500/10" },
    success: {
        icon: <IconCheckCircle className="w-3.5 h-3.5" />,
        color: "#22c55e",
        bg: "bg-green-500/10",
    },
    warn: {
        icon: <IconExclamation className="w-3.5 h-3.5" />,
        color: "#f59e0b",
        bg: "bg-amber-500/10",
    },
    error: { icon: <IconXCircle className="w-3.5 h-3.5" />, color: "#ef4444", bg: "bg-red-500/10" },
};

export function LogPanel() {
    const entries = useLogStore((s) => s.entries);
    const filterLevel = useLogStore((s) => s.filterLevel);
    const filterSource = useLogStore((s) => s.filterSource);
    const setFilterLevel = useLogStore((s) => s.setFilterLevel);
    const setFilterSource = useLogStore((s) => s.setFilterSource);
    const clearLogs = useLogStore((s) => s.clearLogs);
    const queryHistory = useGraphStore((s) => s.queryHistory);

    const filteredEntries = entries.filter((e) => {
        if (filterLevel !== "all" && e.level !== filterLevel) return false;
        if (filterSource && !e.source.toLowerCase().includes(filterSource.toLowerCase()))
            return false;
        return true;
    });

    return (
        <div className="flex flex-col h-full overflow-hidden">
            <div className="p-3 space-y-2 border-b border-slate-800 shrink-0">
                <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Activity Log
                    </h4>
                    <div className="flex items-center gap-2">
                        <span className="text-[10px] text-slate-600">
                            {filteredEntries.length} entries
                        </span>
                        <Button variant="ghost" size="xs" onClick={clearLogs}>
                            Clear
                        </Button>
                    </div>
                </div>

                <div className="flex items-center gap-1">
                    {(["all", "info", "success", "warn", "error"] as const).map((level) => (
                        <button
                            key={level}
                            onClick={() => setFilterLevel(level)}
                            className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
                                filterLevel === level
                                    ? "bg-slate-700 text-slate-100"
                                    : "text-slate-500 hover:text-slate-300 hover:bg-slate-800"
                            }`}
                        >
                            {level === "all" ? (
                                "All"
                            ) : (
                                <span className="flex items-center gap-1">
                                    {LEVEL_CONFIG[level].icon}
                                    {level}
                                </span>
                            )}
                        </button>
                    ))}
                </div>

                <Input
                    placeholder="Filter by source…"
                    value={filterSource}
                    onChange={(e) => setFilterSource(e.target.value)}
                />
            </div>

            <div className="flex border-b border-slate-800 shrink-0">
                <TabSection entries={filteredEntries} queryHistory={queryHistory} />
            </div>
        </div>
    );
}

function TabSection({
    entries,
    queryHistory,
}: Readonly<{
    entries: ReturnType<typeof useLogStore.getState>["entries"];
    queryHistory: QueryHistoryEntry[];
}>) {
    return (
        <div className="flex flex-col flex-1 overflow-hidden">
            {queryHistory.length > 0 && (
                <div className="p-3 border-b border-slate-800 shrink-0">
                    <h5 className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
                        Recent Queries
                    </h5>
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                        {queryHistory.slice(0, 10).map((q) => (
                            <QueryHistoryRow key={q.id} entry={q} />
                        ))}
                    </div>
                </div>
            )}

            <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
                {entries.length === 0 && (
                    <p className="text-xs text-slate-600 italic p-2 text-center">
                        No log entries yet. Actions will appear here.
                    </p>
                )}
                {entries.map((entry) => {
                    const cfg = LEVEL_CONFIG[entry.level];
                    return (
                        <div
                            key={entry.id}
                            className={`flex items-start gap-2 px-2 py-1.5 rounded text-[11px] transition-colors hover:bg-slate-800/50 ${cfg.bg}`}
                        >
                            <span className="shrink-0 mt-0.5" style={{ color: cfg.color }}>
                                {cfg.icon}
                            </span>

                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <span
                                        className="px-1 py-0.5 rounded text-[9px] font-mono font-medium"
                                        style={{
                                            color: cfg.color,
                                            backgroundColor: cfg.color + "15",
                                        }}
                                    >
                                        {entry.source}
                                    </span>
                                    <span className="text-slate-600 text-[9px]">
                                        {formatTime(entry.timestamp)}
                                    </span>
                                </div>
                                <p className="text-slate-300 mt-0.5 wrap-break-word">
                                    {entry.message}
                                </p>

                                {entry.details && Object.keys(entry.details).length > 0 && (
                                    <div className="mt-1 pl-2 border-l border-slate-700">
                                        {Object.entries(entry.details).map(([k, v]) => (
                                            <div key={k} className="flex gap-2 text-[10px]">
                                                <span className="text-slate-500">{k}:</span>
                                                <span className="text-slate-400 font-mono">
                                                    {String(v)}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function QueryHistoryRow({ entry }: Readonly<{ entry: QueryHistoryEntry }>) {
    const typeColors: Record<string, string> = {
        full: "#3b82f6",
        subgraph: "#8b5cf6",
        path: "#22c55e",
        impact: "#ef4444",
        layout: "#06b6d4",
    };

    const color = typeColors[entry.type] ?? "#64748b";

    return (
        <div className="flex items-center gap-2 px-2 py-1 rounded text-[10px] hover:bg-slate-800 transition-colors">
            <span
                className="px-1.5 py-0.5 rounded font-medium"
                style={{ color, backgroundColor: color + "20" }}
            >
                {entry.type}
            </span>
            <span className="text-slate-400 flex-1 truncate font-mono">
                {entry.nodeCount}n / {entry.edgeCount}e
            </span>
            <span className="text-slate-600 shrink-0">{formatTime(entry.timestamp)}</span>
        </div>
    );
}

function formatTime(iso: string): string {
    try {
        const d = new Date(iso);
        return d.toLocaleTimeString("ru-RU", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
    } catch {
        return iso;
    }
}
