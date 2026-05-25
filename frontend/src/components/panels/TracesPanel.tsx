import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  fetchTraceDetail,
  fetchTracesList,
  type TraceDetail,
  type TraceSpan,
  type TraceSummary,
} from '../../api/timelineApi';
import { useTimelineStore } from '../../features/graph/store';
import { useTraceReplay } from '../../hooks/useTraceReplay';
import { Button } from '../common/Button';
import { Spinner } from '../common/Spinner';

type SortOrder = 'newest' | 'oldest' | 'slowest' | 'errors';

function ageString(iso: string | null | undefined): string {
  if (!iso) return '-';
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 0) return 'just now';
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

function durationLabel(ms: number): string {
  if (!Number.isFinite(ms) || ms <= 0) return '<1 ms';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

function nsToMs(ns: number | undefined): number {
  return Math.max(0, Number(ns ?? 0) / 1_000_000);
}

function parseOptionalInt(value: string): number | undefined {
  if (!value.trim()) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? Math.floor(parsed) : undefined;
}

function textOr(value: string | null | undefined, fallback: string): string {
  return value?.trim() ? value : fallback;
}

function firstText(...values: Array<string | null | undefined>): string | null {
  return values.find((value) => value?.trim()) ?? null;
}

export function TracesPanel() {
  const windowStart = useTimelineStore((state) => state.windowStart);
  const chunkCount = useTimelineStore((state) => state.chunkCount);
  const chunkBucketSeconds = useTimelineStore((state) => state.chunkBucketSeconds);
  const currentTime = useTimelineStore((state) => state.currentTime);

  const bucketMs = chunkBucketSeconds * 1000;
  const { effStart, effEnd } = useMemo(() => {
    if (currentTime) {
      const currentMs = new Date(currentTime).getTime();
      const slotStart = windowStart + Math.floor((currentMs - windowStart) / bucketMs) * bucketMs;
      return { effStart: slotStart, effEnd: slotStart + bucketMs };
    }
    return { effStart: windowStart, effEnd: windowStart + chunkCount * bucketMs };
  }, [currentTime, windowStart, bucketMs, chunkCount]);

  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<string | null>(null);
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [activeTraceId, setActiveTraceId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TraceDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [spanQuery, setSpanQuery] = useState('');
  const [multiHop, setMultiHop] = useState(true);
  const [errorOnly, setErrorOnly] = useState(false);
  const [minDuration, setMinDuration] = useState('');
  const [maxDuration, setMaxDuration] = useState('');
  const [sortOrder, setSortOrder] = useState<SortOrder>('newest');

  const { play, stop, isPlaying } = useTraceReplay();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchTracesList({
        windowStart: new Date(effStart).toISOString(),
        windowEnd: new Date(effEnd).toISOString(),
        limit: 100,
        multiHop,
        hasErrors: errorOnly ? true : undefined,
        minDurationMs: parseOptionalInt(minDuration),
        maxDurationMs: parseOptionalInt(maxDuration),
      });
      setTraces(response.traces);
      setSource(response.source ?? null);
      if (selectedTraceId && !response.traces.some((trace) => trace.trace_id === selectedTraceId)) {
        setSelectedTraceId(null);
        setDetail(null);
        setSelectedSpanId(null);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Failed to fetch traces');
    } finally {
      setLoading(false);
    }
  }, [effStart, effEnd, multiHop, errorOnly, minDuration, maxDuration, selectedTraceId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    if (!selectedTraceId) return;

    let alive = true;
    const timer = window.setTimeout(() => {
      setDetailLoading(true);
      setDetailError(null);
      void fetchTraceDetail(selectedTraceId)
        .then((data) => {
          if (!alive) return;
          setDetail(data);
          setSelectedSpanId(data.spans.find((span) => span.error?.is_error)?.span_id ?? data.spans[0]?.span_id ?? null);
        })
        .catch((caught) => {
          if (!alive) return;
          setDetail(null);
          setDetailError(caught instanceof Error ? caught.message : 'Failed to load trace detail');
        })
        .finally(() => {
          if (alive) setDetailLoading(false);
        });
    }, 0);

    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [selectedTraceId]);

  const sortedTraces = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const filtered = traces.filter((trace) => {
      if (!needle) return true;
      return [trace.trace_id, trace.root_service, trace.root_name, ...(trace.services_involved ?? [])].some((value) =>
        value.toLowerCase().includes(needle),
      );
    });

    filtered.sort((left, right) => {
      const leftTime = left.start_time ? new Date(left.start_time).getTime() : 0;
      const rightTime = right.start_time ? new Date(right.start_time).getTime() : 0;
      if (sortOrder === 'oldest') return leftTime - rightTime;
      if (sortOrder === 'slowest') return right.duration_ms - left.duration_ms;
      if (sortOrder === 'errors') {
        return Number(right.error_count ?? Number(right.has_errors)) - Number(left.error_count ?? Number(left.has_errors));
      }
      return rightTime - leftTime;
    });
    return filtered;
  }, [traces, query, sortOrder]);

  const handleReplay = useCallback(
    (id: string) => {
      if (isPlaying && activeTraceId === id) {
        stop();
        setActiveTraceId(null);
        return;
      }
      if (isPlaying) stop();
      setActiveTraceId(id);
      void play(id);
    },
    [isPlaying, activeTraceId, play, stop],
  );

  return (
    <div className="flex h-full flex-col bg-slate-950">
      <div className="shrink-0 border-b border-slate-800/70 px-3 py-2">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-xs font-semibold text-slate-200">
              Traces {currentTime ? 'in selected slot' : 'in window'}
            </h3>
            <p className="mt-0.5 truncate text-[10px] text-slate-500 tabular-nums">
              {new Date(effStart).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              {' - '}
              {new Date(effEnd).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              {' | '}
              {sortedTraces.length} matching{source ? ` | ${source}` : ''}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={() => { void load(); }} disabled={loading}>
            {loading ? '...' : 'Refresh'}
          </Button>
        </div>

        <div className="mt-2 grid grid-cols-2 gap-1.5">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search trace/service"
            className="col-span-2 rounded border border-slate-800 bg-slate-900 px-2 py-1 text-[11px] text-slate-200 outline-none placeholder:text-slate-600 focus:border-blue-600"
          />
          <input
            value={minDuration}
            onChange={(event) => setMinDuration(event.target.value)}
            placeholder="Min ms"
            inputMode="numeric"
            className="rounded border border-slate-800 bg-slate-900 px-2 py-1 text-[11px] text-slate-200 outline-none placeholder:text-slate-600 focus:border-blue-600"
          />
          <input
            value={maxDuration}
            onChange={(event) => setMaxDuration(event.target.value)}
            placeholder="Max ms"
            inputMode="numeric"
            className="rounded border border-slate-800 bg-slate-900 px-2 py-1 text-[11px] text-slate-200 outline-none placeholder:text-slate-600 focus:border-blue-600"
          />
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-slate-400">
          <label className="flex cursor-pointer items-center gap-1.5">
            <input
              type="checkbox"
              checked={multiHop}
              onChange={(event) => setMultiHop(event.target.checked)}
              className="h-3 w-3 accent-blue-500"
            />
            Multi-service
          </label>
          <label className="flex cursor-pointer items-center gap-1.5">
            <input
              type="checkbox"
              checked={errorOnly}
              onChange={(event) => setErrorOnly(event.target.checked)}
              className="h-3 w-3 accent-red-500"
            />
            Errors only
          </label>
          <select
            value={sortOrder}
            onChange={(event) => setSortOrder(event.target.value as SortOrder)}
            className="ml-auto rounded border border-slate-800 bg-slate-900 px-1.5 py-0.5 text-[10px] text-slate-300 outline-none"
          >
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
            <option value="slowest">Slowest</option>
            <option value="errors">Errors</option>
          </select>
        </div>
      </div>

      {error && <div className="m-2 rounded border border-red-700/60 bg-red-900/30 px-2 py-1.5 text-[11px] text-red-200">{error}</div>}

      <div className="grid min-h-0 flex-1 grid-rows-[minmax(180px,0.9fr)_minmax(240px,1.1fr)]">
        <div className="scrollbar-thin min-h-0 overflow-y-auto border-b border-slate-800/70">
          {loading && traces.length === 0 && (
            <div className="flex h-full items-center justify-center">
              <Spinner size="md" />
            </div>
          )}

          {!loading && sortedTraces.length === 0 && !error && (
            <div className="flex h-full flex-col items-center justify-center px-4 text-center text-[11px] text-slate-500">
              <p>No traces match the filters.</p>
              <p className="mt-1 text-slate-600">Try a wider time window or disable strict filters.</p>
            </div>
          )}

          {sortedTraces.map((trace) => {
            const selected = selectedTraceId === trace.trace_id;
            const playing = activeTraceId === trace.trace_id && isPlaying;
            return (
              <div
                key={trace.trace_id}
                onClick={() => setSelectedTraceId(trace.trace_id)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    setSelectedTraceId(trace.trace_id);
                  }
                }}
                role="button"
                tabIndex={0}
                className={[
                  'group cursor-pointer border-b border-slate-800/40 px-3 py-2 transition-colors',
                  selected ? 'bg-blue-950/30' : 'hover:bg-slate-900/80',
                ].join(' ')}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className={trace.has_errors ? 'h-2 w-2 shrink-0 rounded-full bg-red-500' : 'h-2 w-2 shrink-0 rounded-full bg-emerald-500'} />
                      <span className="truncate text-[11px] font-semibold text-slate-200">
                        <span className="text-blue-300">{textOr(trace.root_service, 'unknown')}</span>
                        <span className="mx-1 text-slate-600">/</span>
                        <span className="font-mono text-slate-300">{textOr(trace.root_name, '(unnamed)')}</span>
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-slate-500">
                      <span className="tabular-nums">{ageString(trace.start_time)}</span>
                      <span className="tabular-nums text-slate-300">{durationLabel(trace.duration_ms)}</span>
                      <span className="tabular-nums">{trace.span_count ?? 0} spans</span>
                      <span className="tabular-nums">{trace.service_count} svc</span>
                      {(trace.error_count ?? 0) > 0 && <span className="font-mono text-red-400">{trace.error_count} err</span>}
                    </div>
                  </div>
                  <Button
                    variant={playing ? 'danger' : 'ghost'}
                    size="xs"
                    onClick={(event) => {
                      event.stopPropagation();
                      handleReplay(trace.trace_id);
                    }}
                  >
                    {playing ? 'Stop' : 'Replay'}
                  </Button>
                </div>
                {trace.services_involved.length > 0 && (
                  <div className="mt-1 truncate font-mono text-[9px] text-slate-600">{trace.services_involved.join(' -> ')}</div>
                )}
              </div>
            );
          })}
        </div>

        <TraceDetailPane
          detail={detail}
          loading={detailLoading}
          error={detailError}
          selectedSpanId={selectedSpanId}
          spanQuery={spanQuery}
          onSpanQueryChange={setSpanQuery}
          onSelectSpan={setSelectedSpanId}
          onReplay={() => selectedTraceId && handleReplay(selectedTraceId)}
          replaying={isPlaying && activeTraceId === selectedTraceId}
        />
      </div>
    </div>
  );
}

