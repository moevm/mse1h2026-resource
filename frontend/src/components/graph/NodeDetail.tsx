import { useGraphDataStore, useGraphUiStore } from '../../features/graph/store';
import { formatLabel, formatValue } from '../../lib/utils/format';
import { InfoRow } from '../../shared/components/InfoRow';
import { MetricBar } from '../../shared/components/MetricBar';
import type {
  CacheProperties,
  DatabaseProperties,
  DeploymentProperties,
  EndpointProperties,
  ExternalAPIProperties,
  GraphEdge,
  GraphNode,
  LibraryProperties,
  PodProperties,
  QueueTopicProperties,
  SecretConfigProperties,
  ServiceProperties,
  TableProperties,
  TeamOwnerProperties,
} from '../../types';
import { getEdgeColor } from '../../utils/colors';
import { Badge } from '../common/Badge';
import { EmptyState } from '../common/EmptyState';
import { StatusDot } from '../common/StatusDot';
import { IconInfo } from '../icons';

function s(v: unknown): string {
  if (v == null) return '';
  if (typeof v === 'object') return JSON.stringify(v);
  return `${v as string | number | boolean}`;
}

function n(v: unknown): number {
  return Number(v) || 0;
}

function formatTimestamp(v: unknown): string {
  if (v == null) return '';
  try {
    return new Date(String(v)).toLocaleString('ru-RU', {
      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return String(v);
  }
}

function Divider() {
  return <div className="border-t border-slate-800/70" />;
}

export function NodeDetail() {
  const selectedId = useGraphUiStore((s) => s.selectedNodeId);
  const nodes = useGraphDataStore((s) => s.nodes);
  const edges = useGraphDataStore((s) => s.edges);

  if (!selectedId) {
    return (
      <EmptyState
        icon={<IconInfo className="h-10 w-10" />}
        title="No node selected"
        description="Click a node on the graph to view its details."
        className="pt-12"
      />
    );
  }

  const node = nodes.find((n) => n.id === selectedId);
  if (!node) return null;

  const incoming = edges.filter((e) => e.target_id === selectedId);
  const outgoing = edges.filter((e) => e.source_id === selectedId);

  return (
    <div className="flex max-h-full flex-col gap-4 overflow-y-auto p-5">
      {/* Node Header */}
      <div className="space-y-2.5">
        <div className="flex items-center gap-2.5">
          <Badge label={node.type} nodeType={node.type} size="md" />
          <StatusDot status={node.status} showLabel size="sm" />
        </div>
        <h3 className="text-lg leading-snug font-semibold text-slate-100">{node.name}</h3>
        <p className="font-mono text-xs leading-relaxed break-all text-slate-500">{node.id}</p>
        <div className="flex flex-wrap gap-1.5">
          {node.environment && (
            <span className="inline-block rounded-md border border-slate-700/60 bg-slate-800/80 px-2 py-0.5 text-[10px] font-medium text-slate-400">
              {node.environment}
            </span>
          )}
          {node.properties.created_at != null && (
            <span className="inline-block rounded-md border border-slate-700/40 bg-slate-800/50 px-2 py-0.5 text-[10px] text-slate-500">
              Created: {formatTimestamp(node.properties.created_at)}
            </span>
          )}
          {node.properties.last_seen_at != null && (
            <span className="inline-block rounded-md border border-slate-700/40 bg-slate-800/50 px-2 py-0.5 text-[10px] text-slate-500">
              Last seen: {formatTimestamp(node.properties.last_seen_at)}
            </span>
          )}
        </div>
      </div>

      <Divider />
      <TypeSpecificMetrics node={node} />
      <PropertiesSection properties={node.properties} />

      <Divider />
      <EdgeSection title={`Incoming (${incoming.length})`} edges={incoming} direction="from" nodes={nodes} />
      <EdgeSection title={`Outgoing (${outgoing.length})`} edges={outgoing} direction="to" nodes={nodes} />
    </div>
  );
}

function TypeSpecificMetrics({ node }: Readonly<{ node: GraphNode }>) {
  switch (node.type) {
    case 'Service': {
      const p = node.properties as ServiceProperties;
      return (
        <Section title="Service Metrics">
          {p.language && <InfoRow label="Language" value={s(p.language)} />}
          {p.framework && <InfoRow label="Framework" value={s(p.framework)} />}
          {p.version && <InfoRow label="Version" value={s(p.version)} />}
          {p.tier != null && <InfoRow label="Tier" value={`T${s(p.tier)}`} />}
          {(p as Record<string, unknown>).memory_mb != null && (
            <MetricBar label="Memory" value={n((p as Record<string, unknown>).memory_mb)} max={2048} unit="MB" decimals={1} />
          )}
          {(p as Record<string, unknown>).cpu_seconds_total != null && (
            <InfoRow
              label="CPU time"
              value={`${n((p as Record<string, unknown>).cpu_seconds_total).toFixed(2)} s (cumulative)`}
            />
          )}
        </Section>
      );
    }

    case 'Deployment': {
      const p = node.properties as DeploymentProperties;
      return (
        <Section title="Deployment Metrics">
          {p.strategy && <InfoRow label="Strategy" value={s(p.strategy)} />}
          {p.namespace && <InfoRow label="Namespace" value={s(p.namespace)} />}
          {p.image_tag && <InfoRow label="Image" value={s(p.image_tag)} />}
          {p.replicas_desired != null && p.replicas_ready != null && (
            <ReplicaIndicator desired={n(p.replicas_desired)} ready={n(p.replicas_ready)} />
          )}
        </Section>
      );
    }

    case 'Pod': {
      const p = node.properties as PodProperties;
      return (
        <Section title="Pod Metrics">
          {p.phase && <InfoRow label="Phase" value={s(p.phase)} />}
          {p.namespace && <InfoRow label="Namespace" value={s(p.namespace)} />}
          {p.node_name && <InfoRow label="Node" value={s(p.node_name)} />}
          {p.restart_count != null && (
            <InfoRow label="Restarts" value={s(p.restart_count)} warn={n(p.restart_count) > 0} />
          )}
          {p.cpu_usage_m != null && <MetricBar label="CPU" value={n(p.cpu_usage_m)} max={1000} unit="m" />}
          {p.memory_usage_mi != null && <MetricBar label="Memory" value={n(p.memory_usage_mi)} max={1024} unit="Mi" />}
        </Section>
      );
    }

    case 'Database': {
      const p = node.properties as DatabaseProperties;
      return (
        <Section title="Database Info">
          {p.engine && <InfoRow label="Engine" value={s(p.engine)} />}
          {p.version && <InfoRow label="Version" value={s(p.version)} />}
          {p.capacity_gb != null && <InfoRow label="Capacity" value={`${s(p.capacity_gb)} GB`} />}
          {p.max_connections != null && <InfoRow label="Max Connections" value={s(p.max_connections)} />}
          {p.multi_az != null && <InfoRow label="Multi-AZ" value={p.multi_az ? 'Yes' : 'No'} />}
          {p.is_managed != null && <InfoRow label="Managed" value={p.is_managed ? 'Yes' : 'No'} />}
        </Section>
      );
    }

    case 'Cache': {
      const p = node.properties as CacheProperties;
      return (
        <Section title="Cache Metrics">
          {p.engine && <InfoRow label="Engine" value={s(p.engine)} />}
          {p.eviction_policy && <InfoRow label="Eviction" value={s(p.eviction_policy)} />}
          {p.hit_rate_target != null && <MetricBar label="Hit Rate" value={n(p.hit_rate_target)} max={100} unit="%" />}
          {p.keys_count != null && <InfoRow label="Keys" value={n(p.keys_count).toLocaleString()} />}
          {p.connected_clients != null && <InfoRow label="Clients" value={s(p.connected_clients)} />}
        </Section>
      );
    }

    case 'QueueTopic': {
      const p = node.properties as QueueTopicProperties;
      return (
        <Section title="Queue/Topic Metrics">
          {p.broker && <InfoRow label="Broker" value={s(p.broker)} />}
          {p.partitions != null && <InfoRow label="Partitions" value={s(p.partitions)} />}
          {p.replication_factor != null && <InfoRow label="Replication" value={s(p.replication_factor)} />}
          {p.message_rate != null && <MetricBar label="Msg Rate" value={n(p.message_rate)} max={1000} unit="msg/s" />}
        </Section>
      );
    }

    case 'SLASLO': {
      const p = node.properties;
      return (
        <Section title="SLA/SLO">
          {p.metric_name != null && <InfoRow label="Metric" value={s(p.metric_name)} />}
          {p.target_percentage != null && <InfoRow label="Target" value={`${s(p.target_percentage)}%`} />}
          {p.current_value != null && (
            <SLOGauge
              current={n(p.current_value)}
              target={n(p.target_percentage ?? 99)}
              metric={s(p.metric_name ?? 'value')}
            />
          )}
          {p.violation_count != null && (
            <InfoRow label="Violations" value={s(p.violation_count)} warn={n(p.violation_count) > 0} />
          )}
        </Section>
      );
    }

    case 'Endpoint': {
      const p = node.properties as EndpointProperties;
      return (
        <Section title="Endpoint Info">
          {p.path && <InfoRow label="Path" value={s(p.path)} />}
          {p.method && <InfoRow label="Method" value={s(p.method)} />}
          {p.service_name && <InfoRow label="Service" value={s(p.service_name)} />}
          {p.current_rps != null && <MetricBar label="RPS" value={n(p.current_rps)} max={1000} unit="req/s" />}
          {p.timeout_ms != null && <InfoRow label="Timeout" value={`${s(p.timeout_ms)}ms`} />}
          {p.auth_required != null && <InfoRow label="Auth Required" value={p.auth_required ? 'Yes' : 'No'} />}
          {p.is_public != null && <InfoRow label="Public" value={p.is_public ? 'Yes' : 'No'} />}
          {p.deprecated && <InfoRow label="Status" value="Deprecated" warn />}
        </Section>
      );
    }

    case 'Table': {
      const p = node.properties as TableProperties;
      return (
        <Section title="Table Info">
          {p.database_ref && <InfoRow label="Database" value={s(p.database_ref)} />}
          {p.schema_name && <InfoRow label="Schema" value={s(p.schema_name)} />}
          {p.row_count != null && <InfoRow label="Rows" value={n(p.row_count).toLocaleString()} />}
          {p.size_bytes != null && <InfoRow label="Size" value={`${(n(p.size_bytes) / 1048576).toFixed(1)} MB`} />}
          {p.is_partitioned != null && <InfoRow label="Partitioned" value={p.is_partitioned ? 'Yes' : 'No'} />}
        </Section>
      );
    }

    case 'Library': {
      const p = node.properties as LibraryProperties;
      return (
        <Section title="Library Info">
          {p.language && <InfoRow label="Language" value={s(p.language)} />}
          {p.version && <InfoRow label="Version" value={s(p.version)} />}
          {p.package_manager && <InfoRow label="Package Manager" value={s(p.package_manager)} />}
          {p.license && <InfoRow label="License" value={s(p.license)} />}
        </Section>
      );
    }

    case 'TeamOwner': {
      const p = node.properties as TeamOwnerProperties;
      return (
        <Section title="Team Info">
          {p.lead_name && <InfoRow label="Lead" value={s(p.lead_name)} />}
          {p.email && <InfoRow label="Email" value={s(p.email)} />}
          {p.slack_channel && <InfoRow label="Slack" value={s(p.slack_channel)} />}
          {p.department && <InfoRow label="Department" value={s(p.department)} />}
          {p.cost_center && <InfoRow label="Cost Center" value={s(p.cost_center)} />}
        </Section>
      );
    }

    case 'SecretConfig': {
      const p = node.properties as SecretConfigProperties;
      return (
        <Section title="Secret Config">
          {p.provider && <InfoRow label="Provider" value={s(p.provider)} />}
          {p.algorithm && <InfoRow label="Algorithm" value={s(p.algorithm)} />}
          {p.is_encrypted != null && <InfoRow label="Encrypted" value={p.is_encrypted ? 'Yes' : 'No'} />}
          {p.rotation_interval_days != null && <InfoRow label="Rotation" value={`${s(p.rotation_interval_days)} days`} />}
          {p.vault_path && <InfoRow label="Vault Path" value={s(p.vault_path)} />}
        </Section>
      );
    }

    case 'ExternalAPI': {
      const p = node.properties as ExternalAPIProperties;
      return (
        <Section title="External API">
          {p.base_url && <InfoRow label="Base URL" value={s(p.base_url)} />}
          {p.auth_type && <InfoRow label="Auth Type" value={s(p.auth_type)} />}
          {p.rate_limit_tier && <InfoRow label="Rate Limit" value={s(p.rate_limit_tier)} />}
          {p.provider && <InfoRow label="Provider" value={s(p.provider)} />}
          {p.sla_percentage != null && <MetricBar label="SLA" value={n(p.sla_percentage)} max={100} unit="%" />}
          {p.documentation_url && <InfoRow label="Docs" value={s(p.documentation_url)} />}
        </Section>
      );
    }

    default: {
      const entries = Object.entries(node.properties).filter(([, v]) => v !== null && v !== undefined && v !== '');
      if (entries.length === 0) return null;
      return (
        <Section title={`${node.type} Properties`}>
          {entries.map(([k, v]) => (
            <InfoRow key={k} label={formatLabel(k)} value={formatValue(v)} />
          ))}
        </Section>
      );
    }
  }
}

function expandProperties(raw: Record<string, unknown>): Array<[string, unknown]> {
  const merged: Record<string, unknown> = { ...raw };
  const nested = merged.properties;
  if (typeof nested === 'string') {
    try {
      const parsed = JSON.parse(nested);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        for (const [k, v] of Object.entries(parsed as Record<string, unknown>)) {
          if (!(k in merged)) merged[k] = v;
        }
        delete merged.properties;
      }
    } catch {
      /* leave as string */
    }
  } else if (nested && typeof nested === 'object' && !Array.isArray(nested)) {
    for (const [k, v] of Object.entries(nested as Record<string, unknown>)) {
      if (!(k in merged)) merged[k] = v;
    }
    delete merged.properties;
  }
  return Object.entries(merged).filter(([, v]) => v !== null && v !== undefined && v !== '');
}

function PropertiesSection({ properties }: Readonly<{ properties: Record<string, unknown> }>) {
  const entries = expandProperties(properties);
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
  direction: 'from' | 'to';
  nodes: GraphNode[];
}>) {
  return (
    <Section title={title}>
      {edges.length === 0 && <p className="text-sm text-slate-500">None</p>}
      <div className="space-y-2">
        {edges.map((e) => (
          <EdgeDetailRow key={`${e.source_id}-${e.target_id}-${e.type}`} edge={e} direction={direction} nodes={nodes} />
        ))}
      </div>
    </Section>
  );
}

