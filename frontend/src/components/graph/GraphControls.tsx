import { useEffect, useState } from 'react';

import { clearStaleNodes } from '../../api/graphApi';
import { useCyContext } from '../../context/CytoscapeContext';
import { useGraphDataStore, useGraphUiStore } from '../../features/graph/store';
import { useGraph } from '../../hooks/useGraph';
import { Button } from '../common/Button';
import { IconFit, IconZoomIn, IconZoomOut } from '../icons';

export function GraphControls() {
  const { fitGraph, runLayout, zoomIn, zoomOut, centerOn } = useCyContext();
  const selectedNodeId = useGraphUiStore((s) => s.selectedNodeId);
  const clearVisualFocus = useGraphUiStore((s) => s.clearVisualFocus);
  const edgeDisplayMode = useGraphUiStore((s) => s.edgeDisplayMode);
  const setEdgeDisplayMode = useGraphUiStore((s) => s.setEdgeDisplayMode);
  const nodeTtlSeconds = useGraphUiStore((s) => s.nodeTtlSeconds);
  const setNodeTtlSeconds = useGraphUiStore((s) => s.setNodeTtlSeconds);
  const tickNow = useGraphUiStore((s) => s.tickNow);
  const nowMs = useGraphUiStore((s) => s.nowMs);
  const nodes = useGraphDataStore((s) => s.nodes);
  const selectedAppId = useGraphUiStore((s) => s.selectedAppId);
  const { loadFullGraph } = useGraph();

  const [ttlInput, setTtlInput] = useState(String(Math.round(nodeTtlSeconds / 60)));
  const [clearLoading, setClearLoading] = useState(false);

  useEffect(() => {
    setTtlInput(String(Math.round(nodeTtlSeconds / 60)));
  }, [nodeTtlSeconds]);

  useEffect(() => {
    const id = setInterval(tickNow, 5000);
    return () => clearInterval(id);
  }, [tickNow]);

  const ttlMs = nodeTtlSeconds * 1000;
  const staleCount = nodes.filter((n) => {
    const ls = (n.properties as Record<string, unknown>).last_seen_at;
    const t = typeof ls === 'string' ? Date.parse(ls) : (typeof ls === 'number' ? ls : NaN);
    return Number.isFinite(t) && nowMs - t > ttlMs;
  }).length;

  const commitTtl = () => {
    const m = parseInt(ttlInput, 10);
    if (Number.isFinite(m) && m >= 1) {
      setNodeTtlSeconds(m * 60);
    } else {
      setTtlInput(String(Math.round(nodeTtlSeconds / 60)));
    }
  };

  const handleClearStale = async () => {
    setClearLoading(true);
    try {
      await clearStaleNodes(nodeTtlSeconds);
      await loadFullGraph(500, selectedAppId ?? undefined);
    } catch (e) {
      console.error('clear-stale failed', e);
    } finally {
      setClearLoading(false);
    }
  };

  const typeCounts = new Map<string, number>();
  for (const n of nodes) {
    typeCounts.set(n.type, (typeCounts.get(n.type) ?? 0) + 1);
  }
  const typeEntries = [...typeCounts.entries()].sort((a, b) => b[1] - a[1]);

  return (
    <>
      <div className="animate-fade-in absolute bottom-5 left-5 z-30 flex items-center gap-1 rounded-xl border border-slate-700/70 bg-slate-900/95 p-1.5 shadow-2xl shadow-black/40 backdrop-blur-md">
        <Button variant="ghost" size="sm" onClick={zoomIn} title="Zoom in" icon={<IconZoomIn className="h-4 w-4" />} className="hover:bg-slate-800" />
        <Button variant="ghost" size="sm" onClick={zoomOut} title="Zoom out" icon={<IconZoomOut className="h-4 w-4" />} className="hover:bg-slate-800" />
        <div className="mx-1 h-5 w-px bg-slate-700/60" />
        <Button variant="ghost" size="sm" onClick={fitGraph} title="Fit to screen" icon={<IconFit className="h-4 w-4" />} className="hover:bg-slate-800" />
        <div className="mx-1 h-5 w-px bg-slate-700/60" />
        <Button variant="ghost" size="sm" onClick={() => runLayout('cose')} title="Force-directed layout" className="font-medium hover:bg-slate-800">Force</Button>
        <Button variant="ghost" size="sm" onClick={() => runLayout('circle')} title="Circle layout" className="font-medium hover:bg-slate-800">Circle</Button>
        <Button variant="ghost" size="sm" onClick={() => runLayout('grid')} title="Grid layout" className="font-medium hover:bg-slate-800">Grid</Button>
        <div className="mx-1 h-5 w-px bg-slate-700/60" />
        <Button variant="ghost" size="sm" onClick={() => { if (selectedNodeId) centerOn(selectedNodeId); }} title="Center selected node" disabled={!selectedNodeId} className="font-medium hover:bg-slate-800">Center</Button>
        <Button variant="ghost" size="sm" onClick={clearVisualFocus} title="Clear highlights" className="font-medium hover:bg-slate-800">Clear</Button>
        <div className="mx-1 h-5 w-px bg-slate-700/60" />
        <div className="flex items-center gap-0.5 rounded-md bg-slate-800/60 p-0.5">
          <button
            onClick={() => setEdgeDisplayMode('topology')}
            title="Topology: edge style reflects relationship type only"
            className={[
              'rounded px-2 py-1 text-[11px] font-medium transition-colors',
              edgeDisplayMode === 'topology'
                ? 'bg-slate-700 text-slate-100'
                : 'text-slate-400 hover:text-slate-200',
            ].join(' ')}
          >
            Topology
          </button>
          <button
            onClick={() => setEdgeDisplayMode('load')}
            title="Load: thickness = call volume vs busiest edge, color = error rate"
            className={[
              'rounded px-2 py-1 text-[11px] font-medium transition-colors',
              edgeDisplayMode === 'load'
                ? 'bg-blue-600 text-white'
                : 'text-slate-400 hover:text-slate-200',
            ].join(' ')}
          >
            Load
          </button>
        </div>
        <div className="mx-1 h-5 w-px bg-slate-700/60" />
        <label className="flex items-center gap-1 text-[10px] text-slate-400" title="A node is marked unknown after this many minutes without updates">
          TTL
          <input
            type="number"
            min={1}
            max={1440}
            value={ttlInput}
            onChange={(e) => setTtlInput(e.target.value)}
            onBlur={commitTtl}
            onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }}
            className="w-10 rounded bg-slate-800/80 px-1 py-0.5 text-center font-mono text-[10px] text-slate-200 outline-none focus:ring-1 focus:ring-blue-500"
          />
          <span className="text-slate-600">min</span>
        </label>
        <button
          onClick={handleClearStale}
          disabled={clearLoading || staleCount === 0}
          title="Delete all nodes whose last_seen_at is older than TTL"
          className={[
            'rounded px-2 py-1 text-[11px] font-medium transition-colors',
            staleCount > 0
              ? 'bg-amber-600/30 text-amber-200 hover:bg-amber-600/50'
              : 'text-slate-600',
            clearLoading ? 'opacity-50' : '',
          ].join(' ')}
        >
          {clearLoading ? '...' : `Clear unknown (${staleCount})`}
        </button>
      </div>

      {typeEntries.length > 0 && (
        <div className="animate-fade-in absolute top-3 left-3 z-30 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-slate-700/50 bg-slate-900/90 px-3 py-1.5 text-[10px] shadow-lg backdrop-blur-sm">
          {typeEntries.map(([type, count]) => (
            <span key={type} className="flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: nodeTypeColor(type) }} />
              <span className="text-slate-400">{type}</span>
              <span className="text-slate-600">{count}</span>
            </span>
          ))}
        </div>
      )}
    </>
  );
}

function nodeTypeColor(type: string): string {
  const colors: Record<string, string> = {
    Service: '#3b82f6',
    Database: '#8b5cf6',
    Cache: '#f59e0b',
    ExternalAPI: '#ef4444',
    QueueTopic: '#10b981',
    Endpoint: '#06b6d4',
    Table: '#a78bfa',
    Library: '#f472b6',
    Deployment: '#6366f1',
    Pod: '#14b8a6',
    TeamOwner: '#f97316',
    SecretConfig: '#ec4899',
    SLASLO: '#22d3ee',
  };
  return colors[type] ?? '#64748b';
}
