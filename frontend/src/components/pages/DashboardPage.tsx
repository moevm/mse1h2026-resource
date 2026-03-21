import { useState, useCallback } from "react";
import { useGraph } from "../../hooks/useGraph";
import { useGraphStore } from "../../store/graphStore";
import { useLogStore } from "../../store/logStore";
import { Spinner } from "../common/Spinner";
import { Badge } from "../common/Badge";
import { Button } from "../common/Button";
import { EmptyState } from "../common/EmptyState";
import {
    IconRefresh,
    IconCheckCircle,
    IconXCircle,
    IconExclamation,
    IconInfo,
    IconClock,
    IconDatabase,
    IconGraph,
} from "../icons";
import { getEdgeColor, getNodeColor } from "../../utils/colors";

const LOG_CFG = {
    info: { Icon: IconInfo, cls: "text-blue-400" },
    success: { Icon: IconCheckCircle, cls: "text-emerald-400" },
    warn: { Icon: IconExclamation, cls: "text-amber-400" },
    error: { Icon: IconXCircle, cls: "text-red-400" },
} as const;

export function DashboardPage() {
    const { loadStats, loadAnalytics } = useGraph();

    const stats = useGraphStore((s) => s.stats);
    const analytics = useGraphStore((s) => s.analytics);
    const nodes = useGraphStore((s) => s.nodes);
    const edges = useGraphStore((s) => s.edges);
    const lastRefreshed = useGraphStore((s) => s.lastRefreshedAt);
    const queryHistory = useGraphStore((s) => s.queryHistory);
    const logEntries = useLogStore((s) => s.entries);

    const [refreshing, setRefreshing] = useState(false);

    const handleRefresh = useCallback(async () => {
        setRefreshing(true);
        await Promise.all([loadStats(), loadAnalytics()]);
        setRefreshing(false);
    }, [loadStats, loadAnalytics]);

    const totalNodes = stats?.total_nodes ?? nodes.length;
    const totalEdges = stats?.total_edges ?? edges.length;

    const nodeEntries = (
        stats
            ? Object.entries(stats.nodes_by_type)
            : [...new Set(nodes.map((n) => n.type))].map((t): [string, number] => [
                  t,
                  nodes.filter((n) => n.type === t).length,
              ])
    ).sort(([, a], [, b]) => b - a);

    const edgeEntries = (
        stats
            ? Object.entries(stats.edges_by_type)
            : [...new Set(edges.map((e) => e.type))].map((t): [string, number] => [
                  t,
                  edges.filter((e) => e.type === t).length,
              ])
    ).sort(([, a], [, b]) => b - a);

    const hasData = totalNodes > 0 || totalEdges > 0;
    const maxNodeCnt = nodeEntries[0]?.[1] ?? 1;
    const maxEdgeCnt = edgeEntries[0]?.[1] ?? 1;

    return (
        <div className="h-full overflow-y-auto bg-slate-950">
            <div className="max-w-7xl mx-auto px-6 py-8 space-y-8 animate-fade-in">
                {/* Header */}
                <div className="flex items-center justify-between gap-4">
                    <div>
                        <h1 className="text-xl font-semibold text-slate-100 tracking-tight">
                            Dashboard
                        </h1>
                        <p className="text-sm text-slate-400 mt-1">
                            Topology statistics and recent activity
                        </p>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                        {lastRefreshed && (
                            <span className="hidden sm:flex items-center gap-2 text-xs text-slate-500">
                                <IconClock className="w-3.5 h-3.5" />
                                {new Date(lastRefreshed).toLocaleTimeString("ru-RU")}
                            </span>
                        )}
                        <Button
                            variant="secondary"
                            size="sm"
                            icon={<IconRefresh className="w-4 h-4" />}
                            loading={refreshing}
                            onClick={() => {
                                void handleRefresh();
                            }}
                        >
                            Refresh
                        </Button>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-stagger">
                    <StatCard
                        label="Nodes"
                        value={totalNodes}
                        accent="#3b82f6"
                        icon="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5zM6.75 12a.75.75 0 100-1.5.75.75 0 000 1.5zM17.25 12a.75.75 0 100-1.5.75.75 0 000 1.5z"
                    />
                    <StatCard
                        label="Edges"
                        value={totalEdges}
                        accent="#8b5cf6"
                        icon="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
                    />
                    <StatCard
                        label="Node Types"
                        value={nodeEntries.length}
                        accent="#06b6d4"
                        icon="M3.75 6h16.5M3.75 12h16.5M3.75 18h16.5"
                    />
                    <StatCard
                        label="Edge Types"
                        value={edgeEntries.length}
                        accent="#22c55e"
                        icon="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z"
                    />
                </div>

                {refreshing && (
                    <div className="flex justify-center py-12">
                        <Spinner size="lg" label="Loading statistics" />
                    </div>
                )}

                {!refreshing && !hasData && (
                    <EmptyState
                        icon={<IconDatabase className="w-12 h-12" />}
                        title="No data loaded"
                        description="Go to Graph page to load topology data, then click Refresh."
                        action={
                            <Button
                                variant="primary"
                                size="sm"
                                icon={<IconRefresh className="w-4 h-4" />}
                                loading={refreshing}
                                onClick={() => {
                                    void handleRefresh();
                                }}
                            >
                                Load Statistics
                            </Button>
                        }
                    />
                )}

                {/* Type Distribution */}
                {(nodeEntries.length > 0 || edgeEntries.length > 0) && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                        {nodeEntries.length > 0 && (
                            <Panel title="Nodes by Type" count={nodeEntries.length}>
                                <div className="space-y-3">
                                    {nodeEntries.map(([type, count]) => (
                                        <TypeRow
                                            key={type}
                                            label={type}
                                            count={count}
                                            max={maxNodeCnt}
                                            color={getNodeColor(type)}
                                            badge
                                        />
                                    ))}
                                </div>
                            </Panel>
                        )}
                        {edgeEntries.length > 0 && (
                            <Panel title="Edges by Type" count={edgeEntries.length}>
                                <div className="space-y-3">
                                    {edgeEntries.map(([type, count]) => (
                                        <TypeRow
                                            key={type}
                                            label={type}
                                            count={count}
                                            max={maxEdgeCnt}
                                            color={getEdgeColor(type)}
                                            badge={false}
                                        />
                                    ))}
                                </div>
                            </Panel>
                        )}
                    </div>
                )}

                {/* Analytics */}
                {analytics && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                        {Object.keys(analytics.pagerank).length > 0 && (
                            <Panel title="Top by PageRank" subtitle="Influence centrality">
                                <RankList
                                    entries={Object.entries(analytics.pagerank)
                                        .sort(([, a], [, b]) => b - a)
                                        .slice(0, 8)}
                                    accent="#3b82f6"
                                />
                            </Panel>
                        )}
                        {Object.keys(analytics.betweenness).length > 0 && (
                            <Panel title="Top by Betweenness" subtitle="Bridge centrality">
                                <RankList
                                    entries={Object.entries(analytics.betweenness)
                                        .sort(([, a], [, b]) => b - a)
                                        .slice(0, 8)}
                                    accent="#8b5cf6"
                                />
                            </Panel>
                        )}
                    </div>
                )}

                {/* Activity Panels */}
                {hasData && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                        <Panel title="Recent Queries" count={queryHistory.length}>
                            {queryHistory.length === 0 ? (
                                <EmptyState
                                    icon={<IconGraph className="w-8 h-8" />}
                                    title="No queries yet"
                                    description="Queries appear here after use."
                                    className="py-8"
                                />
                            ) : (
                                <div className="space-y-1">
                                    {queryHistory.slice(0, 6).map((q) => (
                                        <div
                                            key={q.id}
                                            className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-slate-800/60 transition-colors"
                                        >
                                            <Badge label={q.type} color="#3b82f6" dot={false} />
                                            <span className="text-slate-300 tabular-nums text-xs shrink-0 font-mono">
                                                {q.nodeCount}N / {q.edgeCount}E
                                            </span>
                                            {q.params && (
                                                <span className="text-slate-500 truncate flex-1 font-mono text-xs">
                                                    {JSON.stringify(q.params).slice(0, 40)}
                                                </span>
                                            )}
                                            <span className="text-slate-500 text-xs tabular-nums shrink-0 flex items-center gap-1.5">
                                                <IconClock className="w-3.5 h-3.5" />
                                                {new Date(q.timestamp).toLocaleTimeString("ru-RU")}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </Panel>

                        <Panel title="Activity" count={logEntries.length}>
                            {logEntries.length === 0 ? (
                                <EmptyState
                                    icon={<IconInfo className="w-8 h-8" />}
                                    title="No activity"
                                    description="System events appear here."
                                    className="py-8"
                                />
                            ) : (
                                <div className="space-y-1">
                                    {logEntries.slice(0, 8).map((entry) => {
                                        const cfg =
                                            LOG_CFG[entry.level as keyof typeof LOG_CFG] ??
                                            LOG_CFG.info;
                                        return (
                                            <div
                                                key={entry.id}
                                                className="flex items-start gap-3 px-3 py-2.5 rounded-lg hover:bg-slate-800/60 transition-colors"
                                            >
                                                <cfg.Icon
                                                    className={`w-4 h-4 shrink-0 mt-0.5 ${cfg.cls}`}
                                                />
                                                <span className="text-slate-300 text-sm flex-1 leading-relaxed">
                                                    {entry.message}
                                                </span>
                                                <span className="text-slate-500 text-xs tabular-nums shrink-0 mt-0.5">
                                                    {new Date(entry.timestamp).toLocaleTimeString(
                                                        "ru-RU",
                                                    )}
                                                </span>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </Panel>
                    </div>
                )}
            </div>
        </div>
    );
}

interface StatCardProps {
    label: string;
    value: number;
    accent: string;
    icon: string;
}

function StatCard({ label, value, accent, icon }: Readonly<StatCardProps>) {
    return (
        <div className="relative overflow-hidden rounded-xl bg-slate-900/80 border border-slate-800/80 p-5 hover:border-slate-700/80 transition-all duration-300 group animate-fade-in">
            {/* Gradient background */}
            <div
                className="absolute inset-0 pointer-events-none opacity-60 group-hover:opacity-80 transition-opacity duration-300"
                style={{
                    background: `radial-gradient(ellipse 80% 60% at 100% 0%, ${accent}20, transparent)`,
                }}
            />
            <div className="relative flex items-start justify-between gap-3">
                <div>
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
                        {label}
                    </p>
                    <p
                        className="text-3xl font-bold mt-2 tabular-nums tracking-tight"
                        style={{ color: accent }}
                    >
                        {value.toLocaleString()}
                    </p>
                </div>
                <div
                    className="h-10 w-10 rounded-xl flex items-center justify-center shrink-0 transition-transform duration-300 group-hover:scale-110"
                    style={{ backgroundColor: `${accent}20` }}
                >
                    <svg
                        className="w-5 h-5"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={1.5}
                        style={{ color: accent }}
                    >
                        <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
                    </svg>
                </div>
            </div>
        </div>
    );
}

interface PanelProps {
    title: string;
    subtitle?: string;
    count?: number;
    children: React.ReactNode;
}

function Panel({ title, subtitle, count, children }: Readonly<PanelProps>) {
    return (
        <div className="rounded-xl bg-slate-900/80 border border-slate-800/80 p-5 shadow-lg shadow-slate-950/50">
            <div className="flex items-baseline gap-3 mb-4">
                <h2 className="text-sm font-semibold text-slate-200">{title}</h2>
                {subtitle && <span className="text-xs text-slate-500">{subtitle}</span>}
                {count !== undefined && count > 0 && (
                    <span className="ml-auto text-xs text-slate-500 tabular-nums font-mono bg-slate-800/50 px-2 py-0.5 rounded">
                        {count}
                    </span>
                )}
            </div>
            {children}
        </div>
    );
}

interface TypeRowProps {
    label: string;
    count: number;
    max: number;
    color: string;
    badge: boolean;
}

function TypeRow({ label, count, max, color, badge }: Readonly<TypeRowProps>) {
    const pct = Math.max(3, Math.round((count / Math.max(max, 1)) * 100));
    return (
        <div className="flex items-center gap-4 group">
            <div className="w-28 shrink-0 min-w-0">
                {badge ? (
                    <Badge label={label} color={color} size="sm" />
                ) : (
                    <span className="flex items-center gap-2 min-w-0">
                        <span
                            className="h-2.5 w-2.5 rounded-full shrink-0 shadow-sm"
                            style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}60` }}
                        />
                        <span className="text-sm text-slate-300 truncate">{label}</span>
                    </span>
                )}
            </div>
            <div className="flex-1 h-2 bg-slate-800/80 rounded-full overflow-hidden">
                <div
                    className="h-full rounded-full transition-all duration-700 ease-out"
                    style={{ width: `${pct}%`, backgroundColor: `${color}` }}
                />
            </div>
            <span className="text-sm text-slate-400 tabular-nums w-12 text-right font-medium shrink-0">
                {count.toLocaleString()}
            </span>
        </div>
    );
}

interface RankListProps {
    entries: [string, number][];
    accent: string;
}

function RankList({ entries, accent }: Readonly<RankListProps>) {
    const max = entries[0]?.[1] ?? 1;
    return (
        <div className="space-y-2">
            {entries.map(([id, score], i) => {
                const pct = Math.max(3, Math.round((score / Math.max(max, 1)) * 100));
                return (
                    <div
                        key={id}
                        className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-slate-800/60 transition-colors"
                    >
                        <span
                            className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold"
                            style={{
                                backgroundColor: i < 3 ? `${accent}25` : "transparent",
                                color: i < 3 ? accent : "#64748b",
                            }}
                        >
                            {i + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                            <p className="text-slate-200 font-mono truncate text-sm">{id}</p>
                            <div className="h-1.5 bg-slate-800 rounded-full mt-1.5 overflow-hidden">
                                <div
                                    className="h-full rounded-full transition-all duration-500"
                                    style={{
                                        width: `${pct}%`,
                                        backgroundColor: accent,
                                        opacity: 0.7,
                                    }}
                                />
                            </div>
                        </div>
                        <span
                            className="tabular-nums font-semibold text-sm shrink-0"
                            style={{ color: accent }}
                        >
                            {score.toFixed(3)}
                        </span>
                    </div>
                );
            })}
        </div>
    );
}
