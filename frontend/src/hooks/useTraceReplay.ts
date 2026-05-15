import { useCallback, useRef, useState } from 'react';

import { fetchLatestTraceReplay, fetchTraceReplayById, type TraceReplayHop } from '../api/timelineApi';
import { useCyContext } from '../context/CytoscapeContext';
import { useLogStore } from '../store/logStore';

const errMsg = (e: unknown, fallback: string) => (e instanceof Error ? e.message : fallback);

const MIN_HOP_DURATION_MS = 350;
const HOP_GAP_MS = 200;

export function useTraceReplay() {
  const { cyRef } = useCyContext();
  const addLog = useLogStore((s) => s.addLog);

  const [isPlaying, setIsPlaying] = useState(false);
  const [lastTraceId, setLastTraceId] = useState<string | null>(null);
  const cancelRef = useRef(false);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const stop = useCallback(() => {
    cancelRef.current = true;
    for (const t of timersRef.current) clearTimeout(t);
    timersRef.current = [];
    const cy = cyRef.current;
    if (cy && !cy.destroyed()) {
      cy.edges().removeClass('trace-replay').removeClass('trace-error');
    }
    setIsPlaying(false);
  }, [cyRef]);

  const play = useCallback(async (traceIdArg?: string) => {
    if (isPlaying) return;
    cancelRef.current = false;
    setIsPlaying(true);
    addLog('info', 'replay', traceIdArg ? `Fetching trace ${traceIdArg.slice(0, 12)}...` : 'Fetching latest trace...');

    let hops: TraceReplayHop[];
    let traceId: string | null;
    try {
      const resp = traceIdArg
        ? await fetchTraceReplayById(traceIdArg)
        : await fetchLatestTraceReplay();
      hops = resp.hops;
      traceId = resp.trace_id ?? traceIdArg ?? null;
    } catch (e) {
      addLog('error', 'replay', errMsg(e, 'Failed to fetch trace replay'));
      setIsPlaying(false);
      return;
    }

    if (!traceId || hops.length === 0) {
      addLog('warn', 'replay', 'No recent trace with cross-service hops found');
      setIsPlaying(false);
      return;
    }
    setLastTraceId(traceId);
    addLog('success', 'replay', `Replaying trace ${traceId.slice(0, 12)}... (${hops.length} hops)`);

    const cy = cyRef.current;
    if (!cy || cy.destroyed()) {
      setIsPlaying(false);
      return;
    }

    cy.edges().removeClass('trace-replay').removeClass('trace-error');

    const matchEdge = (caller: string, callee: string) => {
      const sourceId = `urn:service:${caller}`;
      const targetId = `urn:service:${callee}`;
      return cy.edges().filter((e) =>
        e.data('source') === sourceId && e.data('target') === targetId,
      );
    };

    let prevStart = 0;
    for (let i = 0; i < hops.length; i++) {
      const hop = hops[i];
      const delay = i === 0 ? 0 : Math.max(HOP_GAP_MS, hop.start_offset_ms - prevStart);
      prevStart = hop.start_offset_ms;
      const holdMs = Math.max(MIN_HOP_DURATION_MS, hop.duration_ms);

      const fireAt = i === 0 ? 0 : delay;
      timersRef.current.push(
        setTimeout(() => {
          if (cancelRef.current) return;
          const edges = matchEdge(hop.caller_service, hop.callee_service);
          if (edges.length === 0) return;
          edges.addClass('trace-replay');
          if (hop.is_error) edges.addClass('trace-error');
          timersRef.current.push(
            setTimeout(() => {
              if (cancelRef.current) return;
              edges.removeClass('trace-replay').removeClass('trace-error');
            }, holdMs),
          );
        }, fireAt + i * HOP_GAP_MS),
      );
    }

    const totalDuration =
      hops.reduce((acc, h, i) => {
        const gap = i === 0 ? 0 : Math.max(HOP_GAP_MS, h.start_offset_ms - hops[i - 1].start_offset_ms);
        return acc + gap + HOP_GAP_MS;
      }, 0) + MIN_HOP_DURATION_MS * 2;

    timersRef.current.push(
      setTimeout(() => {
        if (!cancelRef.current) setIsPlaying(false);
      }, totalDuration),
    );
  }, [isPlaying, cyRef, addLog]);

  return { play, stop, isPlaying, lastTraceId };
}
