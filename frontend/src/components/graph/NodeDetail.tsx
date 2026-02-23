import { useGraphStore } from "../../store/graphStore";
import { Badge } from "../common/Badge";
import { StatusDot } from "../common/StatusDot";
import { EmptyState } from "../common/EmptyState";
import { getEdgeColor } from "../../utils/colors";
import { IconInfo } from "../icons";
import type {
    GraphNode,
    GraphEdge,
    ServiceProperties,
    DeploymentProperties,
    PodProperties,
    DatabaseProperties,
    CacheProperties,
    QueueTopicProperties,
} from "../../types";

function s(v: unknown): string {
    if (v == null) return "";
    if (typeof v === "object") return JSON.stringify(v);
    return `${v as string | number | boolean}`;
}

function n(v: unknown): number {
    return Number(v) || 0;
}

export function NodeDetail() {
    const selectedId = useGraphStore((s) => s.selectedNodeId);
    const nodes = useGraphStore((s) => s.nodes);
    const edges = useGraphStore((s) => s.edges);

    if (!selectedId) {
        return (
            <EmptyState
                icon={<IconInfo className="w-8 h-8" />}
                title="No node selected"
                description="Click a node on the graph to view its details."
                className="pt-8"
            />
        );
    }

    const node = nodes.find((n) => n.id === selectedId);
    if (!node) return null;

    const incoming = edges.filter((e) => e.target_id === selectedId);
    const outgoing = edges.filter((e) => e.source_id === selectedId);

    return (
        <div className="flex flex-col gap-4 p-4 overflow-y-auto max-h-full">
            <div>
                <div className="flex items-center gap-2 mb-1">
                    <Badge label={node.type} nodeType={node.type} />
                    <StatusDot status={node.status} showLabel size="sm" />
                </div>
                <h3 className="text-base font-semibold text-slate-100">{node.name}</h3>
                <p className="text-xs text-slate-500 font-mono mt-0.5 break-all">{node.id}</p>
                {node.environment && (
                    <span className="inline-block mt-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700">
                        {node.environment}
                    </span>
                )}
            </div>

            <TypeSpecificMetrics node={node} />

            <PropertiesSection properties={node.properties} />

            <EdgeSection
                title={`Incoming (${incoming.length})`}
                edges={incoming}
                direction="from"
                nodes={nodes}
            />
            <EdgeSection
                title={`Outgoing (${outgoing.length})`}
                edges={outgoing}
                direction="to"
                nodes={nodes}
            />
        </div>
    );
}

