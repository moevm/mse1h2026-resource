import { useCallback, useEffect, useMemo, useState } from 'react';

import { fetchTracesList, type TraceSummary } from '../../api/timelineApi';
import { useTimelineStore } from '../../features/graph/store';
import { useTraceReplay } from '../../hooks/useTraceReplay';
import { Button } from '../common/Button';
import { Spinner } from '../common/Spinner';

type SortOrder = 'newest' | 'oldest';

function ageString(iso: string | null): string {
  if (!iso) return '—';
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 0) return 'just now';
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  return `${h}h ago`;
}

function durationLabel(ms: number): string {
  if (ms < 1) return '<1 ms';
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

export function TracesPanel() {
  const windowStart = useTimelineStore((s) => s.windowStart);
  const chunkCount = useTimelineStore((s) => s.chunkCount);
  const chunkBucketSeconds = useTimelineStore((s) => s.chunkBucketSeconds);
  const currentTime = useTimelineStore((s) => s.currentTime);

  const bucketMs = chunkBucketSeconds * 1000;
  const { effStart, effEnd } = useMemo(() => {
    if (currentTime) {
      const ctMs = new Date(currentTime).getTime();
      const slotStart = windowStart + Math.floor((ctMs - windowStart) / bucketMs) * bucketMs;
      return { effStart: slotStart, effEnd: slotStart + bucketMs };
    }
    return { effStart: windowStart, effEnd: windowStart + chunkCount * bucketMs };
  }, [currentTime, windowStart, bucketMs, chunkCount]);

  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTraceId, setActiveTraceId] = useState<string | null>(null);
  const [multiHop, setMultiHop] = useState(true);
  const [sortOrder, setSortOrder] = useState<SortOrder>('newest');

  const { play, stop, isPlaying } = useTraceReplay();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetchTracesList({
        windowStart: new Date(effStart).toISOString(),
        windowEnd: new Date(effEnd).toISOString(),
        limit: 100,
        multiHop,
      });
      setTraces(resp.traces);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch traces');
    } finally {
      setLoading(false);
    }
  }, [effStart, effEnd, multiHop]);

  useEffect(() => {
    void load();
  }, [load]);

  const sortedTraces = useMemo(() => {
    const ts = (t: TraceSummary) => (t.start_time ? new Date(t.start_time).getTime() : 0);
    const arr = [...traces];
    arr.sort((a, b) => (sortOrder === 'newest' ? ts(b) - ts(a) : ts(a) - ts(b)));
    return arr;
  }, [traces, sortOrder]);

  const handleReplay = useCallback((id: string) => {
    if (isPlaying && activeTraceId === id) {
      stop();
      setActiveTraceId(null);
      return;
    }
    if (isPlaying) stop();
    setActiveTraceId(id);
    void play(id);
  }, [isPlaying, activeTraceId, play, stop]);

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-slate-800/70 px-3 py-2">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-semibold text-slate-200">
              Traces {currentTime ? 'in selected slot' : 'in window'}
            </h3>
            <p className="mt-0.5 text-[10px] text-slate-500 tabular-nums">
              {new Date(effStart).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              {' – '}
              {new Date(effEnd).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              {' · '}
              {traces.length} matching
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={load} disabled={loading}>
            {loading ? '...' : 'Refresh'}
          </Button>
        </div>

        <div className="mt-2 flex items-center gap-3 text-[10px] text-slate-400">
          <label className="flex cursor-pointer items-center gap-1.5">
            <input
              type="checkbox"
              checked={multiHop}
              onChange={(e) => setMultiHop(e.target.checked)}
              className="h-3 w-3 accent-blue-500"
            />
            Multi-service only
          </label>
          <button
            onClick={() => setSortOrder((o) => (o === 'newest' ? 'oldest' : 'newest'))}
            className="ml-auto flex items-center gap-1 rounded bg-slate-800/70 px-1.5 py-0.5 text-[10px] text-slate-300 hover:bg-slate-700/70"
            title={`Click to sort ${sortOrder === 'newest' ? 'oldest → newest' : 'newest → oldest'}`}
          >
            {sortOrder === 'newest' ? 'Newest first ↓' : 'Oldest first ↑'}
          </button>
        </div>
      </div>

      {error && (
        <div className="m-2 rounded border border-red-700/60 bg-red-900/30 px-2 py-1.5 text-[11px] text-red-200">
          {error}
        </div>
      )}

      {loading && traces.length === 0 && (
        <div className="flex flex-1 items-center justify-center">
          <Spinner size="md" />
        </div>
      )}

      {!loading && traces.length === 0 && !error && (
        <div className="flex flex-1 flex-col items-center justify-center px-4 text-center text-[11px] text-slate-500">
          <p>No traces match the filters.</p>
          <p className="mt-1 text-slate-600">
            Try unchecking Multi-service or expanding the timeline window.
          </p>
        </div>
      )}

      <div className="scrollbar-thin flex-1 overflow-y-auto">
        {sortedTraces.map((t) => {
          const isActive = activeTraceId === t.trace_id;
          const playing = isActive && isPlaying;
          return (
            <button
              key={t.trace_id}
              onClick={() => handleReplay(t.trace_id)}
              className={[
                'group block w-full border-b border-slate-800/40 px-3 py-2 text-left transition-colors',
                isActive ? 'bg-cyan-900/20' : 'hover:bg-slate-800/50',
              ].join(' ')}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="min-w-0 flex-1 truncate text-[11px] font-semibold text-slate-200">
                  <span className="text-cyan-400">{t.root_service}</span>
                  <span className="mx-1 text-slate-600">·</span>
                  <span className="font-mono text-slate-300">{t.root_name || '(unnamed)'}</span>
                </span>
                <span
                  className={[
                    'shrink-0 rounded px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide transition-colors',
                    playing ? 'bg-cyan-500/20 text-cyan-300' : 'bg-slate-700/50 text-slate-400 group-hover:bg-slate-700',
                  ].join(' ')}
                >
                  {playing ? 'Stop' : 'Replay'}
                </span>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[10px] text-slate-500">
                <span className="tabular-nums">{ageString(t.start_time)}</span>
                <span className="tabular-nums">{durationLabel(t.duration_ms)}</span>
                <span className="tabular-nums">
                  <span className="text-slate-400">{t.service_count}</span> svc
                  <span className="mx-1 text-slate-700">·</span>
                  <span className="text-slate-400">{t.hop_count}</span> hop{t.hop_count === 1 ? '' : 's'}
                </span>
                {t.has_errors && (
                  <span className="rounded bg-red-500/15 px-1.5 py-0 font-mono text-[9px] uppercase tracking-wide text-red-400">
                    err
                  </span>
                )}
              </div>
              {t.services_involved.length > 0 && (
                <div className="mt-1 truncate font-mono text-[9px] text-slate-600">
                  {t.services_involved.join(' → ')}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