function TraceDetailPane({
  detail,
  loading,
  error,
  selectedSpanId,
  spanQuery,
  onSpanQueryChange,
  onSelectSpan,
  onReplay,
  replaying,
}: Readonly<{
  detail: TraceDetail | null;
  loading: boolean;
  error: string | null;
  selectedSpanId: string | null;
  spanQuery: string;
  onSpanQueryChange: (value: string) => void;
  onSelectSpan: (spanId: string) => void;
  onReplay: () => void;
  replaying: boolean;
}>) {
  const selectedSpan = detail?.spans.find((span) => span.span_id === selectedSpanId) ?? null;
  const filteredSpans = useMemo(() => {
    if (!detail) return [];
    const needle = spanQuery.trim().toLowerCase();
    if (!needle) return detail.spans;
    return detail.spans.filter((span) =>
      [span.span_name, span.operation_name ?? '', span.service_name ?? '', span.span_kind ?? '', span.error?.kind ?? '', span.error?.message ?? ''].some((value) =>
        value.toLowerCase().includes(needle),
      ),
    );
  }, [detail, spanQuery]);

  if (loading) return <div className="flex min-h-0 items-center justify-center"><Spinner size="md" /></div>;
  if (error) return <div className="m-3 rounded border border-red-800 bg-red-950/40 p-3 text-[11px] text-red-200">{error}</div>;
  if (!detail) {
    return (
      <div className="flex min-h-0 flex-col items-center justify-center px-5 text-center text-[11px] text-slate-500">
        <p>Select a trace to inspect spans, errors, and latency.</p>
      </div>
    );
  }

  return (
    <div className="scrollbar-thin min-h-0 overflow-y-auto px-3 py-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className={detail.has_errors ? 'h-2.5 w-2.5 rounded-full bg-red-500' : 'h-2.5 w-2.5 rounded-full bg-emerald-500'} />
            <h4 className="truncate text-xs font-semibold text-slate-100">{textOr(detail.root_service, 'unknown')}</h4>
          </div>
          <p className="mt-0.5 truncate font-mono text-[10px] text-slate-500">{detail.trace_id}</p>
        </div>
        <Button variant={replaying ? 'danger' : 'secondary'} size="xs" onClick={onReplay}>{replaying ? 'Stop' : 'Replay'}</Button>
      </div>

      <div className="mt-2 grid grid-cols-4 gap-1.5 text-center">
        <Metric label="duration" value={durationLabel(detail.duration_ms)} />
        <Metric label="spans" value={String(detail.span_count)} />
        <Metric label="errors" value={String(detail.error_count)} tone={detail.error_count > 0 ? 'red' : 'slate'} />
        <Metric label="hops" value={String(detail.hop_count)} />
      </div>

      <input
        value={spanQuery}
        onChange={(event) => onSpanQueryChange(event.target.value)}
        placeholder="Filter spans"
        className="mt-2 w-full rounded border border-slate-800 bg-slate-900 px-2 py-1 text-[11px] text-slate-200 outline-none placeholder:text-slate-600 focus:border-blue-600"
      />

      <SpanWaterfall spans={filteredSpans} selectedSpanId={selectedSpanId} onSelectSpan={onSelectSpan} />
      <SpanTree spans={filteredSpans} allSpans={detail.spans} selectedSpanId={selectedSpanId} onSelectSpan={onSelectSpan} />
      {selectedSpan && <SpanInspector span={selectedSpan} />}
    </div>
  );
}

