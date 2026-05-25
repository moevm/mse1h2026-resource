import { useGraphDataStore, useGraphFilterStore } from '../../features/graph/store';
import { getEdgeColor, getNodeColor } from '../../utils/colors';
import { EmptyState } from '../common/EmptyState';

export function FilterPanel() {
  const nodes = useGraphDataStore((s) => s.nodes);
  const edges = useGraphDataStore((s) => s.edges);
  const hiddenNodeTypes = useGraphFilterStore((s) => s.hiddenNodeTypes);
  const hiddenEdgeTypes = useGraphFilterStore((s) => s.hiddenEdgeTypes);
  const filterMode = useGraphFilterStore((s) => s.filterMode);
  const toggleNodeType = useGraphFilterStore((s) => s.toggleNodeType);
  const toggleEdgeType = useGraphFilterStore((s) => s.toggleEdgeType);
  const setHiddenNodeTypes = useGraphFilterStore((s) => s.setHiddenNodeTypes);
  const setHiddenEdgeTypes = useGraphFilterStore((s) => s.setHiddenEdgeTypes);
  const setFilterMode = useGraphFilterStore((s) => s.setFilterMode);

  const nodeTypes = [...new Set(nodes.map((n) => n.type))].sort((a, b) => a.localeCompare(b));
  const edgeTypes = [...new Set(edges.map((e) => e.type))].sort((a, b) => a.localeCompare(b));

  const selectAll = () => {
    setHiddenNodeTypes([]);
    setHiddenEdgeTypes([]);
  };
  const resetAll = () => {
    setHiddenNodeTypes(nodeTypes);
    setHiddenEdgeTypes(edgeTypes);
  };

  if (nodeTypes.length === 0 && edgeTypes.length === 0) {
    return <EmptyState title="No graph loaded" description="Load a graph to see type filters." className="pt-12" />;
  }

  return (
    <div className="flex max-h-full flex-col overflow-y-auto">
      <div className="flex gap-1.5 px-5 pt-4">
        <button
          onClick={selectAll}
          className="flex-1 rounded-md bg-slate-800/60 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700/70"
        >
          Select all
        </button>
        <button
          onClick={resetAll}
          className="flex-1 rounded-md bg-slate-800/60 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700/70"
        >
          Reset filters
        </button>
      </div>
      <div className="border-b border-slate-800/70 px-5 pt-4 pb-4">
        <p className="mb-3 text-xs font-semibold tracking-wide text-slate-400 uppercase">Filter Mode</p>
        <div className="flex overflow-hidden rounded-lg border border-slate-700/70 bg-slate-900">
          <ModeBtn
            active={filterMode === 'ghost'}
            onClick={() => setFilterMode('ghost')}
            label="Ghost"
            desc="Dim in place"
          />
          <span className="w-px shrink-0 bg-slate-700/60" />
          <ModeBtn
            active={filterMode === 'exclude'}
            onClick={() => setFilterMode('exclude')}
            label="Exclude"
            desc="Hide completely"
          />
        </div>
      </div>

      {nodeTypes.length > 0 && (
        <section className="px-5 pt-4 pb-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-xs font-semibold tracking-wide text-slate-400 uppercase">Node Types</h3>
            <div className="flex gap-1.5">
              <BulkBtn label="All" active={hiddenNodeTypes.size === 0} onClick={() => setHiddenNodeTypes([])} />
              <BulkBtn
                label="None"
                active={nodeTypes.every((t) => hiddenNodeTypes.has(t))}
                onClick={() => setHiddenNodeTypes(nodeTypes)}
              />
            </div>
          </div>
          <div className="space-y-1">
            {nodeTypes.map((t) => (
              <TypeToggle
                key={t}
                label={t}
                color={getNodeColor(t)}
                checked={!hiddenNodeTypes.has(t)}
                count={nodes.filter((n) => n.type === t).length}
                onToggle={() => toggleNodeType(t)}
              />
            ))}
          </div>
        </section>
      )}

      {nodeTypes.length > 0 && edgeTypes.length > 0 && <div className="mx-5 border-t border-slate-800/60" />}

      {edgeTypes.length > 0 && (
        <section className="px-5 pt-4 pb-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-xs font-semibold tracking-wide text-slate-400 uppercase">Edge Types</h3>
            <div className="flex gap-1.5">
              <BulkBtn label="All" active={hiddenEdgeTypes.size === 0} onClick={() => setHiddenEdgeTypes([])} />
              <BulkBtn
                label="None"
                active={edgeTypes.every((t) => hiddenEdgeTypes.has(t))}
                onClick={() => setHiddenEdgeTypes(edgeTypes)}
              />
            </div>
          </div>
          <div className="space-y-1">
            {edgeTypes.map((t) => (
              <TypeToggle
                key={t}
                label={t}
                color={getEdgeColor(t)}
                checked={!hiddenEdgeTypes.has(t)}
                count={edges.filter((e) => e.type === t).length}
                onToggle={() => toggleEdgeType(t)}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function ModeBtn({
  active,
  onClick,
  label,
  desc,
}: Readonly<{ active: boolean; onClick: () => void; label: string; desc: string }>) {
  return (
    <button
      onClick={onClick}
      className={[
        'flex-1 px-3.5 py-3 text-left transition-all duration-200',
        active ? 'border-l-2 border-blue-500 bg-blue-600/20' : 'border-l-2 border-transparent hover:bg-slate-800/60',
      ].join(' ')}
    >
      <p className={`text-sm leading-tight font-semibold ${active ? 'text-blue-300' : 'text-slate-400'}`}>{label}</p>
      <p className="mt-1 text-xs leading-snug text-slate-500">{desc}</p>
    </button>
  );
}

function BulkBtn({ label, onClick, active }: Readonly<{ label: string; onClick: () => void; active: boolean }>) {
  return (
    <button
      onClick={onClick}
      className={[
        'rounded-md px-2.5 py-1 text-xs font-medium transition-all duration-150',
        active ? 'bg-slate-700/80 text-slate-200' : 'text-slate-500 hover:bg-slate-800/60 hover:text-slate-300',
      ].join(' ')}
    >
      {label}
    </button>
  );
}

interface TypeToggleProps {
  label: string;
  color: string;
  checked: boolean;
  count: number;
  onToggle: () => void;
}

function TypeToggle({ label, color, checked, count, onToggle }: Readonly<TypeToggleProps>) {
  return (
    <label className="group flex cursor-pointer items-center gap-3 rounded-lg px-2.5 py-2 transition-all duration-150 hover:bg-slate-800/70">
      <input type="checkbox" checked={checked} onChange={onToggle} className="shrink-0" />
      <span
        className="h-3 w-3 shrink-0 rounded-sm shadow-sm transition-all duration-150"
        style={{
          backgroundColor: color,
          opacity: checked ? 1 : 0.3,
          boxShadow: checked ? `0 0 8px ${color}60` : 'none',
        }}
      />
      <span
        className={`flex-1 text-sm leading-tight transition-colors ${
          checked ? 'font-medium text-slate-200' : 'text-slate-500'
        }`}
      >
        {label}
      </span>
      <span
        className={`rounded px-2 py-0.5 font-mono text-xs tabular-nums ${
          checked ? 'bg-slate-800/60 text-slate-400' : 'text-slate-600'
        }`}
      >
        {count}
      </span>
    </label>
  );
}