function TypeSpecificMetrics({ node }: Readonly<{ node: GraphNode }>) {
    switch (node.type) {
        case "Service": {
            const p = node.properties as ServiceProperties;
            return (
                <Section title="Service Metrics">
                    {p.language && <InfoRow label="Language" value={s(p.language)} />}
                    {p.framework && <InfoRow label="Framework" value={s(p.framework)} />}
                    {p.version && <InfoRow label="Version" value={s(p.version)} />}
                    {p.tier != null && <InfoRow label="Tier" value={`T${s(p.tier)}`} />}
                    {p.memory_allocated_mb != null && (
                        <MetricBar
                            label="Memory"
                            value={n(p.memory_allocated_mb)}
                            max={2048}
                            unit="MB"
                        />
                    )}
                    {p.cpu_allocated_cores != null && (
                        <MetricBar
                            label="CPU"
                            value={n(p.cpu_allocated_cores)}
                            max={4}
                            unit="cores"
                            decimals={2}
                        />
                    )}
                </Section>
            );
        }

        case "Deployment": {
            const p = node.properties as DeploymentProperties;
            return (
                <Section title="Deployment Metrics">
                    {p.strategy && <InfoRow label="Strategy" value={s(p.strategy)} />}
                    {p.namespace && <InfoRow label="Namespace" value={s(p.namespace)} />}
                    {p.image_tag && <InfoRow label="Image" value={s(p.image_tag)} />}
                    {p.replicas_desired != null && p.replicas_ready != null && (
                        <ReplicaIndicator
                            desired={n(p.replicas_desired)}
                            ready={n(p.replicas_ready)}
                        />
                    )}
                </Section>
            );
        }

        case "Pod": {
            const p = node.properties as PodProperties;
            return (
                <Section title="Pod Metrics">
                    {p.phase && <InfoRow label="Phase" value={s(p.phase)} />}
                    {p.namespace && <InfoRow label="Namespace" value={s(p.namespace)} />}
                    {p.node_name && <InfoRow label="Node" value={s(p.node_name)} />}
                    {p.restart_count != null && (
                        <InfoRow
                            label="Restarts"
                            value={s(p.restart_count)}
                            warn={n(p.restart_count) > 0}
                        />
                    )}
                    {p.cpu_usage_m != null && (
                        <MetricBar label="CPU" value={n(p.cpu_usage_m)} max={1000} unit="m" />
                    )}
                    {p.memory_usage_mi != null && (
                        <MetricBar
                            label="Memory"
                            value={n(p.memory_usage_mi)}
                            max={1024}
                            unit="Mi"
                        />
                    )}
                </Section>
            );
        }

        case "Database": {
            const p = node.properties as DatabaseProperties;
            return (
                <Section title="Database Info">
                    {p.engine && <InfoRow label="Engine" value={s(p.engine)} />}
                    {p.version && <InfoRow label="Version" value={s(p.version)} />}
                    {p.capacity_gb != null && (
                        <InfoRow label="Capacity" value={`${s(p.capacity_gb)} GB`} />
                    )}
                    {p.max_connections != null && (
                        <InfoRow label="Max Connections" value={s(p.max_connections)} />
                    )}
                    {p.multi_az != null && (
                        <InfoRow label="Multi-AZ" value={p.multi_az ? "Yes" : "No"} />
                    )}
                    {p.is_managed != null && (
                        <InfoRow label="Managed" value={p.is_managed ? "Yes" : "No"} />
                    )}
                </Section>
            );
        }

        case "Cache": {
            const p = node.properties as CacheProperties;
            return (
                <Section title="Cache Metrics">
                    {p.engine && <InfoRow label="Engine" value={s(p.engine)} />}
                    {p.eviction_policy && <InfoRow label="Eviction" value={s(p.eviction_policy)} />}
                    {p.hit_rate_target != null && (
                        <MetricBar
                            label="Hit Rate"
                            value={n(p.hit_rate_target)}
                            max={100}
                            unit="%"
                        />
                    )}
                    {p.keys_count != null && (
                        <InfoRow label="Keys" value={n(p.keys_count).toLocaleString()} />
                    )}
                    {p.connected_clients != null && (
                        <InfoRow label="Clients" value={s(p.connected_clients)} />
                    )}
                </Section>
            );
        }

        case "QueueTopic": {
            const p = node.properties as QueueTopicProperties;
            return (
                <Section title="Queue/Topic Metrics">
                    {p.broker && <InfoRow label="Broker" value={s(p.broker)} />}
                    {p.partitions != null && <InfoRow label="Partitions" value={s(p.partitions)} />}
                    {p.replication_factor != null && (
                        <InfoRow label="Replication" value={s(p.replication_factor)} />
                    )}
                    {p.message_rate != null && (
                        <MetricBar
                            label="Msg Rate"
                            value={n(p.message_rate)}
                            max={1000}
                            unit="msg/s"
                        />
                    )}
                </Section>
            );
        }

        case "SLASLO": {
            const p = node.properties;
            return (
                <Section title="SLA/SLO">
                    {p.metric_name != null && <InfoRow label="Metric" value={s(p.metric_name)} />}
                    {p.target_percentage != null && (
                        <InfoRow label="Target" value={`${s(p.target_percentage)}%`} />
                    )}
                    {p.current_value != null && (
                        <SLOGauge
                            current={n(p.current_value)}
                            target={n(p.target_percentage ?? 99)}
                            metric={s(p.metric_name ?? "value")}
                        />
                    )}
                    {p.violation_count != null && (
                        <InfoRow
                            label="Violations"
                            value={s(p.violation_count)}
                            warn={n(p.violation_count) > 0}
                        />
                    )}
                </Section>
            );
        }

        default:
            return null;
    }
}

