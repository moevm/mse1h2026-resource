import { useCallback } from 'react';

import {
  fetchAnalytics,
  fetchFullGraph,
  fetchHealth,
  fetchImpact,
  fetchLayout,
  fetchShortestPath,
  fetchStats,
  fetchSubgraph,
} from '../api';
import { useGraphDataStore, useGraphFilterStore, useGraphUiStore } from '../features/graph/store';
import { useLogStore } from '../store/logStore';
import type { ImpactRequest, PathRequest, SubgraphRequest } from '../types';

export function useGraph() {
  const setGraph = useGraphDataStore((s) => s.setGraph);
  const setStats = useGraphDataStore((s) => s.setStats);
  const setAnalytics = useGraphDataStore((s) => s.setAnalytics);
  const addQueryHistory = useGraphDataStore((s) => s.addQueryHistory);
  const setLastRefreshed = useGraphDataStore((s) => s.setLastRefreshed);
  const setLoading = useGraphUiStore((s) => s.setLoading);
  const setError = useGraphUiStore((s) => s.setError);
  const setBackendStatus = useGraphUiStore((s) => s.setBackendStatus);
  const clearVisualFocus = useGraphUiStore((s) => s.clearVisualFocus);
  const setHiddenNodeTypes = useGraphFilterStore((s) => s.setHiddenNodeTypes);
  const setHiddenEdgeTypes = useGraphFilterStore((s) => s.setHiddenEdgeTypes);

  const { addLog } = useLogStore();

  const errMsg = (e: unknown, fallback: string) => (e instanceof Error ? e.message : fallback);

  const syncFilters = useCallback(() => {
    setHiddenNodeTypes([]);
    setHiddenEdgeTypes([]);
  }, [setHiddenNodeTypes, setHiddenEdgeTypes]);

  const checkHealth = useCallback(async () => {
    setBackendStatus('checking');
    try {
      const res = await fetchHealth();
      setBackendStatus(res.status === 'ok' ? 'connected' : 'disconnected');
      addLog('success', 'health', `Backend status: ${res.status}`);
    } catch (e: unknown) {
      setBackendStatus('disconnected');
      addLog('error', 'health', `Backend unreachable: ${errMsg(e, 'Connection failed')}`);
    }
  }, [setBackendStatus, addLog]);

  const loadFullGraph = useCallback(
    async (
      limit = 500,
      appId?: string,
      asOf?: string,
      window?: { start: string; end: string },
    ) => {
      setLoading(true);
      const appInfo = appId ? ` (app=${appId.slice(0, 8)}...)` : '';
      const timeInfo = asOf ? ` as_of=${asOf}` : '';
      const winInfo = window ? ` window=[${window.start.slice(11, 19)}..${window.end.slice(11, 19)}]` : '';
      addLog('info', 'graph', `Loading full graph (limit=${limit}${appInfo}${timeInfo}${winInfo})...`);
      try {
        const res = await fetchFullGraph(limit, {
          appId,
          asOf,
          windowStart: window?.start,
          windowEnd: window?.end,
        });
        setGraph(res.nodes, res.edges);
        clearVisualFocus();
        syncFilters();
        setLastRefreshed();
        addQueryHistory({
          type: 'full',
          params: { limit, app_id: appId },
          nodeCount: res.node_count,
          edgeCount: res.edge_count,
        });
        addLog('success', 'graph', `Full graph loaded: ${res.node_count} nodes, ${res.edge_count} edges`, {
          node_count: res.node_count,
          edge_count: res.edge_count,
        });
      } catch (e: unknown) {
        const msg = errMsg(e, 'Failed to load graph');
        setError(msg);
        addLog('error', 'graph', msg);
      } finally {
        setLoading(false);
      }
    },
    [setGraph, setLoading, setError, syncFilters, addLog, addQueryHistory, setLastRefreshed, clearVisualFocus],
  );

  const loadLayout = useCallback(
    async (limit = 500, layout = 'spring') => {
      setLoading(true);
      addLog('info', 'graph', `Loading layout '${layout}' (limit=${limit})...`);
      try {
        const res = await fetchLayout(limit, layout);
        setGraph(res.nodes, res.edges);
        clearVisualFocus();
        syncFilters();
        setLastRefreshed();
        addQueryHistory({
          type: 'layout',
          params: { limit, layout },
          nodeCount: res.node_count,
          edgeCount: res.edge_count,
        });
        addLog('success', 'graph', `Layout '${layout}' loaded: ${res.node_count} nodes, ${res.edge_count} edges`);
      } catch (e: unknown) {
        const msg = errMsg(e, 'Failed to load layout');
        setError(msg);
        addLog('error', 'graph', msg);
      } finally {
        setLoading(false);
      }
    },
    [setGraph, setLoading, setError, syncFilters, addLog, addQueryHistory, setLastRefreshed, clearVisualFocus],
  );

  const loadSubgraph = useCallback(
    async (req: SubgraphRequest) => {
      setLoading(true);
      addLog('info', 'graph', `Loading subgraph around '${req.center_node_id}' (depth=${req.depth})...`);
      try {
        const res = await fetchSubgraph(req);
        setGraph(res.nodes, res.edges);
        clearVisualFocus();
        syncFilters();
        setLastRefreshed();
        addQueryHistory({
          type: 'subgraph',
          params: { ...req },
          nodeCount: res.node_count,
          edgeCount: res.edge_count,
        });
        addLog('success', 'graph', `Subgraph loaded: ${res.node_count} nodes, ${res.edge_count} edges`, {
          center: req.center_node_id,
          depth: req.depth,
        });
      } catch (e: unknown) {
        const msg = errMsg(e, 'Failed to load subgraph');
        setError(msg);
        addLog('error', 'graph', msg);
      } finally {
        setLoading(false);
      }
    },
    [setGraph, setLoading, setError, syncFilters, addLog, addQueryHistory, setLastRefreshed, clearVisualFocus],
  );

  const loadShortestPath = useCallback(
    async (req: PathRequest) => {
      setLoading(true);
      addLog('info', 'graph', `Finding path: ${req.source_id} -> ${req.target_id}...`);
      try {
        const res = await fetchShortestPath(req);
        setGraph(res.nodes, res.edges);
        clearVisualFocus();
        syncFilters();
        setLastRefreshed();
        addQueryHistory({
          type: 'path',
          params: { ...req },
          nodeCount: res.node_count,
          edgeCount: res.edge_count,
        });
        addLog('success', 'graph', `Path found: ${res.node_count} nodes, ${res.edge_count} edges`, {
          source: req.source_id,
          target: req.target_id,
        });
      } catch (e: unknown) {
        const msg = errMsg(e, 'Failed to find path');
        setError(msg);
        addLog('error', 'graph', msg);
      } finally {
        setLoading(false);
      }
    },
    [setGraph, setLoading, setError, syncFilters, addLog, addQueryHistory, setLastRefreshed, clearVisualFocus],
  );

  const loadImpact = useCallback(
    async (req: ImpactRequest) => {
      setLoading(true);
      addLog(
        'info',
        'graph',
        `Impact analysis: ${req.node_id} (${req.direction ?? 'downstream'}, depth=${req.depth ?? 3})...`,
      );
      try {
        const res = await fetchImpact(req);
        setGraph(res.nodes, res.edges);
        clearVisualFocus();
        syncFilters();
        setLastRefreshed();
        addQueryHistory({
          type: 'impact',
          params: { ...req },
          nodeCount: res.node_count,
          edgeCount: res.edge_count,
        });
        addLog('success', 'graph', `Impact analysis: ${res.node_count} affected nodes, ${res.edge_count} edges`, {
          node_id: req.node_id,
          direction: req.direction,
        });
      } catch (e: unknown) {
        const msg = errMsg(e, 'Failed to load impact');
        setError(msg);
        addLog('error', 'graph', msg);
      } finally {
        setLoading(false);
      }
    },
    [setGraph, setLoading, setError, syncFilters, addLog, addQueryHistory, setLastRefreshed, clearVisualFocus],
  );

  const loadStats = useCallback(async () => {
    try {
      const res = await fetchStats();
      setStats(res);
      addLog('info', 'stats', `Stats loaded: ${res.total_nodes} nodes, ${res.total_edges} edges`);
    } catch (e: unknown) {
      const msg = errMsg(e, 'Failed to load stats');
      setError(msg);
      addLog('error', 'stats', msg);
    }
  }, [setStats, setError, addLog]);

  const loadAnalytics = useCallback(
    async (limit = 1000) => {
      addLog('info', 'analytics', `Computing analytics (limit=${limit})...`);
      try {
        const res = await fetchAnalytics(limit);
        setAnalytics(res);
        addLog(
          'success',
          'analytics',
          `Analytics computed: ${Object.keys(res.pagerank).length} nodes, ${res.communities.length} communities`,
        );
      } catch (e: unknown) {
        const msg = errMsg(e, 'Failed to load analytics');
        setError(msg);
        addLog('error', 'analytics', msg);
      }
    },
    [setAnalytics, setError, addLog],
  );

  return {
    checkHealth,
    loadFullGraph,
    loadLayout,
    loadSubgraph,
    loadShortestPath,
    loadImpact,
    loadStats,
    loadAnalytics,
  };
}
