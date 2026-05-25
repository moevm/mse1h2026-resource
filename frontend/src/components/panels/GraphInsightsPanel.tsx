import { useMemo, useState } from 'react';

import { useCyContext } from '../../context/CytoscapeContext';
import { useGraphDataStore, useGraphUiStore } from '../../features/graph/store';
import { collectNeighborhood, computeGraphInsights, findShortestPathLocal } from '../../utils/graphAnalysis';
import { Button } from '../common/Button';
import { Section } from '../common/Card';
import { Input } from '../common/Input';

export default function GraphInsightsPanel() {
  const nodes = useGraphDataStore((s) => s.nodes);
  const edges = useGraphDataStore((s) => s.edges);
  const selectedNodeId = useGraphUiStore((s) => s.selectedNodeId);
  const selectNode = useGraphUiStore((s) => s.selectNode);
  const setHighlightedNodes = useGraphUiStore((s) => s.setHighlightedNodes);
  const setHighlightedEdges = useGraphUiStore((s) => s.setHighlightedEdges);
  const setFocusedNodes = useGraphUiStore((s) => s.setFocusedNodes);
  const clearVisualFocus = useGraphUiStore((s) => s.clearVisualFocus);
  const { centerOn } = useCyContext();

  const [sourceId, setSourceId] = useState('');
  const [targetId, setTargetId] = useState('');
  const [pathDirection, setPathDirection] = useState<'directed' | 'undirected'>('directed');
  const [pathDepthLimit, setPathDepthLimit] = useState(10);
  const [pathResult, setPathResult] = useState<string | null>(null);

  const [focusDepth, setFocusDepth] = useState(2);
  const [focusDirection, setFocusDirection] = useState<'incoming' | 'outgoing' | 'both'>('both');
  const [focusResult, setFocusResult] = useState<string | null>(null);

  const insights = useMemo(() => computeGraphInsights(nodes, edges), [nodes, edges]);

  const onFindLocalPath = () => {
    const source = sourceId.trim();
    const target = targetId.trim();

    const found = findShortestPathLocal(nodes, edges, source, target, {
      direction: pathDirection,
      maxDepth: pathDepthLimit,
    });

    if (!found) {
      setPathResult('Path not found in the currently loaded graph.');
      return;
    }

    setHighlightedNodes(new Set(found.nodeIds));
    setHighlightedEdges(new Set(found.edgeIds));
    setFocusedNodes(new Set(found.nodeIds));

    const last = found.nodeIds.at(-1);
    if (last) {
      selectNode(last);
      centerOn(last);
    }

    setPathResult(`Path found: ${found.hops} hop(s), ${found.nodeIds.length} node(s).`);
  };

  const onFocusNeighborhood = () => {
    const center = selectedNodeId ?? sourceId.trim();
    if (!center) {
      setFocusResult('Select a node or set Source ID first.');
      return;
    }

    const neighborhood = collectNeighborhood(nodes, edges, center, focusDepth, focusDirection);
    if (neighborhood.nodeIds.size === 0) {
      setFocusResult('Center node is not in current graph view.');
      return;
    }

    setFocusedNodes(neighborhood.nodeIds);
    setHighlightedNodes(neighborhood.nodeIds);
    setHighlightedEdges(neighborhood.edgeIds);
    centerOn(center);

    setFocusResult(`Focused neighborhood: ${neighborhood.nodeIds.size} node(s), ${neighborhood.edgeIds.size} edge(s).`);
  };

  return (
    <div className="flex max-h-full flex-col gap-5 overflow-y-auto p-4">
      <Section title="Quick Graph Insights">
        <div className="space-y-2 text-xs text-slate-300">
          <InsightRow label="Nodes" value={insights.nodeCount.toLocaleString()} />
          <InsightRow label="Edges" value={insights.edgeCount.toLocaleString()} />
          <InsightRow label="Avg out-degree" value={insights.avgOutDegree.toFixed(2)} />
          <InsightRow label="Weak components" value={insights.weaklyConnectedComponents.toLocaleString()} />
        </div>
        {insights.topByDegree.length > 0 && (
          <div className="mt-3 border-t border-slate-800/70 pt-3">
            <p className="mb-2 text-[11px] tracking-wide text-slate-500 uppercase">Top connected nodes</p>
            <div className="space-y-1.5">
              {insights.topByDegree.map((entry) => (
                <button
                  key={entry.id}
                  onClick={() => {
                    selectNode(entry.id);
                    centerOn(entry.id);
                  }}
                  className="w-full rounded-md bg-slate-800/60 px-2.5 py-1.5 text-left hover:bg-slate-800"
                >
                  <div className="truncate text-xs text-slate-200">{entry.id}</div>
                  <div className="text-[10px] text-slate-500">degree: {entry.degree}</div>
                </button>
              ))}
            </div>
          </div>
        )}
      </Section>

      <div className="border-t border-slate-800" />

      <Section title="Local Path Finder">
        <div className="space-y-3">
          <Input
            label="Source ID"
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
            placeholder="urn:service:payment-api"
          />
          <Input
            label="Target ID"
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            placeholder="urn:database:postgres-orders"
          />

          <div>
            <label htmlFor="local-path-direction" className="mb-1.5 block text-xs font-medium text-slate-400">
              Direction mode
            </label>
            <select
              id="local-path-direction"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              value={pathDirection}
              onChange={(e) => setPathDirection(e.target.value as 'directed' | 'undirected')}
            >
              <option value="directed">Directed edges</option>
              <option value="undirected">Undirected (ignore direction)</option>
            </select>
          </div>

          <Input
            label="Max depth"
            type="number"
            value={pathDepthLimit}
            onChange={(e) => setPathDepthLimit(Number(e.target.value))}
            min={1}
            max={50}
          />

          <Button variant="primary" size="sm" disabled={!sourceId.trim() || !targetId.trim()} onClick={onFindLocalPath}>
            Find Path In Current Graph
          </Button>

          {pathResult && (
            <p className="rounded-md border border-slate-800/70 bg-slate-900/70 px-2.5 py-1.5 text-xs text-slate-400">
              {pathResult}
            </p>
          )}
        </div>
      </Section>

      <div className="border-t border-slate-800" />

      <Section title="Neighborhood Focus">
        <div className="space-y-3">
          <p className="text-xs text-slate-500">Uses selected node as center. If none selected, Source ID is used.</p>

          <Input
            label="Depth"
            type="number"
            value={focusDepth}
            onChange={(e) => setFocusDepth(Number(e.target.value))}
            min={1}
            max={8}
          />

          <div>
            <label htmlFor="focus-direction" className="mb-1.5 block text-xs font-medium text-slate-400">
              Traversal direction
            </label>
            <select
              id="focus-direction"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              value={focusDirection}
              onChange={(e) => setFocusDirection(e.target.value as 'incoming' | 'outgoing' | 'both')}
            >
              <option value="both">Both</option>
              <option value="outgoing">Outgoing only</option>
              <option value="incoming">Incoming only</option>
            </select>
          </div>

          <Button variant="secondary" size="sm" onClick={onFocusNeighborhood}>
            Focus Neighborhood
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              clearVisualFocus();
              setPathResult(null);
              setFocusResult(null);
            }}
          >
            Clear Focus & Highlights
          </Button>

          {focusResult && (
            <p className="rounded-md border border-slate-800/70 bg-slate-900/70 px-2.5 py-1.5 text-xs text-slate-400">
              {focusResult}
            </p>
          )}
        </div>
      </Section>
    </div>
  );
}

function InsightRow({ label, value }: Readonly<{ label: string; value: string }>) {
  return (
    <div className="flex items-center justify-between rounded-md border border-slate-800/60 bg-slate-900/70 px-2.5 py-1.5">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-200 tabular-nums">{value}</span>
    </div>
  );
}
