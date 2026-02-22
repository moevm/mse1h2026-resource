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
            <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">
                <div className="flex items-center justify-between gap-4">
                    <div>
                        <h1 className="text-lg font-semibold text-slate-100 tracking-tight">
                            Dashboard
                        </h1>
                        <p className="text-xs text-slate-500 mt-0.5">
                            Topology statistics and recent activity
                        </p>
                    </div>
                    <div className="flex items-center gap-2.5 shrink-0">
                        {lastRefreshed && (
                            <span className="hidden sm:flex items-center gap-1.5 text-[11px] text-slate-600">
                                <IconClock className="w-3 h-3" />
                                {new Date(lastRefreshed).toLocaleTimeString("ru-RU")}
                            </span>
                        )}
                        <Button
                            variant="secondary"
                            size="sm"
                            icon={<IconRefresh className="w-3.5 h-3.5" />}
                            loading={refreshing}
                            onClick={() => {
                                void handleRefresh();
                            }}
                        >
                            Refresh
                        </Button>
                    </div>
                </div>

                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
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
                    <div className="flex justify-center py-10">
                        <Spinner size="md" label="Loading statistics" />
                    </div>
                )}

                {!refreshing && !hasData && (
                    <EmptyState
                        icon={<IconDatabase className="w-10 h-10" />}
                        title="No data loaded"
                        description="Go to Graph page to load topology data, then click Refresh."
                        action={
                            <Button
                                variant="primary"
                                size="sm"
                                icon={<IconRefresh className="w-3.5 h-3.5" />}
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

                {(nodeEntries.length > 0 || edgeEntries.length > 0) && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        {nodeEntries.length > 0 && (
                            <Panel title="Nodes by Type" count={nodeEntries.length}>
                                <div className="space-y-2 pt-1">
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
                                <div className="space-y-2 pt-1">
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

                {analytics && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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

                {hasData && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <Panel title="Recent Queries" count={queryHistory.length}>
                            {queryHistory.length === 0 ? (
                                <EmptyState
                                    icon={<IconGraph className="w-7 h-7" />}
                                    title="No queries yet"
                                    description="Queries appear here after use."
                                    className="py-5"
                                />
                            ) : (
                                <div className="space-y-0.5 pt-1">
                                    {queryHistory.slice(0, 6).map((q) => (
                                        <div
                                            key={q.id}
                                            className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-slate-800/50 transition-colors"
                                        >
                                            <Badge label={q.type} color="#3b82f6" dot={false} />
                                            <span className="text-slate-400 tabular-nums text-[11px] shrink-0 font-mono">
                                                {q.nodeCount}N / {q.edgeCount}E
                                            </span>
                                            {q.params && (
                                                <span className="text-slate-600 truncate flex-1 font-mono text-[11px]">
                                                    {JSON.stringify(q.params).slice(0, 45)}
                                                </span>
                                            )}
                                            <span className="text-slate-600 text-[10px] tabular-nums shrink-0 flex items-center gap-1">
                                                <IconClock className="w-3 h-3" />
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
                                    icon={<IconInfo className="w-7 h-7" />}
                                    title="No activity"
                                    description="System events appear here."
                                    className="py-5"
                                />
                            ) : (
                                <div className="space-y-0.5 pt-1">
                                    {logEntries.slice(0, 8).map((entry) => {
                                        const cfg =
                                            LOG_CFG[entry.level as keyof typeof LOG_CFG] ??
                                            LOG_CFG.info;
                                        return (
                                            <div
                                                key={entry.id}
                                                className="flex items-start gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-800/50 transition-colors"
                                            >
                                                <cfg.Icon
                                                    className={`w-3.5 h-3.5 shrink-0 mt-0.5 ${cfg.cls}`}
                                                />
                                                <span className="text-slate-400 text-xs flex-1 leading-relaxed">
                                                    {entry.message}
                                                </span>
                                                <span className="text-slate-600 text-[10px] tabular-nums shrink-0 mt-0.5">
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
        <div className="relative overflow-hidden rounded-xl bg-slate-900 border border-slate-800/80 p-4">
            <div
                className="absolute inset-0 pointer-events-none"
                style={{
                    background: `radial-gradient(ellipse 80% 60% at 100% 0%, ${accent}18, transparent)`,
                }}
            />
            <div className="relative flex items-start justify-between gap-2">
                <div>
                    <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest leading-none">
                        {label}
                    </p>
                    <p
                        className="text-3xl font-bold mt-2.5 tabular-nums tracking-tight"
                        style={{ color: accent }}
                    >
                        {value.toLocaleString()}
                    </p>
                </div>
                <div
                    className="h-8 w-8 rounded-lg flex items-center justify-center shrink-0"
                    style={{ backgroundColor: `${accent}18` }}
                >
                    <svg
                        className="w-4 h-4"
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
        <div className="rounded-xl bg-slate-900 border border-slate-800/80 p-4">
            <div className="flex items-baseline gap-2 mb-3">
                <h2 className="text-sm font-semibold text-slate-200 tracking-tight">{title}</h2>
                {subtitle && <span className="text-[11px] text-slate-600">{subtitle}</span>}
                {count !== undefined && count > 0 && (
                    <span className="ml-auto text-[10px] text-slate-600 tabular-nums font-mono">
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
        <div className="flex items-center gap-3">
            <div className="w-32 shrink-0 min-w-0">
                {badge ? (
                    <Badge label={label} color={color} />
                ) : (
                    <span className="flex items-center gap-1.5 min-w-0">
                        <span
                            className="h-1.5 w-1.5 rounded-full shrink-0"
                            style={{ backgroundColor: color }}
                        />
                        <span className="text-xs text-slate-400 truncate">{label}</span>
                    </span>
                )}
            </div>
            <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                    className="h-full rounded-full transition-[width] duration-500"
                    style={{ width: `${pct}%`, backgroundColor: `${color}cc` }}
                />
            </div>
            <span className="text-xs text-slate-500 tabular-nums w-8 text-right font-mono shrink-0">
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
        <div className="space-y-1.5 pt-1">
            {entries.map(([id, score], i) => {
                const pct = Math.max(3, Math.round((score / Math.max(max, 1)) * 100));
                return (
                    <div
                        key={id}
                        className="flex items-center gap-2.5 px-1 py-1 rounded-lg hover:bg-slate-800/50 transition-colors"
                    >
                        <span className="text-slate-700 tabular-nums w-4 text-right shrink-0 text-[11px] font-mono">
                            {i + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                            <p className="text-slate-300 font-mono truncate text-xs">{id}</p>
                            <div className="h-1 bg-slate-800 rounded-full mt-1 overflow-hidden">
                                <div
                                    className="h-full rounded-full"
                                    style={{
                                        width: `${pct}%`,
                                        backgroundColor: accent,
                                        opacity: 0.55,
                                    }}
                                />
                            </div>
                        </div>
                        <span
                            className="tabular-nums font-medium text-xs shrink-0"
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
