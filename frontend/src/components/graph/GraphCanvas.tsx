import { useCallback, useEffect, useRef, useState } from 'react';

import { useCyContext } from '../../context/CytoscapeContext';
import { useGraphDataStore, useGraphUiStore } from '../../features/graph/store';
import { getStatusColor } from '../../utils/colors';
import { Badge } from '../common/Badge';
import { Spinner } from '../common/Spinner';

export function GraphCanvas() {
  const { containerRef } = useCyContext();

  const loading = useGraphUiStore((s) => s.loading);
  const nodes = useGraphDataStore((s) => s.nodes);
  const edges = useGraphDataStore((s) => s.edges);
  const hoveredNodeId = useGraphUiStore((s) => s.hoveredNodeId);
  const hoveredEdgeId = useGraphUiStore((s) => s.hoveredEdgeId);
  const edgeDisplayMode = useGraphUiStore((s) => s.edgeDisplayMode);

  const hoveredNode = hoveredNodeId ? nodes.find((n) => n.id === hoveredNodeId) : null;
  const hoveredEdge = hoveredEdgeId
    ? edges.find((e) => `${e.source_id}::${e.target_id}::${e.type}` === hoveredEdgeId)
    : null;

  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const rafRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
    },
    [],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!hoveredNode && !hoveredEdge) return;

      const rect = e.currentTarget.getBoundingClientRect();
      const next = { x: e.clientX - rect.left, y: e.clientY - rect.top };

      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        setMousePos(next);
        rafRef.current = null;
      });
    },
    [hoveredNode, hoveredEdge],
  );

  return (
    <div
      className="relative h-full w-full"
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
            className="mb-4 h-16 w-16 opacity-30"
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
          <p className="mt-1 text-xs text-slate-600">Use the Reload button or run an analysis query</p>
        </div>
      )}

      <div ref={containerRef} className="h-full w-full cursor-default" />

      {hoveredNode && <NodeTooltip node={hoveredNode} x={mousePos.x} y={mousePos.y} />}
      {!hoveredNode && hoveredEdge && (
        <EdgeTooltip edge={hoveredEdge} mode={edgeDisplayMode} x={mousePos.x} y={mousePos.y} />
      )}
    </div>
  );
}

interface TooltipEdge {
  source_id: string;
  target_id: string;
  type: string;
  status?: string;
  properties: Record<string, unknown>;
}

function EdgeTooltip({
  edge,
  mode,
  x,
  y,
}: Readonly<{
  edge: TooltipEdge;
  mode: 'topology' | 'load';
  x: number;
  y: number;
}>) {
  const p = edge.properties;
  const callsWindow = numOrNull(p.call_count_window);
  const errsWindow = numOrNull(p.error_count_window);
  const avgLatencyWindow = numOrNull(p.avg_latency_ms_window);
  const callsAll = numOrNull(p.call_count);
  const errsAll = numOrNull(p.error_count);
  const totalDurNs = numOrNull(p.total_duration_ns);
  const lastCallAt = typeof p.last_call_at === 'string' ? p.last_call_at : null;

  const showWindow = callsWindow !== null;
  const calls = showWindow ? callsWindow! : (callsAll ?? 0);
  const errs = showWindow ? (errsWindow ?? 0) : (errsAll ?? 0);
  const avgMs = showWindow
    ? (avgLatencyWindow ?? 0)
    : (callsAll && totalDurNs ? totalDurNs / callsAll / 1_000_000 : 0);
  const errRate = calls > 0 ? errs / calls : 0;

  const OFFSET = 14;
  const style: React.CSSProperties = {
    left: x + OFFSET,
    top: y + OFFSET,
    maxWidth: 260,
  };

  return (
    <div
      className="pointer-events-none absolute z-50 rounded-xl border border-slate-700 bg-slate-800/95 p-3 text-xs shadow-2xl backdrop-blur-sm"
      style={style}
    >
      <div className="mb-1.5 flex items-center gap-2">
        <span className="rounded bg-slate-700/70 px-1.5 py-0.5 font-mono text-[10px] uppercase text-slate-200">
          {edge.type}
        </span>
        {showWindow ? (
          <span className="text-[9px] uppercase tracking-wide text-blue-400">window</span>
        ) : (
          <span className="text-[9px] uppercase tracking-wide text-slate-500">all-time</span>
        )}
        {mode === 'load' && (
          <span className="text-[9px] uppercase tracking-wide text-slate-500">load mode</span>
        )}
      </div>
      <p className="truncate font-mono text-[10px] text-slate-300">{edge.source_id}</p>
      <p className="truncate font-mono text-[10px] text-slate-500">→ {edge.target_id}</p>

      <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-0.5 border-t border-slate-700 pt-2">
        <span className="text-slate-500">calls</span>
        <span className="text-right font-mono text-slate-200 tabular-nums">{calls.toLocaleString()}</span>

        <span className="text-slate-500">errors</span>
        <span className={['text-right font-mono tabular-nums', errs > 0 ? 'text-red-400' : 'text-slate-200'].join(' ')}>
          {errs.toLocaleString()}
        </span>

        <span className="text-slate-500">error rate</span>
        <span className={['text-right font-mono tabular-nums', errRate > 0.05 ? 'text-red-400' : errRate > 0.01 ? 'text-yellow-400' : 'text-slate-200'].join(' ')}>
          {(errRate * 100).toFixed(2)}%
        </span>

        <span className="text-slate-500">avg latency</span>
        <span className="text-right font-mono text-slate-200 tabular-nums">
          {avgMs > 0 ? `${avgMs.toFixed(1)} ms` : '—'}
        </span>

        {lastCallAt && (
          <>
            <span className="text-slate-500">last call</span>
            <span className="text-right font-mono text-[10px] text-slate-400 tabular-nums">
              {ageString(lastCallAt)}
            </span>
          </>
        )}
      </div>
    </div>
  );
}

function numOrNull(v: unknown): number | null {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function ageString(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 0) return 'just now';
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  return `${h}h ago`;
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
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .slice(0, 3);

  const OFFSET = 14;
  const style: React.CSSProperties = {
    left: x + OFFSET,
    top: y + OFFSET,
    maxWidth: 240,
  };

  return (
    <div
      className="pointer-events-none absolute z-50 rounded-xl border border-slate-700 bg-slate-800/95 p-3 text-xs shadow-2xl backdrop-blur-sm"
      style={style}
    >
      <div className="mb-2 flex items-center gap-2">
        <Badge label={node.type} nodeType={node.type} />
        <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: getStatusColor(node.status) }} />
      </div>
      <p className="truncate font-semibold text-slate-100">{node.name}</p>
      <p className="mt-0.5 truncate font-mono text-[10px] text-slate-500">{node.id}</p>
      {preview.length > 0 && (
        <div className="mt-2 space-y-0.5 border-t border-slate-700 pt-2">
          {preview.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3">
              <span className="text-slate-500">{k}</span>
              <span className="max-w-30 truncate font-mono text-slate-300">{String(v)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