function Metric({ label, value, tone = 'slate' }: Readonly<{ label: string; value: string; tone?: 'slate' | 'red' }>) {
  return (
    <div className="rounded border border-slate-800 bg-slate-900/80 px-1.5 py-1">
      <div className={tone === 'red' ? 'font-mono text-[11px] text-red-300' : 'font-mono text-[11px] text-slate-200'}>{value}</div>
      <div className="text-[9px] uppercase tracking-wide text-slate-600">{label}</div>
    </div>
  );
}

function SpanWaterfall({ spans, selectedSpanId, onSelectSpan }: Readonly<{ spans: TraceSpan[]; selectedSpanId: string | null; onSelectSpan: (spanId: string) => void }>) {
  if (spans.length === 0) return null;
  const starts = spans.map((span) => Number(span.start_time_ns ?? 0)).filter((value) => value > 0);
  const ends = spans.map((span) => Number(span.end_time_ns ?? 0)).filter((value) => value > 0);
  const base = starts.length ? Math.min(...starts) : 0;
  const total = Math.max(1, (ends.length ? Math.max(...ends) : base) - base);

  return (
    <div className="mt-3 rounded border border-slate-800 bg-slate-900/40 p-2">
      <div className="mb-1.5 flex items-center justify-between text-[10px] text-slate-500">
        <span>Waterfall</span>
        <span>{durationLabel(total / 1_000_000)}</span>
      </div>
      <div className="space-y-1.5">
        {spans.map((span) => {
          const left = base > 0 ? Math.max(0, ((Number(span.start_time_ns ?? 0) - base) / total) * 100) : 0;
          const width = Math.max(1.5, (Number(span.duration_ns ?? 0) / total) * 100);
          const selected = span.span_id === selectedSpanId;
          return (
            <button
              key={span.span_id}
              onClick={() => onSelectSpan(span.span_id)}
              className={['grid w-full grid-cols-[7.5rem_1fr_3.5rem] items-center gap-2 rounded px-1 py-0.5 text-left', selected ? 'bg-blue-950/50' : 'hover:bg-slate-800/70'].join(' ')}
            >
              <span className="truncate text-[10px] text-slate-400">{textOr(span.service_name, 'unknown')}</span>
              <span className="relative h-3 overflow-hidden rounded bg-slate-800">
                <span
                  className={span.error?.is_error ? 'absolute top-0 h-3 rounded bg-red-500' : 'absolute top-0 h-3 rounded bg-blue-500'}
                  style={{ left: `${Math.min(99, left)}%`, width: `${Math.min(100 - left, width)}%` }}
                />
              </span>
              <span className="text-right font-mono text-[10px] text-slate-500">{durationLabel(nsToMs(span.duration_ns))}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function SpanTree({ spans, allSpans, selectedSpanId, onSelectSpan }: Readonly<{ spans: TraceSpan[]; allSpans: TraceSpan[]; selectedSpanId: string | null; onSelectSpan: (spanId: string) => void }>) {
  if (spans.length === 0) return null;
  const visibleIds = new Set(spans.map((span) => span.span_id));
  const allIds = new Set(allSpans.map((span) => span.span_id));
  const byParent = new Map<string | null, TraceSpan[]>();
  for (const span of spans) {
    const parent = span.parent_span_id && allIds.has(span.parent_span_id) ? span.parent_span_id : null;
    const list = byParent.get(parent) ?? [];
    list.push(span);
    byParent.set(parent, list);
  }
  for (const list of byParent.values()) list.sort((left, right) => Number(left.start_time_ns ?? 0) - Number(right.start_time_ns ?? 0));

  const rows: Array<{ span: TraceSpan; depth: number }> = [];
  const visit = (span: TraceSpan, depth: number) => {
    if (visibleIds.has(span.span_id)) rows.push({ span, depth });
    for (const child of byParent.get(span.span_id) ?? []) visit(child, depth + 1);
  };
  for (const root of byParent.get(null) ?? []) visit(root, 0);

  return (
    <div className="mt-3 rounded border border-slate-800 bg-slate-900/40 p-2">
      <div className="mb-1.5 text-[10px] text-slate-500">Span tree</div>
      <div className="space-y-0.5">
        {rows.map(({ span, depth }) => {
          const selected = span.span_id === selectedSpanId;
          return (
            <button
              key={span.span_id}
              onClick={() => onSelectSpan(span.span_id)}
              className={['flex w-full items-center gap-2 rounded px-1.5 py-1 text-left', selected ? 'bg-blue-950/50' : 'hover:bg-slate-800/70'].join(' ')}
              style={{ paddingLeft: `${6 + depth * 12}px` }}
            >
              <span className={span.error?.is_error ? 'h-2 w-2 shrink-0 rounded-full bg-red-500' : 'h-2 w-2 shrink-0 rounded-full bg-emerald-500'} />
              <span className="min-w-0 flex-1 truncate text-[10px] text-slate-300">{firstText(span.operation_name, span.span_name) ?? '(unnamed span)'}</span>
              <span className="shrink-0 font-mono text-[9px] text-slate-600">{durationLabel(nsToMs(span.duration_ns))}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function SpanInspector({ span }: Readonly<{ span: TraceSpan }>) {
  const attributes = Object.entries(span.attributes ?? {}).filter(([, value]) => value !== null && value !== undefined && value !== '');
  return (
    <div className="mt-3 rounded border border-slate-800 bg-slate-900/40 p-2">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-[11px] font-semibold text-slate-200">{firstText(span.operation_name, span.span_name) ?? '(unnamed span)'}</div>
          <div className="truncate font-mono text-[9px] text-slate-600">{span.span_id}</div>
        </div>
        <span className={span.error?.is_error ? 'rounded bg-red-500/15 px-1.5 py-0.5 text-[9px] font-semibold uppercase text-red-300' : 'rounded bg-emerald-500/15 px-1.5 py-0.5 text-[9px] font-semibold uppercase text-emerald-300'}>
          {span.error?.is_error ? 'error' : 'ok'}
        </span>
      </div>
      <div className="grid grid-cols-[5.5rem_1fr] gap-x-2 gap-y-1 text-[10px]">
        <Info label="service" value={span.service_name} />
        <Info label="kind" value={span.span_kind} />
        <Info label="duration" value={durationLabel(nsToMs(span.duration_ns))} />
        <Info label="http" value={span.http_status_code ? String(span.http_status_code) : null} tone={span.error?.is_error ? 'red' : 'slate'} />
        <Info label="error" value={firstText(span.error?.message, span.error?.kind)} tone="red" />
      </div>
      {attributes.length > 0 && (
        <div className="mt-2 border-t border-slate-800 pt-2">
          <div className="mb-1 text-[10px] text-slate-500">Attributes</div>
          <div className="max-h-32 overflow-y-auto rounded bg-slate-950/70 p-1.5 font-mono text-[9px] text-slate-400">
            {attributes.map(([key, value]) => (
              <div key={key} className="grid grid-cols-[7rem_1fr] gap-2 border-b border-slate-900 py-0.5 last:border-b-0">
                <span className="truncate text-slate-600">{key}</span>
                <span className="truncate">{String(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Info({ label, value, tone = 'slate' }: Readonly<{ label: string; value?: string | null; tone?: 'slate' | 'red' }>) {
  if (!value) return null;
  return (
    <>
      <span className="text-slate-600">{label}</span>
      <span className={tone === 'red' ? 'truncate text-red-300' : 'truncate text-slate-300'}>{value}</span>
    </>
  );
}