function PropertiesSection({ properties }: Readonly<{ properties: Record<string, unknown> }>) {
    const entries = Object.entries(properties).filter(
        ([, v]) => v !== null && v !== undefined && v !== "",
    );
    if (entries.length === 0) return null;

    return (
        <Section title="All Properties">
            {entries.map(([k, v]) => (
                <InfoRow key={k} label={formatLabel(k)} value={formatValue(v)} />
            ))}
        </Section>
    );
}

function EdgeSection({
    title,
    edges,
    direction,
    nodes,
}: Readonly<{
    title: string;
    edges: GraphEdge[];
    direction: "from" | "to";
    nodes: GraphNode[];
}>) {
    return (
        <Section title={title}>
            {edges.length === 0 && <p className="text-xs text-slate-600">None</p>}
            {edges.map((e) => (
                <EdgeDetailRow
                    key={`${e.source_id}-${e.target_id}-${e.type}`}
                    edge={e}
                    direction={direction}
                    nodes={nodes}
                />
            ))}
        </Section>
    );
}

function EdgeDetailRow({
    edge,
    direction,
    nodes,
}: Readonly<{
    edge: GraphEdge;
    direction: "from" | "to";
    nodes: GraphNode[];
}>) {
    const selectNode = useGraphStore((s) => s.selectNode);
    const otherId = direction === "from" ? edge.source_id : edge.target_id;
    const otherNode = nodes.find((n) => n.id === otherId);
    const color = getEdgeColor(edge.type);
    const p = edge.properties;

    const hasCallMetrics = edge.type.toUpperCase() === "CALLS" || edge.type === "calls";
    const rps = p.rps == null ? null : Number(p.rps);
    const latency = p.latency_p99_ms == null ? null : Number(p.latency_p99_ms);
    const errorRate = p.error_rate_percent == null ? null : Number(p.error_rate_percent);

    return (
        <div className="bg-slate-800/50 rounded-lg p-2 space-y-1">
            <button
                onClick={() => selectNode(otherId)}
                className="flex items-center gap-2 w-full text-left text-xs hover:bg-slate-700/50 rounded px-1 py-0.5 transition-colors"
            >
                <span className="font-medium" style={{ color }}>
                    {edge.type}
                </span>
                <span className="text-slate-500">{direction === "from" ? "←" : "→"}</span>
                <span className="text-slate-300 truncate">{otherNode?.name ?? otherId}</span>
            </button>

            {hasCallMetrics && (rps != null || latency != null || errorRate != null) && (
                <div className="flex items-center gap-3 px-1 text-[10px]">
                    {rps != null && (
                        <span className="text-blue-400">
                            <span className="text-slate-500">RPS:</span> {rps.toFixed(1)}
                        </span>
                    )}
                    {latency != null && (
                        <span style={{ color: latency > 200 ? "#f59e0b" : "#22c55e" }}>
                            <span className="text-slate-500">P99:</span> {latency.toFixed(0)}ms
                        </span>
                    )}
                    {errorRate != null && (
                        <span style={{ color: errorRate > 1 ? "#ef4444" : "#22c55e" }}>
                            <span className="text-slate-500">Err:</span> {errorRate.toFixed(2)}%
                        </span>
                    )}
                </div>
            )}

            {!hasCallMetrics && Object.keys(p).length > 0 && (
                <div className="px-1 space-y-0.5">
                    {Object.entries(p)
                        .filter(([, v]) => v != null && v !== "")
                        .slice(0, 4)
                        .map(([k, v]) => (
                            <div key={k} className="flex justify-between text-[10px]">
                                <span className="text-slate-500">{formatLabel(k)}</span>
                                <span className="text-slate-400 font-mono">{formatValue(v)}</span>
                            </div>
                        ))}
                </div>
            )}
        </div>
    );
}