function EdgeDetailRow({
  edge,
  direction,
  nodes,
}: Readonly<{
  edge: GraphEdge;
  direction: 'from' | 'to';
  nodes: GraphNode[];
}>) {
  const selectNode = useGraphUiStore((s) => s.selectNode);
  const otherId = direction === 'from' ? edge.source_id : edge.target_id;
  const otherNode = nodes.find((n) => n.id === otherId);
  const color = getEdgeColor(edge.type);
  const p = edge.properties;

  const hasCallMetrics = edge.type.toUpperCase() === 'CALLS' || edge.type === 'calls';
  const rps = p.rps == null ? null : Number(p.rps);
  const latency = p.latency_p99_ms == null ? null : Number(p.latency_p99_ms);
  const errorRate = p.error_rate_percent == null ? null : Number(p.error_rate_percent);

  return (
    <div className="space-y-2 rounded-lg border border-slate-700/50 bg-slate-800/60 p-3 transition-all duration-200 hover:border-slate-600/60">
      <button
        onClick={() => selectNode(otherId)}
        className="flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-slate-700/40"
      >
        <span className="font-medium" style={{ color }}>
          {edge.type}
        </span>
        <span className="text-base text-slate-400">{direction === 'from' ? '←' : '→'}</span>
        <span className="flex-1 truncate text-slate-200">{otherNode?.name ?? otherId}</span>
      </button>

      {hasCallMetrics && (rps != null || latency != null || errorRate != null) && (
        <div className="flex items-center gap-4 px-2 text-xs">
          {rps != null && (
            <span className="flex items-center gap-1.5">
              <span className="font-medium text-slate-500">RPS:</span>
              <span className="font-semibold text-blue-400 tabular-nums">{rps.toFixed(1)}</span>
            </span>
          )}
          {latency != null && (
            <span className="flex items-center gap-1.5">
              <span className="font-medium text-slate-500">P99:</span>
              <span className="font-semibold tabular-nums" style={{ color: latency > 200 ? '#f59e0b' : '#22c55e' }}>
                {latency.toFixed(0)}ms
              </span>
            </span>
          )}
          {errorRate != null && (
            <span className="flex items-center gap-1.5">
              <span className="font-medium text-slate-500">Err:</span>
              <span className="font-semibold tabular-nums" style={{ color: errorRate > 1 ? '#ef4444' : '#22c55e' }}>
                {errorRate.toFixed(2)}%
              </span>
            </span>
          )}
        </div>
      )}

      {!hasCallMetrics && Object.keys(p).length > 0 && (
        <div className="space-y-1.5 px-2">
          {Object.entries(p)
            .filter(([, v]) => v != null && v !== '')
            .slice(0, 4)
            .map(([k, v]) => (
              <div key={k} className="flex justify-between text-xs">
                <span className="text-slate-400">{formatLabel(k)}</span>
                <span className="font-mono text-slate-300">{formatValue(v)}</span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

function ReplicaIndicator({ desired, ready }: Readonly<{ desired: number; ready: number }>) {
  const isHealthy = ready >= desired;
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-slate-400">Replicas</span>
        <span className="font-mono font-semibold" style={{ color: isHealthy ? '#22c55e' : '#ef4444' }}>
          {ready}/{desired}
        </span>
      </div>
      <div className="flex gap-1.5">
        {Array.from({ length: desired }).map((_, i) => {
          const rid = `replica-${i}`;
          return (
            <div
              key={rid}
              className="h-2.5 flex-1 rounded transition-colors duration-300"
              style={{
                backgroundColor: i < ready ? '#22c55e' : '#ef444450',
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
  const isLatency = metric.includes('latency');
  const isMet = isLatency ? current <= target : current >= target;
  const displayValue = isLatency ? `${current.toFixed(1)}ms` : `${current.toFixed(4)}%`;

  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-700/50 bg-slate-800/60 p-3">
      <div>
        <p className="text-xs font-medium text-slate-400">Current</p>
        <p className="mt-1 font-mono text-base font-bold" style={{ color: isMet ? '#22c55e' : '#ef4444' }}>
          {displayValue}
        </p>
      </div>
      <div
        className="rounded-md px-3 py-1.5 text-xs font-bold"
        style={{
          backgroundColor: isMet ? '#22c55e20' : '#ef444420',
          color: isMet ? '#22c55e' : '#ef4444',
        }}
      >
        {isMet ? 'MEETING SLO' : 'SLO VIOLATION'}
      </div>
    </div>
  );
}

function Section({ title, children }: Readonly<{ title: string; children: React.ReactNode }>) {
  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold tracking-wide text-slate-400 uppercase">{title}</h4>
      {children}
    </div>
  );
}
