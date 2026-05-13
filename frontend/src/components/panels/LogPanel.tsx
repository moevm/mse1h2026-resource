import type { ReactNode } from 'react';

import { type QueryHistoryEntry, useGraphDataStore } from '../../features/graph/store';
import { formatTime } from '../../lib/utils/format';
import { useLogStore } from '../../store/logStore';
import type { LogLevel } from '../../types';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { IconCheckCircle, IconExclamation, IconInfo, IconXCircle } from '../icons';

const LEVEL_CONFIG: Record<LogLevel, { icon: ReactNode; color: string; bg: string }> = {
  info: { icon: <IconInfo className="h-3.5 w-3.5" />, color: '#60a5fa', bg: 'bg-blue-500/10' },
  success: {
    icon: <IconCheckCircle className="h-3.5 w-3.5" />,
    color: '#22c55e',
    bg: 'bg-green-500/10',
  },
  warn: {
    icon: <IconExclamation className="h-3.5 w-3.5" />,
    color: '#f59e0b',
    bg: 'bg-amber-500/10',
  },
  error: { icon: <IconXCircle className="h-3.5 w-3.5" />, color: '#ef4444', bg: 'bg-red-500/10' },
};

export function LogPanel() {
  const entries = useLogStore((s) => s.entries);
  const filterLevel = useLogStore((s) => s.filterLevel);
  const filterSource = useLogStore((s) => s.filterSource);
  const setFilterLevel = useLogStore((s) => s.setFilterLevel);
  const setFilterSource = useLogStore((s) => s.setFilterSource);
  const clearLogs = useLogStore((s) => s.clearLogs);
  const queryHistory = useGraphDataStore((s) => s.queryHistory);

  const filteredEntries = entries.filter((e) => {
    if (filterLevel !== 'all' && e.level !== filterLevel) return false;
    if (filterSource && !e.source.toLowerCase().includes(filterSource.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="shrink-0 space-y-2 border-b border-slate-800 p-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold tracking-wider text-slate-400 uppercase">Activity Log</h4>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-600">{filteredEntries.length} entries</span>
            <Button variant="ghost" size="xs" onClick={clearLogs}>
              Clear
            </Button>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {(['all', 'info', 'success', 'warn', 'error'] as const).map((level) => (
            <button
              key={level}
              onClick={() => setFilterLevel(level)}
              className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors ${
                filterLevel === level
                  ? 'bg-slate-700 text-slate-100'
                  : 'text-slate-500 hover:bg-slate-800 hover:text-slate-300'
              }`}
            >
              {level === 'all' ? (
                'All'
              ) : (
                <span className="flex items-center gap-1">
                  {LEVEL_CONFIG[level].icon}
                  {level}
                </span>
              )}
            </button>
          ))}
        </div>

        <Input placeholder="Filter by source…" value={filterSource} onChange={(e) => setFilterSource(e.target.value)} />
      </div>

      <div className="flex shrink-0 border-b border-slate-800">
        <TabSection entries={filteredEntries} queryHistory={queryHistory} />
      </div>
    </div>
  );
}

function TabSection({
  entries,
  queryHistory,
}: Readonly<{
  entries: ReturnType<typeof useLogStore.getState>['entries'];
  queryHistory: QueryHistoryEntry[];
}>) {
  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {queryHistory.length > 0 && (
        <div className="shrink-0 border-b border-slate-800 p-3">
          <h5 className="mb-2 text-[10px] font-semibold tracking-wider text-slate-500 uppercase">Recent Queries</h5>
          <div className="max-h-32 space-y-1 overflow-y-auto">
            {queryHistory.slice(0, 10).map((q) => (
              <QueryHistoryRow key={q.id} entry={q} />
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 space-y-0.5 overflow-y-auto p-2">
        {entries.length === 0 && (
          <p className="p-2 text-center text-xs text-slate-600 italic">No log entries yet. Actions will appear here.</p>
        )}
        {entries.map((entry) => {
          const cfg = LEVEL_CONFIG[entry.level];
          return (
            <div
              key={entry.id}
              className={`flex items-start gap-2 rounded px-2 py-1.5 text-[11px] transition-colors hover:bg-slate-800/50 ${cfg.bg}`}
            >
              <span className="mt-0.5 shrink-0" style={{ color: cfg.color }}>
                {cfg.icon}
              </span>

              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span
                    className="rounded px-1 py-0.5 font-mono text-[9px] font-medium"
                    style={{
                      color: cfg.color,
                      backgroundColor: cfg.color + '15',
                    }}
                  >
                    {entry.source}
                  </span>
                  <span className="text-[9px] text-slate-600">{formatTime(entry.timestamp)}</span>
                </div>
                <p className="mt-0.5 wrap-break-word text-slate-300">{entry.message}</p>

                {entry.details && Object.keys(entry.details).length > 0 && (
                  <div className="mt-1 border-l border-slate-700 pl-2">
                    {Object.entries(entry.details).map(([k, v]) => (
                      <div key={k} className="flex gap-2 text-[10px]">
                        <span className="text-slate-500">{k}:</span>
                        <span className="font-mono text-slate-400">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function QueryHistoryRow({ entry }: Readonly<{ entry: QueryHistoryEntry }>) {
  const typeColors: Record<string, string> = {
    full: '#3b82f6',
    subgraph: '#8b5cf6',
    path: '#22c55e',
    impact: '#ef4444',
    layout: '#06b6d4',
  };

  const color = typeColors[entry.type] ?? '#64748b';

  return (
    <div className="flex items-center gap-2 rounded px-2 py-1 text-[10px] transition-colors hover:bg-slate-800">
      <span className="rounded px-1.5 py-0.5 font-medium" style={{ color, backgroundColor: color + '20' }}>
        {entry.type}
      </span>
      <span className="flex-1 truncate font-mono text-slate-400">
        {entry.nodeCount}n / {entry.edgeCount}e
      </span>
      <span className="shrink-0 text-slate-600">{formatTime(entry.timestamp)}</span>
    </div>
  );
}