function MetricBar({
    label,
    value,
    max,
    unit,
    decimals = 0,
}: Readonly<{
    label: string;
    value: number;
    max: number;
    unit: string;
    decimals?: number;
}>) {
    const pct = Math.min(100, (value / max) * 100);
    let color = "#22c55e";
    if (pct > 80) color = "#ef4444";
    else if (pct > 60) color = "#f59e0b";

    return (
        <div className="space-y-0.5">
            <div className="flex justify-between text-xs">
                <span className="text-slate-500">{label}</span>
                <span className="text-slate-300 font-mono">
                    {value.toFixed(decimals)} {unit}
                </span>
            </div>
            <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${pct}%`, backgroundColor: color }}
                />
            </div>
        </div>
    );
}

function ReplicaIndicator({ desired, ready }: Readonly<{ desired: number; ready: number }>) {
    const isHealthy = ready >= desired;
    return (
        <div className="space-y-1">
            <div className="flex justify-between text-xs">
                <span className="text-slate-500">Replicas</span>
                <span
                    className="font-mono font-medium"
                    style={{ color: isHealthy ? "#22c55e" : "#ef4444" }}
                >
                    {ready}/{desired}
                </span>
            </div>
            <div className="flex gap-1">
                {Array.from({ length: desired }).map((_, i) => {
                    const rid = `replica-${i}`;
                    return (
                        <div
                            key={rid}
                            className="h-2 flex-1 rounded-sm transition-colors duration-300"
                            style={{
                                backgroundColor: i < ready ? "#22c55e" : "#ef444450",
                            }}
                        />
                    );
                })}
            </div>
        </div>
    );
}

function SLOGauge({
    current,
    target,
    metric,
}: Readonly<{
    current: number;
    target: number;
    metric: string;
}>) {
    const isLatency = metric.includes("latency");
    const isMet = isLatency ? current <= target : current >= target;
    const displayValue = isLatency ? `${current.toFixed(1)}ms` : `${current.toFixed(4)}%`;

    return (
        <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/50 border border-slate-700">
            <div>
                <p className="text-slate-500 text-[10px]">Current</p>
                <p
                    className="text-sm font-mono font-bold"
                    style={{ color: isMet ? "#22c55e" : "#ef4444" }}
                >
                    {displayValue}
                </p>
            </div>
            <div
                className="px-2 py-1 rounded text-[10px] font-medium"
                style={{
                    backgroundColor: isMet ? "#22c55e20" : "#ef444420",
                    color: isMet ? "#22c55e" : "#ef4444",
                }}
            >
                {isMet ? "MEETING SLO" : "SLO VIOLATION"}
            </div>
        </div>
    );
}

function Section({ title, children }: Readonly<{ title: string; children: React.ReactNode }>) {
    return (
        <div>
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                {title}
            </h4>
            <div className="space-y-1">{children}</div>
        </div>
    );
}

function InfoRow({
    label,
    value,
    warn,
}: Readonly<{ label: string; value: string; warn?: boolean }>) {
    return (
        <div className="flex justify-between text-xs">
            <span className="text-slate-500">{label}</span>
            <span className="font-mono" style={{ color: warn ? "#ef4444" : "#cbd5e1" }}>
                {value}
            </span>
        </div>
    );
}

function formatLabel(key: string): string {
    return key.replaceAll("_", " ").replaceAll(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(v: unknown): string {
    if (v === null || v === undefined) return "—";
    if (typeof v === "boolean") return v ? "Yes" : "No";
    if (typeof v === "number") return v.toLocaleString();
    if (Array.isArray(v)) return v.join(", ");
    if (typeof v === "object") return JSON.stringify(v);
    return `${v as string}`;
}
