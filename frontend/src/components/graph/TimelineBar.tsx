import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useTimelineStore, type PlaybackSpeed } from '../../features/graph/store';
import { useGraphDataStore, useGraphUiStore } from '../../features/graph/store';
import { useGraph } from '../../hooks/useGraph';
import { useCyContext } from '../../context/CytoscapeContext';

const REFRESH_RANGE_MS = 30_000;
const REFRESH_EVENTS_MS = 15_000;
const BUCKET_SECONDS = 15;
const DEBOUNCE_MS = 300;

const SPEED_OPTIONS: PlaybackSpeed[] = [1, 2, 5, 10];

const NODE_TYPE_COLORS: Record<string, string> = {
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
  RegionCluster: '#84cc16',
  Node: '#fbbf24',
};

export function TimelineBar({ limit = 500 }: Readonly<{ limit?: number }>) {
  const nodes = useGraphDataStore((s) => s.nodes);
  const edges = useGraphDataStore((s) => s.edges);
  const selectedAppId = useGraphUiStore((s) => s.selectedAppId);
  const { loadFullGraph } = useGraph();
  const { fitGraph } = useCyContext();

  const range = useTimelineStore((s) => s.range);
  const events = useTimelineStore((s) => s.events);
  const currentTime = useTimelineStore((s) => s.currentTime);
  const isPlaying = useTimelineStore((s) => s.isPlaying);
  const playbackSpeed = useTimelineStore((s) => s.playbackSpeed);
  const rangeLoading = useTimelineStore((s) => s.rangeLoading);
  const fetchRange = useTimelineStore((s) => s.fetchRange);
  const fetchEvents = useTimelineStore((s) => s.fetchEvents);
  const goLive = useTimelineStore((s) => s.goLive);
  const setPlaybackSpeed = useTimelineStore((s) => s.setPlaybackSpeed);

  const [trackWidth, setTrackWidth] = useState(0);
  const trackRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const playbackRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const playbackIdxRef = useRef(0);

  const nodeTypes = useMemo(() => new Set(nodes.map((n) => n.type)).size, [nodes]);
  const edgeTypes = useMemo(() => new Set(edges.map((e) => e.type)).size, [edges]);
  const isLive = currentTime === null;

  // Fetch range periodically
  useEffect(() => {
    void fetchRange();
    const id = setInterval(() => void fetchRange(), REFRESH_RANGE_MS);
    return () => clearInterval(id);
  }, [fetchRange]);

  // Fetch events when range appears
  useEffect(() => {
    if (!range?.min_time) return;
    void fetchEvents(BUCKET_SECONDS);
    const id = setInterval(() => void fetchEvents(BUCKET_SECONDS), REFRESH_EVENTS_MS);
    return () => clearInterval(id);
  }, [range?.min_time, fetchEvents]);

  // Observe track width
  useEffect(() => {
    const el = trackRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setTrackWidth(entry.contentRect.width);
      }
    });
    observer.observe(el);
    // Also set initial width
    setTrackWidth(el.clientWidth);
    return () => observer.disconnect();
  }, [range, events]);

  const timeRange = useMemo(() => {
    if (!range?.min_time || !range?.max_time) return null;
    return {
      min: new Date(range.min_time).getTime(),
      max: new Date(range.max_time).getTime(),
    };
  }, [range]);

  const timeToX = useCallback(
    (ts: number): number => {
      if (!timeRange || timeRange.max === timeRange.min || trackWidth === 0) return 0;
      return ((ts - timeRange.min) / (timeRange.max - timeRange.min)) * trackWidth;
    },
    [timeRange, trackWidth],
  );

  const xToTime = useCallback(
    (x: number): number => {
      if (!timeRange || trackWidth === 0) return timeRange?.min ?? Date.now();
      return timeRange.min + (x / trackWidth) * (timeRange.max - timeRange.min);
    },
    [timeRange, trackWidth],
  );

  // Load graph at specific time (debounced for drag, immediate for click)
  const loadAtTimeImmediate = useCallback(
    (iso: string) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = null;
      void loadFullGraph(limit, selectedAppId ?? undefined, iso).then(() => {
        try { fitGraph(); } catch { /* cy not ready */ }
      }).catch(() => {});
    },
    [limit, selectedAppId, loadFullGraph, fitGraph],
  );

  const loadAtTimeDebounced = useCallback(
    (iso: string) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        debounceRef.current = null;
        void loadFullGraph(limit, selectedAppId ?? undefined, iso).then(() => {
          try { fitGraph(); } catch { /* cy not ready */ }
        }).catch(() => {});
      }, DEBOUNCE_MS);
    },
    [limit, selectedAppId, loadFullGraph, fitGraph],
  );

  // --- Playback ---
  const stopPlayback = useCallback(() => {
    if (playbackRef.current) {
      clearInterval(playbackRef.current);
      playbackRef.current = null;
    }
    useTimelineStore.setState({ isPlaying: false });
  }, []);

  const startPlayback = useCallback(() => {
    stopPlayback();
    const evts = useTimelineStore.getState().events;
    if (evts.length === 0) return;

    const ct = useTimelineStore.getState().currentTime;
    let startIdx = 0;
    if (ct) {
      startIdx = evts.findIndex((e) => e.timestamp >= ct);
      if (startIdx < 0) startIdx = 0;
    }
    playbackIdxRef.current = startIdx;

    const speed = useTimelineStore.getState().playbackSpeed;
    const intervals: Record<PlaybackSpeed, number> = { 1: 2000, 2: 1000, 5: 500, 10: 300 };

    useTimelineStore.setState({ isPlaying: true });

    playbackRef.current = setInterval(() => {
      const idx = playbackIdxRef.current;
      const currentEvts = useTimelineStore.getState().events;
      if (idx >= currentEvts.length) {
        stopPlayback();
        return;
      }
      const ev = currentEvts[idx];
      useTimelineStore.setState({ currentTime: ev.timestamp });
      loadAtTimeImmediate(ev.timestamp);
      playbackIdxRef.current = idx + 1;
    }, intervals[speed]);
  }, [stopPlayback, loadAtTimeImmediate]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (playbackRef.current) clearInterval(playbackRef.current);
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const handlePlayPause = useCallback(() => {
    if (isPlaying) {
      stopPlayback();
    } else {
      startPlayback();
    }
  }, [isPlaying, startPlayback, stopPlayback]);

  const handleGoLive = useCallback(() => {
    stopPlayback();
    goLive();
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = null;
    void loadFullGraph(limit, selectedAppId ?? undefined).then(() => {
      try { fitGraph(); } catch { /* cy not ready */ }
    }).catch(() => {});
  }, [stopPlayback, goLive, limit, selectedAppId, loadFullGraph, fitGraph]);

  const handleStepForward = useCallback(() => {
    stopPlayback();
    const evts = useTimelineStore.getState().events;
    if (evts.length === 0) return;
    const ct = useTimelineStore.getState().currentTime;
    let idx = ct ? evts.findIndex((e) => e.timestamp > ct) : 0;
    if (idx < 0) idx = evts.length - 1;
    const nextTime = evts[idx].timestamp;
    useTimelineStore.setState({ currentTime: nextTime });
    loadAtTimeImmediate(nextTime);
  }, [stopPlayback, loadAtTimeImmediate]);

  const handleStepBackward = useCallback(() => {
    stopPlayback();
    const evts = useTimelineStore.getState().events;
    if (evts.length === 0) return;
    const ct = useTimelineStore.getState().currentTime;
    if (!ct) {
      // If live, jump to last event
      const lastTime = evts[evts.length - 1].timestamp;
      useTimelineStore.setState({ currentTime: lastTime });
      loadAtTimeImmediate(lastTime);
      return;
    }
    const idx = evts.findIndex((e) => e.timestamp >= ct);
    const prevIdx = Math.max(0, idx - 1);
    const prevTime = evts[prevIdx].timestamp;
    useTimelineStore.setState({ currentTime: prevTime });
    loadAtTimeImmediate(prevTime);
  }, [stopPlayback, loadAtTimeImmediate]);

  // --- Track interaction ---
  const handleTrackMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!timeRange || trackWidth === 0) return;
      const el = trackRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();

      stopPlayback();

      const scrubTo = (clientX: number) => {
        const nx = clientX - rect.left;
        const clamped = Math.max(0, Math.min(el.clientWidth, nx));
        const ts = xToTime(clamped);
        const iso = new Date(ts).toISOString();
        useTimelineStore.setState({ currentTime: iso });
        loadAtTimeDebounced(iso);
      };

      scrubTo(e.clientX);

      const onMove = (ev: MouseEvent) => {
        ev.preventDefault();
        scrubTo(ev.clientX);
      };
      const onUp = () => {
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
      };
      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
    },
    [timeRange, trackWidth, stopPlayback, xToTime, loadAtTimeDebounced],
  );

  // --- Computed values ---
  const currentX = useMemo(() => {
    if (isLive || !currentTime || !timeRange || trackWidth === 0) return trackWidth;
    return timeToX(new Date(currentTime).getTime());
  }, [isLive, currentTime, trackWidth, timeToX, timeRange]);

  const maxEventCount = useMemo(
    () => Math.max(1, ...events.map((e) => e.nodes_added + e.edges_added)),
    [events],
  );

  const tickMarks = useMemo(() => {
    if (!timeRange || timeRange.max === timeRange.min || trackWidth < 50) return [];
    const span = timeRange.max - timeRange.min;
    const targetTicks = Math.max(3, Math.floor(trackWidth / 120));
    const interval = span / targetTicks;
    const marks: { x: number; label: string }[] = [];
    for (let i = 0; i <= targetTicks; i++) {
      const ts = timeRange.min + interval * i;
      marks.push({
        x: timeToX(ts),
        label: new Date(ts).toLocaleTimeString('ru-RU', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }),
      });
    }
    return marks;
  }, [timeRange, trackWidth, timeToX]);

  const hasData = range?.min_time != null && range?.max_time != null;
  const hasEvents = events.length > 0;

  return (
    <div className="shrink-0 border-t border-slate-800/70 bg-slate-950/90">
      {/* Stats row */}
      <div className="flex h-7 items-center gap-3 px-4 text-[11px]">
        <Stat label="Nodes" value={nodes.length} />
        <div className="h-3 w-px bg-slate-800" />
        <Stat label="Edges" value={edges.length} />
        <div className="h-3 w-px bg-slate-800" />
        <Stat label="Node types" value={nodeTypes} />
        <div className="h-3 w-px bg-slate-800" />
        <Stat label="Edge types" value={edgeTypes} />
        {rangeLoading && (
          <span className="ml-1 text-[10px] text-slate-500">Loading timeline...</span>
        )}
        {isLive ? (
          <span className="ml-auto flex items-center gap-1.5 text-[10px] text-emerald-400">
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            Live
          </span>
        ) : currentTime ? (
          <span className="ml-auto font-mono text-[10px] text-slate-400">
            {new Date(currentTime).toLocaleString('ru-RU', {
              day: '2-digit',
              month: '2-digit',
              year: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })}
          </span>
        ) : null}
      </div>

      {/* Controls row */}
      <div className="flex items-center gap-1.5 px-4 pb-1">
        <CtrlBtn onClick={handleStepBackward} disabled={events.length === 0} title="Step back">
          <SvgIcon d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z M8 6v12h-2V6z" />
        </CtrlBtn>
        <CtrlBtn onClick={handlePlayPause} disabled={!hasData || !hasEvents} title={isPlaying ? 'Pause' : 'Play'}>
          {isPlaying ? (
            <SvgIcon d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
          ) : (
            <SvgIcon d="M8 5v14l11-7z" />
          )}
        </CtrlBtn>
        <CtrlBtn onClick={handleStepForward} disabled={events.length === 0} title="Step forward">
          <SvgIcon d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z M16 6v12h2V6z" />
        </CtrlBtn>

        <div className="mx-1 h-4 w-px bg-slate-800" />

        <div className="flex items-center gap-0.5 rounded-md bg-slate-900/80 p-0.5">
          {SPEED_OPTIONS.map((sp) => (
            <button
              key={sp}
              onClick={() => setPlaybackSpeed(sp)}
              className={[
                'rounded px-1.5 py-0.5 text-[9px] font-semibold transition-colors',
                playbackSpeed === sp
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-500 hover:text-slate-300',
              ].join(' ')}
            >
              {sp}x
            </button>
          ))}
        </div>

        {!isLive && (
          <button
            onClick={handleGoLive}
            className="ml-1 flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-semibold text-emerald-400 transition-colors hover:bg-slate-800"
          >
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Live
          </button>
        )}
      </div>

      {/* Track */}
      <div className="px-4 pb-2">
        {hasData && timeRange ? (
          <div
            ref={trackRef}
            className="relative h-12 cursor-crosshair select-none overflow-hidden rounded-md bg-slate-900/60"
            onMouseDown={handleTrackMouseDown}
          >
            {/* Filled area up to current time */}
            {!isLive && currentTime && currentX > 0 && (
              <div
                className="pointer-events-none absolute top-0 h-full bg-blue-500/5"
                style={{ left: 0, width: Math.min(currentX, trackWidth) }}
              />
            )}

            {/* Event bars */}
            <svg className="absolute inset-0 h-full w-full" preserveAspectRatio="none">
              {events.map((ev, i) => {
                const x = timeToX(new Date(ev.timestamp).getTime());
                if (x < -5 || x > trackWidth + 5) return null;
                const total = ev.nodes_added + ev.edges_added;
                const barMaxH = 28;
                const h = Math.max(3, (total / maxEventCount) * barMaxH);
                const barW = Math.max(4, Math.min(8, trackWidth / Math.max(events.length, 1) - 2));
                const topTypes = Object.entries(ev.node_types).sort((a, b) => b[1] - a[1]);
                const color = topTypes.length > 0 ? (NODE_TYPE_COLORS[topTypes[0][0]] ?? '#3b82f6') : '#3b82f6';
                return (
                  <rect
                    key={i}
                    x={x - barW / 2}
                    y={36 - h}
                    width={barW}
                    height={h}
                    rx={1.5}
                    fill={color}
                    opacity={0.65}
                  />
                );
              })}
            </svg>

            {/* Current time needle */}
            {!isLive && currentTime && currentX > 0 && (
              <div
                className="pointer-events-none absolute top-0 h-full w-0.5 bg-blue-400"
                style={{
                  left: Math.max(0, Math.min(trackWidth, currentX)),
                  boxShadow: '0 0 8px rgba(96,165,250,0.6)',
                  zIndex: 10,
                }}
              >
                <div className="absolute -top-0.5 left-1/2 h-3 w-3 -translate-x-1/2 rounded-full border-2 border-blue-400 bg-slate-900" />
              </div>
            )}

            {/* Live indicator at right edge */}
            {isLive && (
              <div
                className="pointer-events-none absolute top-0 h-full w-0.5 bg-emerald-400"
                style={{ left: trackWidth - 1, boxShadow: '0 0 6px rgba(52,211,153,0.5)' }}
              />
            )}

            {/* Tick marks */}
            <div className="absolute bottom-0 left-0 right-0 h-5">
              {tickMarks.map((tick, i) => (
                <span
                  key={i}
                  className="absolute text-[7px] text-slate-600"
                  style={{ left: tick.x, transform: 'translateX(-50%)' }}
                >
                  {tick.label}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex h-12 items-center justify-center rounded-md bg-slate-900/60 text-[11px] text-slate-600">
            {rangeLoading ? 'Loading timeline...' : 'Waiting for data...'}
          </div>
        )}

        {/* Date range labels */}
        {hasData && timeRange && (
          <div className="mt-0.5 flex justify-between text-[9px] text-slate-600">
            <span>
              {new Date(timeRange.min).toLocaleString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
            {hasEvents && (
              <span className="text-slate-500">
                {events.reduce((a, e) => a + e.nodes_added, 0)} nodes appeared in {events.length} events
              </span>
            )}
            <span>
              {new Date(timeRange.max).toLocaleString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>
        )}
      </div>
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

function CtrlBtn({
  onClick,
  disabled,
  title,
  children,
}: Readonly<{
  onClick: () => void;
  disabled?: boolean;
  title: string;
  children: React.ReactNode;
}>) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={[
        'flex h-6 w-6 items-center justify-center rounded-md transition-colors',
        disabled ? 'cursor-not-allowed text-slate-700' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200',
      ].join(' ')}
    >
      {children}
    </button>
  );
}

function SvgIcon({ d, size = 14 }: Readonly<{ d: string; size?: number }>) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <path d={d} />
    </svg>
  );
}
