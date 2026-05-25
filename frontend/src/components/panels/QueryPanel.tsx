import { useEffect, useId, useState } from 'react';

import { useGraphUiStore } from '../../features/graph/store';
import { useGraph } from '../../hooks/useGraph';
import { Button } from '../common/Button';
import { Section } from '../common/Card';
import { Input } from '../common/Input';

type ImpactDirection = 'upstream' | 'downstream' | 'both';

export function QueryPanel() {
  const { loadSubgraph, loadShortestPath, loadImpact } = useGraph();
  const selectedNodeId = useGraphUiStore((s) => s.selectedNodeId);

  return (
    <div className="flex max-h-full flex-col gap-5 overflow-y-auto p-4">
      <SubgraphForm defaultCenter={selectedNodeId ?? ''} onSubmit={loadSubgraph} />
      <div className="border-t border-slate-800" />
      <PathForm selectedNodeId={selectedNodeId ?? ''} onSubmit={loadShortestPath} />
      <div className="border-t border-slate-800" />
      <ImpactForm defaultNode={selectedNodeId ?? ''} onSubmit={loadImpact} />
    </div>
  );
}

function SubgraphForm({
  defaultCenter,
  onSubmit,
}: Readonly<{
  defaultCenter: string;
  onSubmit: (r: { center_node_id: string; depth: number }) => Promise<void>;
}>) {
  const [center, setCenter] = useState(defaultCenter);
  const [depth, setDepth] = useState(2);

  useEffect(() => {
    if (!center.trim() && defaultCenter) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCenter(defaultCenter);
    }
  }, [defaultCenter, center]);

  return (
    <Section title="Subgraph (Ego Network)">
      <div className="space-y-3">
        <Input
          label="Center Node ID"
          value={center}
          onChange={(e) => setCenter(e.target.value)}
          placeholder="urn:service:…"
        />
        <NumberSlider label="Depth" value={depth} onChange={setDepth} min={1} max={5} />
        <Button
          variant="primary"
          size="sm"
          disabled={!center.trim()}
          onClick={() => {
            void onSubmit({ center_node_id: center.trim(), depth });
          }}
        >
          Load Subgraph
        </Button>
      </div>
    </Section>
  );
}

function PathForm({
  selectedNodeId,
  onSubmit,
}: Readonly<{
  selectedNodeId: string;
  onSubmit: (r: { source_id: string; target_id: string; max_depth?: number }) => Promise<void>;
}>) {
  const [source, setSource] = useState('');
  const [target, setTarget] = useState('');
  const [maxDepth, setMaxDepth] = useState(5);

  return (
    <Section title="Shortest Path">
      <div className="space-y-3">
        <Input
          label="Source ID"
          value={source}
          onChange={(e) => setSource(e.target.value)}
          placeholder="urn:service:…"
        />
        {selectedNodeId && (
          <button className="text-[11px] text-blue-400 hover:text-blue-300" onClick={() => setSource(selectedNodeId)}>
            Use selected node as source
          </button>
        )}
        <Input label="Target ID" value={target} onChange={(e) => setTarget(e.target.value)} placeholder="urn:db:…" />
        {selectedNodeId && (
          <button className="text-[11px] text-blue-400 hover:text-blue-300" onClick={() => setTarget(selectedNodeId)}>
            Use selected node as target
          </button>
        )}
        <NumberSlider label="Max Depth" value={maxDepth} onChange={setMaxDepth} min={1} max={10} />
        <Button
          variant="primary"
          size="sm"
          disabled={!source.trim() || !target.trim()}
          onClick={() => {
            void onSubmit({
              source_id: source.trim(),
              target_id: target.trim(),
              max_depth: maxDepth,
            });
          }}
        >
          Find Path
        </Button>
      </div>
    </Section>
  );
}

function ImpactForm({
  defaultNode,
  onSubmit,
}: Readonly<{
  defaultNode: string;
  onSubmit: (r: { node_id: string; depth?: number; direction?: ImpactDirection }) => Promise<void>;
}>) {
  const [nodeId, setNodeId] = useState(defaultNode);
  const [depth, setDepth] = useState(3);
  const [direction, setDirection] = useState<ImpactDirection>('downstream');

  useEffect(() => {
    if (!nodeId.trim() && defaultNode) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setNodeId(defaultNode);
    }
  }, [defaultNode, nodeId]);

  return (
    <Section title="Impact / Blast Radius">
      <div className="space-y-3">
        <Input label="Node ID" value={nodeId} onChange={(e) => setNodeId(e.target.value)} placeholder="urn:service:…" />
        <NumberSlider label="Depth" value={depth} onChange={setDepth} min={1} max={6} />
        <div>
          <label htmlFor="impact-direction" className="mb-1.5 block text-xs font-medium text-slate-400">
            Direction
          </label>
          <select
            id="impact-direction"
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:ring-1 focus:ring-blue-500 focus:outline-none"
            value={direction}
            onChange={(e) => setDirection(e.target.value as ImpactDirection)}
          >
            <option value="downstream">↓ Downstream</option>
            <option value="upstream">↑ Upstream</option>
            <option value="both">↕ Both</option>
          </select>
        </div>
        <Button
          variant="danger"
          size="sm"
          disabled={!nodeId.trim()}
          onClick={() => {
            void onSubmit({ node_id: nodeId.trim(), depth, direction });
          }}
        >
          Analyze Impact
        </Button>
      </div>
    </Section>
  );
}

function NumberSlider({
  label,
  value,
  onChange,
  min,
  max,
}: Readonly<{
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
}>) {
  const sliderId = useId();
  return (
    <div>
      <div className="mb-1.5 flex justify-between">
        <label htmlFor={sliderId} className="text-xs font-medium text-slate-400">
          {label}
        </label>
        <span className="text-xs font-medium text-blue-400 tabular-nums">{value}</span>
      </div>
      <input
        id={sliderId}
        type="range"
        className="h-1 w-full accent-blue-500"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}
