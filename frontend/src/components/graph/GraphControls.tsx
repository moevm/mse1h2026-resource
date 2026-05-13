import { useCyContext } from '../../context/CytoscapeContext';
import { useGraphDataStore, useGraphUiStore } from '../../features/graph/store';
import { Button } from '../common/Button';
import { IconFit, IconZoomIn, IconZoomOut } from '../icons';

export function GraphControls() {
  const { fitGraph, runLayout, zoomIn, zoomOut, centerOn } = useCyContext();
  const selectedNodeId = useGraphUiStore((s) => s.selectedNodeId);
  const clearVisualFocus = useGraphUiStore((s) => s.clearVisualFocus);
  const nodes = useGraphDataStore((s) => s.nodes);

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
