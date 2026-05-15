import { useCallback, useEffect, useRef, useState } from 'react';

import { CytoscapeProvider } from '../../context/CytoscapeContext';
import { useGraphDataStore, useGraphFilterStore, useGraphUiStore, useTimelineStore } from '../../features/graph/store';
import { useApplications } from '../../hooks/useApplications';
import { useGraph } from '../../hooks/useGraph';
import { useLogStore } from '../../store/logStore';
import type { GraphResponse } from '../../types';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { GraphCanvas } from '../graph/GraphCanvas';
import { GraphControls } from '../graph/GraphControls';
import { HotEdgesPanel } from '../graph/HotEdgesPanel';
import { TimelineBar } from '../graph/TimelineBar';
import { NodeDetail } from '../graph/NodeDetail';
import { IconPanel, IconRefresh, IconSearch, IconX } from '../icons';
import { AppLayout } from '../layout/AppLayout';
import ExportPanel from '../panels/ExportPanel';
import { FilterPanel } from '../panels/FilterPanel';
import GraphInsightsPanel from '../panels/GraphInsightsPanel';
import { LogPanel } from '../panels/LogPanel';
import { QueryPanel } from '../panels/QueryPanel';
import { TracesPanel } from '../panels/TracesPanel';
import TraversalPanel from '../panels/TraversalPanel';

type RightPanel = 'detail' | 'filter' | 'query' | 'insights' | 'export' | 'traversal' | 'traces' | 'log';

const PANEL_CONFIG: Array<{ id: RightPanel; label: string; shortLabel: string }> = [
  { id: 'detail', label: 'Node Detail', shortLabel: 'Detail' },
  { id: 'filter', label: 'Filter', shortLabel: 'Filter' },
  { id: 'query', label: 'Query', shortLabel: 'Query' },
  { id: 'insights', label: 'Insights', shortLabel: 'Insights' },
  { id: 'traversal', label: 'Traversal', shortLabel: 'Traverse' },
  { id: 'traces', label: 'Traces', shortLabel: 'Traces' },
  { id: 'export', label: 'Export', shortLabel: 'Export' },
  { id: 'log', label: 'Activity Log', shortLabel: 'Log' },
];

