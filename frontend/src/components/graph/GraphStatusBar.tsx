import { useCallback, useEffect, useRef, useState } from 'react';

import { type TimelineRange, fetchTimelineRange } from '../../api/graphApi';
import { useCyContext } from '../../context/CytoscapeContext';
import { useGraphDataStore, useGraphUiStore } from '../../features/graph/store';
import { useGraph } from '../../hooks/useGraph';

const REFRESH_INTERVAL = 30_000;
const DEBOUNCE_MS = 300;

interface Props {
  limit?: number;
}

export function GraphStatusBar({ limit = 500 }: Props) {
  const nodes = useGraphDataStore((s) => s.nodes);
  const edges = useGraphDataStore((s) => s.edges);
  const selectedNodeId = useGraphUiStore((s) => s.selectedNodeId);
  const selectedAppId = useGraphUiStore((s) => s.selectedAppId);
  const loading = useGraphUiStore((s) => s.loading);
  const { loadFullGraph } = useGraph();
  const { fitGraph } = useCyContext();

  const [range, setRange] = useState<TimelineRange | null>(null);
  const [isLive, setIsLive] = useState(true);
  const [sliderValue, setSliderValue] = useState(100);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  const nodeTypes = new Set(nodes.map((n) => n.type)).size;
  const edgeTypes = new Set(edges.map((e) => e.type)).size;

  const minTs = range?.min_time ? new Date(range.min_time).getTime() : 0;
  const [nowTs] = useState(() => Date.now());
  const maxTs = range?.max_time ? new Date(range.max_time).getTime() : nowTs;

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const r = await fetchTimelineRange();
        if (mounted && r.min_time) setRange(r);
      } catch {
        /* retry on interval */
      }
    };
    void load();
    const id = setInterval(() => void load(), REFRESH_INTERVAL);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  const handleSlider = useCallback(
    (value: number) => {
      setSliderValue(value);
      setIsLive(false);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        const ts = minTs + ((maxTs - minTs) * value) / 100;
        const iso = new Date(ts).toISOString();
        void loadFullGraph(limit, selectedAppId ?? undefined, iso).then(() => fitGraph());
      }, DEBOUNCE_MS);
    },
    [minTs, maxTs, limit, selectedAppId, loadFullGraph, fitGraph],
  );

  const goLive = useCallback(() => {
    setIsLive(true);
    setSliderValue(100);
    void loadFullGraph(limit, selectedAppId ?? undefined).then(() => fitGraph());
  }, [limit, selectedAppId, loadFullGraph, fitGraph]);

  const selectedTs = isLive ? 0 : minTs + ((maxTs - minTs) * sliderValue) / 100;

  return (
    <div className="shrink-0 border-t border-slate-800/70 bg-slate-950/70">
      {/* Row 1: Stats */}
      <div className="flex h-8 items-center gap-3 px-4 text-[11px]">
        <Stat label="Nodes" value={nodes.length} />
        <div className="h-3 w-px bg-slate-800" />
        <Stat label="Edges" value={edges.length} />
        <div className="h-3 w-px bg-slate-800" />
        <Stat label="Types" value={nodeTypes} />
        <div className="h-3 w-px bg-slate-800" />
        <Stat label="Edge types" value={edgeTypes} />
        {selectedNodeId && (
          <span className="ml-auto max-w-48 truncate font-mono text-[10px] text-blue-400">{selectedNodeId}</span>
        )}
      </div>

      {/* Row 2: Timeline — only when range data is available */}
      {range?.min_time && (
        <div className="flex items-center gap-2 px-4 pt-1 pb-2">
          <span className="min-w-36 font-mono text-[11px] whitespace-nowrap text-slate-400">
            {isLive
              ? '● Live'
              : new Date(selectedTs).toLocaleString('ru-RU', {
                  day: '2-digit',
                  month: '2-digit',
                  year: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                })}
          </span>

          <input
            type="range"
            min={0}
            max={100}
            value={sliderValue}
            onChange={(e) => handleSlider(Number(e.target.value))}
            className="h-1.5 flex-1 cursor-pointer accent-blue-500 disabled:opacity-40"
            disabled={loading}
          />

          {!isLive && (
            <button
              onClick={goLive}
              disabled={loading}
              className="rounded bg-blue-600 px-2.5 py-0.5 text-[10px] font-semibold whitespace-nowrap text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
            >
              Live
            </button>
          )}

          <span className="text-[10px] whitespace-nowrap text-slate-600">
            {new Date(minTs).toLocaleDateString('ru-RU')} — {new Date(maxTs).toLocaleDateString('ru-RU')}
          </span>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: Readonly<{ label: string; value: number }>) {
  return (
    <span>
      <span className="text-slate-600">{label}: </span>
      <span className="font-medium text-slate-300 tabular-nums">{value.toLocaleString()}</span>
    </span>
  );
}
