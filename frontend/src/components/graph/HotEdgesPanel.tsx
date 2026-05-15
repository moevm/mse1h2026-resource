import { useMemo } from 'react';

import { useCyContext } from '../../context/CytoscapeContext';
import { useGraphDataStore, useGraphUiStore } from '../../features/graph/store';
import type { GraphEdge } from '../../types';

const TOP_N = 5;

function shortLabel(id: string): string {
  const idx = id.lastIndexOf(':');
  return idx >= 0 ? id.slice(idx + 1) : id;
}

function numOrZero(v: unknown): number {
  if (v === null || v === undefined || v === '') return 0;
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function edgeKey(e: GraphEdge): string {
  return `${e.source_id}::${e.target_id}::${e.type}`;
}

export function HotEdgesPanel() {
  const edges = useGraphDataStore((s) => s.edges);
  const edgeDisplayMode = useGraphUiStore((s) => s.edgeDisplayMode);
  const setHighlightedEdges = useGraphUiStore((s) => s.setHighlightedEdges);
  const { centerOn } = useCyContext();

  const top = useMemo(() => {
    const scored = edges
      .map((e) => {
        const calls = numOrZero(e.properties.call_count_window ?? e.properties.call_count);
        const errors = numOrZero(e.properties.error_count_window ?? e.properties.error_count);
        return { edge: e, calls, errors };
      })
      .filter((x) => x.calls > 0)
      .sort((a, b) => b.calls - a.calls)
      .slice(0, TOP_N);
    return scored;
  }, [edges]);

  if (edgeDisplayMode !== 'load' || top.length === 0) return null;

  const handleClick = (e: GraphEdge) => {
    const key = edgeKey(e);
    setHighlightedEdges(new Set([key]));
    centerOn(e.source_id);
  };

  return (
    <div className="animate-fade-in absolute top-3 right-3 z-30 w-64 rounded-lg border border-slate-700/60 bg-slate-900/95 p-2 text-[11px] shadow-2xl backdrop-blur-sm">
      <div className="mb-1.5 flex items-center justify-between px-1">
        <span className="font-semibold text-slate-300">Top edges (load)</span>
        <span className="text-[9px] uppercase tracking-wide text-slate-500">{top.length}</span>
      </div>
      <div className="space-y-0.5">
        {top.map((row) => {
          const errRate = row.calls > 0 ? row.errors / row.calls : 0;
          const errColor =
            errRate > 0.05 ? 'text-red-400' : errRate > 0.01 ? 'text-yellow-400' : 'text-slate-400';
          return (
            <button
              key={edgeKey(row.edge)}
              onClick={() => handleClick(row.edge)}
              className="flex w-full items-center gap-2 rounded px-1.5 py-1 text-left transition-colors hover:bg-slate-800"
            >
              <span className="min-w-0 flex-1 truncate">
                <span className="font-mono text-slate-200">{shortLabel(row.edge.source_id)}</span>
                <span className="mx-0.5 text-slate-600">→</span>
                <span className="font-mono text-slate-200">{shortLabel(row.edge.target_id)}</span>
              </span>
              <span className="shrink-0 font-mono text-slate-300 tabular-nums">{row.calls}</span>
              {row.errors > 0 && (
                <span className={`shrink-0 font-mono tabular-nums ${errColor}`}>
                  {row.errors}e
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