export function GraphPage() {
  const { loadFullGraph, checkHealth } = useGraph();
  const { applications } = useApplications();
  const searchQuery = useGraphFilterStore((s) => s.searchQuery);
  const setSearchQuery = useGraphFilterStore((s) => s.setSearchQuery);
  const selectedAppId = useGraphUiStore((s) => s.selectedAppId);
  const setSelectedAppId = useGraphUiStore((s) => s.setSelectedAppId);
  const error = useGraphUiStore((s) => s.error);
  const lastRefreshedAt = useGraphDataStore((s) => s.lastRefreshedAt);
  const logCount = useLogStore((s) => s.entries.length);

  const [rightPanel, setRightPanel] = useState<RightPanel>('detail');
  const limitInput = 500;
  const [showRightPanel, setShowRightPanel] = useState(false);

  const handleTraversalResult = useCallback((data: GraphResponse) => {
    useGraphDataStore.getState().setGraph(data.nodes, data.edges);
  }, []);

  const handleAppChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const value = e.target.value || undefined;
      setSelectedAppId(value ?? null);
      void loadFullGraph(limitInput, value ?? undefined);
    },
    [limitInput, loadFullGraph, setSelectedAppId],
  );

  useEffect(() => {
    void checkHealth();
  }, [checkHealth]);

  const initialLoadDone = useRef(false);
  useEffect(() => {
    if (initialLoadDone.current) return;
    initialLoadDone.current = true;
    void loadFullGraph(limitInput, selectedAppId ?? undefined);
  }, [loadFullGraph, limitInput, selectedAppId]);

  const headerContent = (
    <div className="flex min-w-0 flex-1 items-center gap-3">
      <div className="flex shrink-0 items-center gap-2">
        <label htmlFor="app-selector" className="text-xs whitespace-nowrap text-slate-500">
          App
        </label>
        <select
          id="app-selector"
          className="min-w-36 rounded-lg border border-slate-700 bg-slate-800/80 px-2 py-1.5 text-xs text-slate-200 focus:ring-1 focus:ring-blue-500 focus:outline-none"
          value={selectedAppId ?? ''}
          onChange={handleAppChange}
        >
          <option value="">All Applications</option>
          {applications.map((app) => (
            <option key={app.app_id} value={app.app_id}>
              {app.name} ({app.agent_count})
            </option>
          ))}
        </select>
      </div>

      <Input
        icon={<IconSearch />}
        placeholder="Search nodes…"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        wrapperClassName="flex-1 min-w-0 max-w-sm"
      />

      <div className="flex shrink-0 items-center gap-2">
        <Button
          variant="primary"
          size="sm"
          icon={<IconRefresh className="h-3.5 w-3.5" />}
          onClick={() => {
            const st = useTimelineStore.getState();
            const win = {
              start: new Date(st.windowStart).toISOString(),
              end: new Date(st.windowStart + st.chunkCount * st.chunkBucketSeconds * 1000).toISOString(),
            };
            void loadFullGraph(
              limitInput,
              selectedAppId ?? undefined,
              st.currentTime ?? undefined,
              win,
            );
          }}
        >
          Reload
        </Button>
      </div>

      {lastRefreshedAt && (
        <span className="hidden text-[10px] whitespace-nowrap text-slate-600 2xl:inline">
          Updated: {new Date(lastRefreshedAt).toLocaleTimeString()}
        </span>
      )}
    </div>
  );

  return (
    <AppLayout headerContent={headerContent}>
      <CytoscapeProvider>
        <div className="relative flex h-full overflow-hidden">
          <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
            <div className="relative min-w-0 flex-1">
              {error && (
                <div className="absolute top-3 left-1/2 z-40 -translate-x-1/2 rounded-lg border border-red-700/60 bg-red-900/90 px-4 py-2 text-xs text-red-200 shadow-lg backdrop-blur-sm">
                  {error}
                </div>
              )}
              <GraphCanvas />
              <GraphControls />
              <HotEdgesPanel />

              <button
                onClick={() => setShowRightPanel(true)}
                className="absolute top-3 right-3 z-30 rounded-xl border border-slate-700/60 bg-slate-800/90 p-2.5 shadow-lg backdrop-blur-sm lg:hidden"
                aria-label="Show panel"
              >
                <IconPanel className="h-5 w-5 text-slate-300" />
              </button>
            </div>
            <TimelineBar limit={limitInput} />
          </div>

          {showRightPanel && (
            <button
              type="button"
              className="animate-fade-in fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
              onClick={() => setShowRightPanel(false)}
              aria-label="Close panel"
            />
          )}

          <aside
            className={[
              'flex shrink-0 flex-col overflow-hidden border-l border-slate-800/70 bg-slate-950/95 backdrop-blur-sm',
              'lg:relative lg:w-96 xl:w-[26rem]',
              'fixed top-0 right-0 z-50 h-full w-96 max-w-[90vw] lg:static',
              'transform transition-transform duration-300 ease-out',
              showRightPanel ? 'translate-x-0' : 'translate-x-full lg:translate-x-0',
            ].join(' ')}
          >
            <button
              onClick={() => setShowRightPanel(false)}
              className="absolute top-2.5 right-2.5 z-10 rounded-lg p-1.5 transition-colors hover:bg-slate-800 lg:hidden"
              aria-label="Close panel"
            >
              <IconX className="h-4 w-4 text-slate-400" />
            </button>

            <div className="scrollbar-none flex shrink-0 overflow-x-auto border-b border-slate-800/70">
              {PANEL_CONFIG.map(({ id, shortLabel }) => (
                <button
                  key={id}
                  onClick={() => setRightPanel(id)}
                  className={[
                    'relative flex-1 px-1.5 py-2.5 text-[11px] font-medium whitespace-nowrap transition-colors',
                    rightPanel === id
                      ? 'border-b-2 border-blue-500 text-blue-400'
                      : 'text-slate-500 hover:text-slate-300',
                  ].join(' ')}
                >
                  <span className="inline-flex items-center gap-1">
                    {shortLabel}
                    {id === 'log' && logCount > 0 && (
                      <span className="inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-blue-600 px-1 text-[9px] leading-none font-semibold text-white tabular-nums">
                        {logCount > 99 ? '99+' : logCount}
                      </span>
                    )}
                  </span>
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto">
              {rightPanel === 'detail' && <NodeDetail />}
              {rightPanel === 'filter' && <FilterPanel />}
              {rightPanel === 'query' && <QueryPanel />}
              {rightPanel === 'insights' && <GraphInsightsPanel />}
              {rightPanel === 'export' && <ExportPanel />}
              {rightPanel === 'traversal' && (
                <TraversalPanel
                  onResult={handleTraversalResult}
                  onReset={() => void loadFullGraph(limitInput, selectedAppId ?? undefined)}
                />
              )}
              {rightPanel === 'traces' && <TracesPanel />}
              {rightPanel === 'log' && <LogPanel />}
            </div>
          </aside>
        </div>
      </CytoscapeProvider>
    </AppLayout>
  );
}
