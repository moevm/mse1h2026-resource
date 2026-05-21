import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useTimelineStore, type PlaybackSpeed } from '../../features/graph/store';
import { useGraphDataStore, useGraphUiStore } from '../../features/graph/store';
import { useGraph } from '../../hooks/useGraph';
import { useCyContext } from '../../context/CytoscapeContext';

const REFRESH_RANGE_MS = 30_000;
const REFRESH_EVENTS_MS = 15_000;

const SPEED_OPTIONS: PlaybackSpeed[] = [1, 2, 5, 10];

interface Slot {
  index: number;
  startMs: number;
  endMs: number;
  count: number;
  nodesAdded: number;
  edgesAdded: number;
  spanCount: number;
  errorCount: number;
  topType: string | null;
  events: { timestamp: string; nodes: number; edges: number }[];
}

/**
 * Rolling-window timeline. The view is a fixed-length strip of N slots
 * (configurable). Each slot represents `chunkBucketSeconds` of real time.
 * The right edge tracks "now"; as time advances, the oldest slot falls off
 * the left. Events are mapped into slot indexes purely by their timestamp,
 * so layout is deterministic and never reflows when new data arrives.
 *
 * Clicking or dragging snaps to slot boundaries. Arrow keys step between
 * slots that contain at least one event; Space toggles playback.
 */
