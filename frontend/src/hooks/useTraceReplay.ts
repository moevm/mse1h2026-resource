import { useCallback, useRef, useState } from 'react';

import { fetchLatestTraceReplay, fetchTraceReplayById, type TraceReplayHop } from '../api/timelineApi';
import { useCyContext } from '../context/CytoscapeContext';
import { useLogStore } from '../store/logStore';

const errMsg = (e: unknown, fallback: string) => (e instanceof Error ? e.message : fallback);

const STEP_MS = 700;
const HOLD_AFTER_END_MS = 1500;
const PULSE_FADE_MS = 600;

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
      cy.edges()
        .removeClass('trace-replay')
        .removeClass('trace-replay-head')
        .removeClass('trace-error');
      cy.nodes()
        .removeClass('trace-replay-node')
        .removeClass('trace-replay-head-node');
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

    const cy = cyRef.current;
    if (!cy || cy.destroyed()) {
      setIsPlaying(false);
      return;
    }

    cy.edges()
      .removeClass('trace-replay')
      .removeClass('trace-replay-head')
      .removeClass('trace-error');
    cy.nodes()
      .removeClass('trace-replay-node')
      .removeClass('trace-replay-head-node');

    const calleePrefix: Record<string, string> = {
      Service: 'urn:service:',
      Endpoint: 'urn:endpoint:',
      Database: 'urn:database:',
      Table: 'urn:table:',
      Cache: 'urn:cache:',
      QueueTopic: 'urn:queuetopic:',
      ExternalAPI: 'urn:externalapi:',
    };

    const matchEdgeAndNodes = (caller: string, callee: string, calleeKind: string | undefined) => {
      const sourceId = `urn:service:${caller}`;
      const prefix = calleePrefix[calleeKind ?? 'Service'] ?? 'urn:service:';
      const targetId = `${prefix}${callee}`;

      if (calleeKind === 'Endpoint') {
        const endpointNode = cy.getElementById(targetId);
        if (endpointNode.length > 0) {
          const incident = endpointNode.connectedEdges();
          if (incident.length > 0) {
            return { edges: incident, nodes: incident.connectedNodes().union(endpointNode) };
          }
          return { edges: cy.collection(), nodes: endpointNode };
        }
        return { edges: cy.collection(), nodes: cy.collection() };
      }

      const direct = cy.edges().filter((e) =>
        e.data('source') === sourceId && e.data('target') === targetId,
      );
      if (direct.length > 0) {
        return { edges: direct, nodes: direct.connectedNodes() };
      }
      const reverse = cy.edges().filter((e) =>
        e.data('source') === targetId && e.data('target') === sourceId,
      );
      if (reverse.length > 0) {
        return { edges: reverse, nodes: reverse.connectedNodes() };
      }

      const targetNode = cy.getElementById(targetId);
      if (targetNode.length > 0) {
        return { edges: cy.collection(), nodes: targetNode };
      }
      const byLabel = cy.nodes().filter((n) => n.data('label') === callee);
      return { edges: cy.collection(), nodes: byLabel };
    };

    // Backend already returns hops in DFS-with-Endpoint-last order — don't re-sort.
    const ordered = hops;

    addLog('success', 'replay', `Replaying trace ${traceId.slice(0, 12)}... (${ordered.length} hops)`);

    let prevHeadEdges: cytoscape.EdgeCollection | null = null;
    let prevHeadNodes: cytoscape.NodeCollection | null = null;

    ordered.forEach((hop, i) => {
      timersRef.current.push(
        setTimeout(() => {
          if (cancelRef.current) return;
          const { edges, nodes } = matchEdgeAndNodes(
            hop.caller_service, hop.callee_service, hop.callee_kind,
          );
          if (edges.length === 0 && nodes.length === 0) {
            addLog('warn', 'replay', `Hop not found in graph: ${hop.caller_service} → ${hop.callee_service} (${hop.callee_kind ?? 'Service'})`);
            return;
          }
          if (prevHeadEdges) prevHeadEdges.removeClass('trace-replay-head');
          if (prevHeadNodes) prevHeadNodes.removeClass('trace-replay-head-node');
          if (edges.length > 0) {
            edges.addClass('trace-replay');
            edges.addClass('trace-replay-head');
            if (hop.is_error) edges.addClass('trace-error');
          }
          if (nodes.length > 0) {
            nodes.addClass('trace-replay-node');
            nodes.addClass('trace-replay-head-node');
          }
          prevHeadEdges = edges;
          prevHeadNodes = nodes;
        }, i * STEP_MS),
      );
    });

    const totalShowMs = ordered.length * STEP_MS + HOLD_AFTER_END_MS;

    timersRef.current.push(
      setTimeout(() => {
        if (cancelRef.current) return;
        const c = cyRef.current;
        if (c && !c.destroyed()) {
          c.edges().removeClass('trace-replay-head');
          c.nodes().removeClass('trace-replay-head-node');
        }
      }, totalShowMs - PULSE_FADE_MS),
    );

    timersRef.current.push(
      setTimeout(() => {
        if (cancelRef.current) return;
        const c = cyRef.current;
        if (c && !c.destroyed()) {
          c.edges()
            .removeClass('trace-replay')
            .removeClass('trace-replay-head')
            .removeClass('trace-error');
          c.nodes()
            .removeClass('trace-replay-node')
            .removeClass('trace-replay-head-node');
        }
        setIsPlaying(false);
      }, totalShowMs),
    );
  }, [isPlaying, cyRef, addLog]);

  return { play, stop, isPlaying, lastTraceId };
}