export function TimelineBar({ limit = 500 }: Readonly<{ limit?: number }>) {
  const nodes = useGraphDataStore((s) => s.nodes);
  const edges = useGraphDataStore((s) => s.edges);
  const selectedAppId = useGraphUiStore((s) => s.selectedAppId);
  const { loadFullGraph } = useGraph();
  const { fitGraph } = useCyContext();

  const events = useTimelineStore((s) => s.events);
  const activity = useTimelineStore((s) => s.activity);
  const setMode = useTimelineStore((s) => s.setMode);
  const currentTime = useTimelineStore((s) => s.currentTime);
  const isPlaying = useTimelineStore((s) => s.isPlaying);
  const playbackSpeed = useTimelineStore((s) => s.playbackSpeed);
  const eventsLoading = useTimelineStore((s) => s.eventsLoading);
  const fetchRange = useTimelineStore((s) => s.fetchRange);
  const fetchEvents = useTimelineStore((s) => s.fetchEvents);
  const goLive = useTimelineStore((s) => s.goLive);
  const setPlaybackSpeed = useTimelineStore((s) => s.setPlaybackSpeed);
  const chunkCount = useTimelineStore((s) => s.chunkCount);
  const chunkBucketSeconds = useTimelineStore((s) => s.chunkBucketSeconds);
  const windowStart = useTimelineStore((s) => s.windowStart);
  const setChunkCount = useTimelineStore((s) => s.setChunkCount);
  const setChunkBucketSeconds = useTimelineStore((s) => s.setChunkBucketSeconds);

  const stripRef = useRef<HTMLDivElement>(null);
  const playbackRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [stripWidth, setStripWidth] = useState(0);
  const [chunkCountInput, setChunkCountInput] = useState(String(chunkCount));
  const [bucketInput, setBucketInput] = useState(String(chunkBucketSeconds));

  // Sync input fields when the store changes (e.g., reset).
  useEffect(() => setChunkCountInput(String(chunkCount)), [chunkCount]);
  useEffect(() => setBucketInput(String(chunkBucketSeconds)), [chunkBucketSeconds]);

  // Initial + periodic fetch. fetchEvents re-anchors windowEnd to "now".
  useEffect(() => {
    void fetchRange();
    const id = setInterval(() => void fetchRange(), REFRESH_RANGE_MS);
    return () => clearInterval(id);
  }, [fetchRange]);

  useEffect(() => {
    setMode('activity');
  }, [setMode]);

  useEffect(() => {
    void fetchEvents();
    const id = setInterval(() => void fetchEvents(), REFRESH_EVENTS_MS);
    return () => clearInterval(id);
  }, [fetchEvents, chunkCount, chunkBucketSeconds]);

  // Track strip width for cursor positioning.
  useEffect(() => {
    const el = stripRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      for (const entry of entries) setStripWidth(entry.contentRect.width);
    });
    obs.observe(el);
    setStripWidth(el.clientWidth);
    return () => obs.disconnect();
  }, []);

  // --- Slot derivation ---
  // Window is left-anchored: windowStart comes from the store (bucket-aligned
  // to the oldest visible event). windowEnd is derived. The first event ever
  // received lands at slot 0; later events fill slots to the right.
  const bucketMs = chunkBucketSeconds * 1000;
  const windowEnd = windowStart + chunkCount * bucketMs;

  const slots = useMemo<Slot[]>(() => {
    const out: Slot[] = Array.from({ length: chunkCount }, (_, i) => ({
      index: i,
      startMs: windowStart + i * bucketMs,
      endMs: windowStart + (i + 1) * bucketMs,
      count: 0,
      nodesAdded: 0,
      edgesAdded: 0,
      spanCount: 0,
      errorCount: 0,
      topType: null,
      events: [],
    }));

    for (const b of activity) {
      const ts = b.bucket_ts;
      if (ts < windowStart || ts >= windowEnd) continue;
      const idx = Math.min(chunkCount - 1, Math.floor((ts - windowStart) / bucketMs));
      const slot = out[idx];
      slot.spanCount += b.span_count;
      slot.errorCount += b.error_count;
      slot.count += b.span_count;
      slot.events.push({
        timestamp: b.timestamp,
        nodes: 0,
        edges: 0,
      });
    }
    for (const ev of events) {
      const ts = new Date(ev.timestamp).getTime();
      if (ts < windowStart || ts >= windowEnd) continue;
      const idx = Math.min(chunkCount - 1, Math.floor((ts - windowStart) / bucketMs));
      const slot = out[idx];
      slot.nodesAdded += ev.nodes_added;
      slot.edgesAdded += ev.edges_added;
      slot.count += ev.nodes_added + ev.edges_added;
      slot.events.push({
        timestamp: ev.timestamp,
        nodes: ev.nodes_added,
        edges: ev.edges_added,
      });
    }
    return out;
  }, [events, activity, chunkCount, bucketMs, windowStart, windowEnd]);

  const maxSlotCount = useMemo(
    () => Math.max(1, ...slots.map((s) => s.count)),
    [slots],
  );

  const nonEmptySlots = useMemo(
    () => slots.filter((s) => s.count > 0),
    [slots],
  );

  // Map a time-of-cursor to a slot index. -1 means out of window.
  const tsToSlotIdx = useCallback(
    (ts: number): number => {
      if (ts < windowStart || ts >= windowEnd) return -1;
      return Math.min(chunkCount - 1, Math.floor((ts - windowStart) / bucketMs));
    },
    [windowStart, windowEnd, chunkCount, bucketMs],
  );

  const slotWidth = stripWidth / chunkCount;

  // --- Stats ---
  const nodeTypes = useMemo(() => new Set(nodes.map((n) => n.type)).size, [nodes]);
  const edgeTypes = useMemo(() => new Set(edges.map((e) => e.type)).size, [edges]);
  const windowTotal = useMemo(
    () => slots.reduce((a, s) => a + s.count, 0),
    [slots],
  );
  const isLive = currentTime === null;

  // --- Graph loading ---
  const loadAtSlot = useCallback(
    (slot: Slot) => {
      const now = Date.now();
      const asOfMs = Math.min(Math.max(slot.endMs - 1, slot.startMs), now);
      const iso = new Date(asOfMs).toISOString();
      useTimelineStore.setState({ currentTime: iso });
      const win = {
        start: new Date(slot.startMs).toISOString(),
        end: new Date(Math.min(slot.endMs, now)).toISOString(),
      };
      void loadFullGraph(limit, selectedAppId ?? undefined, iso, win).then(() => {
        try { fitGraph(); } catch { /* cy not ready */ }
      }).catch(() => {});
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
    if (nonEmptySlots.length === 0) return;

    const ct = useTimelineStore.getState().currentTime;
    const startIdx = ct
      ? Math.max(0, nonEmptySlots.findIndex((s) => s.events.some((e) => e.timestamp >= ct)))
      : 0;
    let cursor = startIdx;

    const speed = useTimelineStore.getState().playbackSpeed;
    const intervals: Record<PlaybackSpeed, number> = { 1: 1500, 2: 800, 5: 400, 10: 250 };
    useTimelineStore.setState({ isPlaying: true });

    playbackRef.current = setInterval(() => {
      if (cursor >= nonEmptySlots.length) {
        stopPlayback();
        return;
      }
      loadAtSlot(nonEmptySlots[cursor]);
      cursor += 1;
    }, intervals[speed]);
  }, [stopPlayback, nonEmptySlots, loadAtSlot]);

  useEffect(() => () => {
    if (playbackRef.current) clearInterval(playbackRef.current);
  }, []);

  const handlePlayPause = useCallback(() => {
    if (isPlaying) stopPlayback();
    else startPlayback();
  }, [isPlaying, startPlayback, stopPlayback]);

  const handleGoLive = useCallback(() => {
    stopPlayback();
    goLive();
    const win = {
      start: new Date(windowStart).toISOString(),
      end: new Date(windowEnd).toISOString(),
    };
    void loadFullGraph(limit, selectedAppId ?? undefined, undefined, win).then(() => {
      try { fitGraph(); } catch { /* cy not ready */ }
    }).catch(() => {});
  }, [stopPlayback, goLive, limit, selectedAppId, loadFullGraph, fitGraph, windowStart, windowEnd]);

  const handleStep = useCallback(
    (dir: 1 | -1) => {
      stopPlayback();
      if (nonEmptySlots.length === 0) return;
      const ct = useTimelineStore.getState().currentTime;
      const ctMs = ct ? new Date(ct).getTime() : Number.POSITIVE_INFINITY;

      // Locate the non-empty slot that currently holds ctMs. A slot owns
      // [startMs, endMs); if ctMs is past every slot (e.g. Live), curIdx
      // stays -1 and we fall back to the nearest neighbour by position.
      const curIdx = nonEmptySlots.findIndex(
        (s) => s.startMs <= ctMs && ctMs < s.endMs,
      );

      if (dir > 0) {
        if (curIdx >= 0 && curIdx < nonEmptySlots.length - 1) {
          loadAtSlot(nonEmptySlots[curIdx + 1]);
        } else if (curIdx === -1) {
          // ctMs precedes everything → first non-empty slot.
          const first = nonEmptySlots.find((s) => s.startMs > ctMs);
          if (first) loadAtSlot(first);
        }
        // curIdx === last: already at rightmost, do nothing.
      } else {
        if (curIdx > 0) {
          loadAtSlot(nonEmptySlots[curIdx - 1]);
        } else if (curIdx === -1) {
          // ctMs is past the last slot (or Live) → jump to the latest one.
          const prev = [...nonEmptySlots].reverse().find((s) => s.endMs <= ctMs);
          if (prev) loadAtSlot(prev);
          else loadAtSlot(nonEmptySlots[nonEmptySlots.length - 1]);
        }
        // curIdx === 0: already at oldest, do nothing.
      }
    },
    [nonEmptySlots, stopPlayback, loadAtSlot],
  );

  // --- Click / drag scrubbing (snaps to slot) ---
  const handleStripMouseDown = useCallback(
    (e: React.MouseEvent) => {
      const el = stripRef.current;
      if (!el || slotWidth === 0) return;
      const rect = el.getBoundingClientRect();
      stopPlayback();

      let lastSlotIdx = -1;
      const scrubTo = (clientX: number) => {
        const nx = Math.max(0, Math.min(el.clientWidth - 1, clientX - rect.left));
        const idx = Math.min(chunkCount - 1, Math.floor(nx / slotWidth));
        if (idx === lastSlotIdx) return;
        lastSlotIdx = idx;
        const slot = slots[idx];
        // Only snap to slots that actually have data; skip empty.
        if (slot.count === 0) return;
        loadAtSlot(slot);
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
    [stopPlayback, slots, chunkCount, slotWidth, loadAtSlot],
  );

  // --- Keyboard navigation ---
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      const t = ev.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      if (ev.key === 'ArrowLeft') { ev.preventDefault(); handleStep(-1); }
      else if (ev.key === 'ArrowRight') { ev.preventDefault(); handleStep(1); }
      else if (ev.key === 'Home') {
        ev.preventDefault();
        stopPlayback();
        if (nonEmptySlots.length > 0) loadAtSlot(nonEmptySlots[0]);
      }
      else if (ev.key === 'End') { ev.preventDefault(); handleGoLive(); }
      else if (ev.key === ' ') { ev.preventDefault(); handlePlayPause(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [handleStep, handleGoLive, handlePlayPause, stopPlayback, loadAtSlot, nonEmptySlots]);

  // --- Cursor position ---
  const currentSlotIdx = useMemo(() => {
    if (isLive || !currentTime) return -1;
    return tsToSlotIdx(new Date(currentTime).getTime());
  }, [isLive, currentTime, tsToSlotIdx]);

  const formatTimeShort = (ms: number) =>
    new Date(ms).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });

  const commitChunkCount = () => {
    const n = parseInt(chunkCountInput, 10);
    if (Number.isFinite(n) && n >= 2 && n <= 120) setChunkCount(n);
    else setChunkCountInput(String(chunkCount));
  };
  const commitBucket = () => {
    const n = parseInt(bucketInput, 10);
    if (Number.isFinite(n) && n >= 10 && n <= 3600) setChunkBucketSeconds(n);
    else setBucketInput(String(chunkBucketSeconds));
  };

  return (
    <div className="shrink-0 overflow-hidden border-t border-slate-800/70 bg-slate-950/95">
      {/* Top row: stats + window summary */}
      <div className="flex h-6 items-center gap-3 px-4 pt-0.5 text-[11px]">
        <Stat label="Nodes" value={nodes.length} />
        <Sep />
        <Stat label="Edges" value={edges.length} />
        <Sep />
        <Stat label="Node types" value={nodeTypes} />
        <Sep />
        <Stat label="Edge types" value={edgeTypes} />
        <Sep />
        {currentSlotIdx >= 0 && slots[currentSlotIdx] ? (
          <span className="text-slate-500 flex items-center gap-2">
            <span className="font-mono text-slate-400">
              {formatTimeShort(slots[currentSlotIdx].startMs)}–{formatTimeShort(slots[currentSlotIdx].endMs)}
            </span>
            <span className="text-slate-300">{slots[currentSlotIdx].spanCount} spans</span>
            <span
              className={
                slots[currentSlotIdx].errorCount > 0 ? 'text-red-400' : 'text-slate-500'
              }
            >
              {slots[currentSlotIdx].errorCount} err
            </span>
            {slots[currentSlotIdx].spanCount > 0 && (
              <span className="text-slate-500">
                {((slots[currentSlotIdx].errorCount / slots[currentSlotIdx].spanCount) * 100).toFixed(1)}%
              </span>
            )}
          </span>
        ) : (
          <span className="text-slate-500">
            Window: <span className="font-mono text-slate-300">{chunkCount}×{chunkBucketSeconds}s</span>
            <span className="ml-1 text-slate-600">({windowTotal} spans)</span>
          </span>
        )}
        {eventsLoading && (
          <span className="text-[10px] text-slate-500">Loading...</span>
        )}
        {isLive ? (
          <span className="ml-auto flex items-center gap-1.5 text-[10px] text-slate-400" title="Showing all known nodes/edges, ignoring time snapshot">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-slate-500" />
            Full topology
          </span>
        ) : currentTime ? (
          <span className="ml-auto font-mono text-[10px] text-slate-400">
            {new Date(currentTime).toLocaleString('ru-RU', {
              day: '2-digit', month: '2-digit', year: '2-digit',
              hour: '2-digit', minute: '2-digit', second: '2-digit',
            })}
          </span>
        ) : null}
      </div>

      <div className="flex items-center gap-1.5 px-4 pb-0.5">
        <CtrlBtn onClick={() => handleStep(-1)} disabled={nonEmptySlots.length === 0} title="Step back (←)">
          <SvgIcon d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z M8 6v12h-2V6z" />
        </CtrlBtn>
        <CtrlBtn onClick={handlePlayPause} disabled={nonEmptySlots.length === 0} title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}>
          {isPlaying ? (
            <SvgIcon d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
          ) : (
            <SvgIcon d="M8 5v14l11-7z" />
          )}
        </CtrlBtn>
        <CtrlBtn onClick={() => handleStep(1)} disabled={nonEmptySlots.length === 0} title="Step forward (→)">
          <SvgIcon d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z M16 6v12h2V6z" />
        </CtrlBtn>

        <Sep />

        <div className="flex items-center gap-0.5 rounded-md bg-slate-900/80 p-0.5">
          {SPEED_OPTIONS.map((sp) => (
            <button
              key={sp}
              onClick={() => setPlaybackSpeed(sp)}
              className={[
                'rounded px-1.5 py-0.5 text-[9px] font-semibold transition-colors',
                playbackSpeed === sp ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-slate-300',
              ].join(' ')}
            >
              {sp}x
            </button>
          ))}
        </div>


        <Sep />

        <label className="flex items-center gap-1 text-[10px] text-slate-500">
          buckets
          <input
            type="number"
            min={2}
            max={120}
            value={chunkCountInput}
            onChange={(e) => setChunkCountInput(e.target.value)}
            onBlur={commitChunkCount}
            onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }}
            className="w-12 rounded bg-slate-900/80 px-1 py-0.5 text-center font-mono text-[10px] text-slate-200 outline-none focus:ring-1 focus:ring-blue-500"
          />
        </label>
        <label className="flex items-center gap-1 text-[10px] text-slate-500">
          seconds in bucket
          <input
            type="number"
            min={10}
            max={3600}
            value={bucketInput}
            onChange={(e) => setBucketInput(e.target.value)}
            onBlur={commitBucket}
            onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }}
            className="w-14 rounded bg-slate-900/80 px-1 py-0.5 text-center font-mono text-[10px] text-slate-200 outline-none focus:ring-1 focus:ring-blue-500"
          />
        </label>

      </div>

      <div className="px-4 pb-0.5">
        <div
          ref={stripRef}
          className="relative h-9 cursor-pointer select-none overflow-hidden rounded-md bg-slate-900/60"
          onMouseDown={handleStripMouseDown}
          title="Click or drag a chunk to jump. ← → step, Home first, Space play."
        >
          <svg className="absolute inset-0 h-full w-full" preserveAspectRatio="none">
            {Array.from({ length: chunkCount + 1 }).map((_, i) => (
              <line
                key={i}
                x1={i * slotWidth}
                x2={i * slotWidth}
                y1={0}
                y2={36}
                stroke="#1e293b"
                strokeWidth={1}
                opacity={i % 5 === 0 ? 0.9 : 0.35}
              />
            ))}

            {slots.map((slot) => {
              const x = slot.index * slotWidth;
              const barW = Math.max(2, slotWidth - 3);
              const barMaxH = 22;
              const barBaseY = 25;
              const h = slot.count > 0 ? Math.max(3, (slot.count / maxSlotCount) * barMaxH) : 0;
              const errRate = slot.spanCount > 0 ? slot.errorCount / slot.spanCount : 0;
              const color =
                errRate > 0.05 ? '#ef4444' : errRate > 0.01 ? '#f59e0b' : '#3b82f6';
              const isActive = slot.index === currentSlotIdx;
              const hasData = slot.count > 0;
              return (
                <g key={slot.index}>
                  <rect
                    x={x}
                    y={0}
                    width={slotWidth}
                    height={36}
                    fill={isActive ? 'rgba(96,165,250,0.08)' : 'transparent'}
                  />
                  {hasData && (
                    <rect
                      x={x + (slotWidth - barW) / 2}
                      y={barBaseY - h}
                      width={barW}
                      height={h}
                      rx={1.5}
                      fill={color}
                      opacity={isActive ? 1 : 0.75}
                      stroke={isActive ? '#60a5fa' : 'none'}
                      strokeWidth={isActive ? 1.5 : 0}
                    />
                  )}
                </g>
              );
            })}
          </svg>

          {isLive && (
            <div
              className="pointer-events-none absolute top-0 h-full w-0.5 bg-slate-500/60"
              style={{ left: stripWidth - 1 }}
            />
          )}

          <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-3 overflow-hidden">
            {Array.from({ length: chunkCount + 1 }).map((_, i) => {
              if (i !== 0 && i !== chunkCount && i % 5 !== 0) return null;
              const ts = windowStart + i * bucketMs;
              const isFirst = i === 0;
              const isLast = i === chunkCount;
              const transform = isFirst
                ? 'translateX(0)'
                : isLast
                  ? 'translateX(-100%)'
                  : 'translateX(-50%)';
              return (
                <span
                  key={i}
                  className="absolute font-mono text-[8px] leading-3 text-slate-500"
                  style={{ left: i * slotWidth, transform }}
                >
                  {formatTimeShort(ts)}
                </span>
              );
            })}
          </div>
        </div>

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

function Sep() {
  return <div className="h-3 w-px bg-slate-800" />;
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
