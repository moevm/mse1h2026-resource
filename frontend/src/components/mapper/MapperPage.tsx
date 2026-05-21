import { useCallback, useEffect, useState } from 'react';

import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';

import { fetchAgents } from '../../api/agentsApi';
import { fetchApplications } from '../../api/applicationsApi';
import { mapperApi } from '../../api/mapperApi';
import { useMapperStore } from '../../store/mapperStore';
import type { MappingConfig } from '../../types/mapper';
import { MappingBuilder } from './MappingBuilder';
import { PreviewPanel } from './PreviewPanel';
import { RawDataPanel } from './RawDataPanel';
import { ResizablePanels } from './ResizablePanels';
import { SchemaBrowser } from './SchemaBrowser';
import { TimelineSlider } from './TimelineSlider';

interface Agent {
  agent_id: string;
  name: string;
  source_type: string;
  description?: string;
  app_id?: string;
  app_name?: string;
}

interface Application {
  app_id: string;
  name: string;
  agent_count: number;
}

type MobilePanel = 'mappings' | 'data' | 'config';
<<<<<<< HEAD
=======
type MockerAction = 'create' | null;
>>>>>>> f81199920d6f71cd1754b6eaad7dfc55c74955f8

export function MapperPage() {
  const {
    chunks,
    selectedChunk,
    chunksLoading,
    draftMapping,
    previewLoading,
    setChunks,
    selectChunk,
    setChunksLoading,
    setDraftMapping,
    setPreview,
    setPreviewLoading,
    clearPreview,
    saveDraftMapping,
  } = useMapperStore();

  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);

  const [activeMapping, setActiveMapping] = useState<MappingConfig | null>(null);
  const [availableMappings, setAvailableMappings] = useState<MappingConfig[]>([]);
  const [mappingsLoading, setMappingsLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [replayLoading, setReplayLoading] = useState(false);
  const [lastReplayAt, setLastReplayAt] = useState<string | null>(null);
  const [deactivateClearLoading, setDeactivateClearLoading] = useState(false);

  const [activePanel, setActivePanel] = useState<MobilePanel>('data');

  const buildUniqueMappingName = useCallback(() => {
    const baseName = selectedAgent ? `${selectedAgent.name} Mapping` : 'New Mapping';
    const existingNames = new Set(availableMappings.map((mapping) => mapping.name));

    if (!existingNames.has(baseName)) {
      return baseName;
    }

    let index = 2;
    while (existingNames.has(`${baseName} ${index}`)) {
      index += 1;
    }

    return `${baseName} ${index}`;
  }, [availableMappings, selectedAgent]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await fetchApplications();
        if (!cancelled) setApplications(data);
      } catch (error) {
        console.error('Failed to load applications:', error);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await fetchAgents();
        if (!cancelled) setAgents(data);
      } catch (error) {
        console.error('Failed to load agents:', error);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const filteredAgents = selectedAppId ? agents.filter((a) => a.app_id === selectedAppId) : agents;
  const currentSelectedChunkId = selectedChunk?.id ?? null;
  const activeMappings = availableMappings.filter((mapping) => mapping.is_active);

  const loadMappingsForAgent = useCallback(
    async (_agent: Agent | null) => {
      setMappingsLoading(true);
      try {
        const response = await mapperApi.listMappings({ limit: 100 });
        setAvailableMappings(response.mappings);

        const active = response.mappings.find((mapping) => mapping.is_active) ?? null;
        setActiveMapping(active);
        if (active) {
          setDraftMapping(active);
        }
      } catch (error) {
        console.error('Failed to load mappings:', error);
      } finally {
        setMappingsLoading(false);
      }
    },
    [setDraftMapping],
  );

  const loadChunksForAgent = useCallback(
    async (agent: Agent | null) => {
      if (!agent) {
        setChunks([]);
        selectChunk(null);
        return;
      }

      setChunksLoading(true);
      try {
        const response = await mapperApi.listChunks({
          agent_id: agent.agent_id,
          limit: 100,
        });
        setChunks(response.chunks);

        if (response.chunks.length === 0) {
          if (currentSelectedChunkId !== null) {
            selectChunk(null);
          }
        } else {
          const selectedStillExists = currentSelectedChunkId
            ? response.chunks.find((chunk) => chunk.id === currentSelectedChunkId)
            : null;
          const nextChunk = selectedStillExists ?? response.chunks[0];
          if (nextChunk.id !== currentSelectedChunkId) {
            selectChunk(nextChunk);
          }
        }
      } catch (error) {
        console.error('Failed to load chunks:', error);
      } finally {
        setChunksLoading(false);
      }
    },
    [currentSelectedChunkId, selectChunk, setChunks, setChunksLoading],
  );

  const handlePinChunk = useCallback(
    async (chunkId: string) => {
      try {
        await mapperApi.pinChunk(chunkId);
        setChunks(chunks.map((c) => (c.id === chunkId ? { ...c, is_pinned: true } : c)));
        if (selectedChunk?.id === chunkId) {
          selectChunk({ ...selectedChunk, is_pinned: true });
        }
      } catch (error) {
        console.error('Failed to pin chunk:', error);
      }
    },
    [chunks, selectedChunk, setChunks, selectChunk],
  );

  const handleUnpinChunk = useCallback(
    async (chunkId: string) => {
      try {
        await mapperApi.unpinChunk(chunkId);
        setChunks(chunks.map((c) => (c.id === chunkId ? { ...c, is_pinned: false } : c)));
        if (selectedChunk?.id === chunkId) {
          selectChunk({ ...selectedChunk, is_pinned: false });
        }
      } catch (error) {
        console.error('Failed to unpin chunk:', error);
      }
    },
    [chunks, selectedChunk, setChunks, selectChunk],
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!selectedAgent && !cancelled) {
        return;
      }
      setMappingsLoading(true);
      try {
        const response = await mapperApi.listMappings({ limit: 100 });
        if (!cancelled) {
          setAvailableMappings(response.mappings);
          const active = response.mappings.find((mapping) => mapping.is_active) ?? null;
          setActiveMapping(active);
          if (active) {
            setDraftMapping(active);
          }
        }
      } catch (error) {
        console.error('Failed to load mappings:', error);
      } finally {
        if (!cancelled) setMappingsLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [selectedAgent, setDraftMapping]);

  useEffect(() => {
    void loadChunksForAgent(selectedAgent);
  }, [selectedAgent, loadChunksForAgent]);

  const handleActivate = useCallback(
    async (mappingId: string) => {
      try {
        const updated = await mapperApi.activateMapping(mappingId);
        setActiveMapping(updated);
        setDraftMapping(updated);
        await loadMappingsForAgent(selectedAgent);
      } catch (error) {
        console.error('Failed to activate mapping:', error);
      }
    },
    [loadMappingsForAgent, selectedAgent, setDraftMapping],
  );

  const handleSelectMapping = useCallback(
    (mapping: MappingConfig) => {
      setDraftMapping(mapping);
      if (mapping.is_active) {
        setActiveMapping(mapping);
      }
    },
    [setDraftMapping],
  );

  const handleDeactivateAndClear = useCallback(async () => {
    const mappingId = draftMapping?.id && draftMapping.is_active ? draftMapping.id : activeMapping?.id;
    if (!mappingId) return;
    setDeactivateClearLoading(true);
    try {
      const result = await mapperApi.deactivateAndClearMapping(mappingId);
      setActiveMapping(null);
      setActionMessage(`Deactivated + cleared: ${result.deleted_nodes} nodes, ${result.deleted_edges} edges`);
      await loadMappingsForAgent(selectedAgent);
    } catch (error) {
      console.error('Failed to deactivate and clear mapping:', error);
      setActionMessage('Deactivate + clear failed');
    } finally {
      setDeactivateClearLoading(false);
    }
  }, [activeMapping, draftMapping, loadMappingsForAgent, selectedAgent]);

  const handleNewMapping = useCallback(() => {
    setDraftMapping({
      name: buildUniqueMappingName(),
      source_type: 'custom',
      field_mappings: [],
      conditional_rules: [],
      edge_preset_id: 'default',
      sample_chunk_id: selectedChunk?.id ?? null,
    });
    clearPreview();
    setActionMessage(null);
  }, [buildUniqueMappingName, selectedChunk, setDraftMapping]);

  const ensureDraftMappingId = useCallback(async (): Promise<string | null> => {
    if (!draftMapping) return null;
    if (draftMapping.id) return draftMapping.id;

    await saveDraftMapping();
    return useMapperStore.getState().draftMapping?.id ?? null;
  }, [draftMapping, saveDraftMapping]);

  const handlePreview = useCallback(async () => {
    if (!selectedChunk) {
      setActionMessage('Select a data chunk first');
      return;
    }

    setPreviewLoading(true);
    setActionMessage(null);

    try {
      const mappingId = await ensureDraftMappingId();
      if (!mappingId) {
        setActionMessage('Create or save a mapping first');
        return;
      }

      const result = await mapperApi.preview(selectedChunk.id, mappingId);
      setPreview(result.nodes, result.edges, result.warnings, result.unresolved_references);
      setActionMessage(`Preview: ${result.nodes.length} nodes, ${result.edges.length} edges`);
    } catch (error) {
      console.error('Preview failed:', error);
      setActionMessage('Preview failed');
    } finally {
      setPreviewLoading(false);
    }
  }, [selectedChunk, ensureDraftMappingId, setPreview, setPreviewLoading]);

  const handleApply = useCallback(async () => {
    if (!selectedChunk) {
      setActionMessage('Select a data chunk first');
      return;
    }

    setPreviewLoading(true);
    setActionMessage(null);

    try {
      const mappingId = await ensureDraftMappingId();
      if (!mappingId) {
        setActionMessage('Create or save a mapping first');
        return;
      }

      const result = await mapperApi.apply(selectedChunk.id, mappingId);
      if (result.success) {
        setActionMessage(`Applied: ${result.nodes_processed} nodes, ${result.edges_processed} edges`);
      } else {
        setActionMessage(`Apply finished with errors (${result.errors.length})`);
      }

      const preview = await mapperApi.preview(selectedChunk.id, mappingId);
      setPreview(preview.nodes, preview.edges, preview.warnings, preview.unresolved_references);
    } catch (error) {
      console.error('Apply failed:', error);
      setActionMessage('Apply failed');
    } finally {
      setPreviewLoading(false);
    }
  }, [selectedChunk, ensureDraftMappingId, setPreview, setPreviewLoading]);

  const handleReplay = useCallback(async () => {
    setReplayLoading(true);
    setActionMessage(null);

    try {
      const mappingId = await ensureDraftMappingId();
      if (!mappingId) {
        setActionMessage('Create or save a mapping first');
        return;
      }

      const sourceType = draftMapping?.source_type;
      let clearedSummary = '';
      if (sourceType) {
        const stale = availableMappings.filter(
          (m) => m.is_active && m.source_type === sourceType && m.id && m.id !== mappingId,
        );
        for (const m of stale) {
          try {
            const res = await mapperApi.deactivateAndClearMapping(m.id as string);
            clearedSummary += ` cleared ${res.deleted_nodes}n/${res.deleted_edges}e from "${m.name}";`;
          } catch (e) {
            console.warn('deactivate-and-clear failed for', m.id, e);
          }
        }
      }

      try {
        await mapperApi.activateMapping(mappingId);
      } catch (e) {
        console.warn('activate failed (continuing with replay)', e);
      }

      const result = await mapperApi.replayMapping(mappingId, {
        agent_id: selectedAgent?.agent_id,
      });

      const tail = `${result.chunks_processed} chunks, ${result.nodes_created} nodes, ${result.edges_created} edges`;
      if (result.errors.length > 0) {
        setActionMessage(`Replay: ${tail}, errors: ${result.errors.length}.${clearedSummary}`);
      } else {
        setActionMessage(`Replay complete: ${tail}.${clearedSummary}`);
        setLastReplayAt(new Date().toLocaleString());
      }

      await loadMappingsForAgent(selectedAgent);
    } catch (error) {
      console.error('Replay failed:', error);
      const detail =
        (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        ?? (error as Error).message
        ?? 'unknown error';
      setActionMessage(`Replay failed: ${detail}`);
    } finally {
      setReplayLoading(false);
    }
  }, [ensureDraftMappingId, selectedAgent, draftMapping, availableMappings, loadMappingsForAgent]);

  const refreshMappings = useCallback(async () => {
    await loadMappingsForAgent(selectedAgent);
  }, [loadMappingsForAgent, selectedAgent]);

<<<<<<< HEAD
=======
  const handleCreateMappings = useCallback(async () => {
    setMockerActionLoading('create');
    setMockerMessage(null);
    try {
      const templates = await mapperApi.listMappingTemplates();
      let createdCount = 0;

      for (const template of templates.templates) {
        try {
          await mapperApi.instantiateMappingTemplate(template.id, {
            sample_chunk_id: selectedChunk?.id ?? null,
            activate: true,
          });
          createdCount += 1;
        } catch (error) {
          const detail =
            typeof error === 'object' && error !== null && 'response' in error
              ? (error as { response?: { status?: number } }).response?.status
              : undefined;

          if (detail !== 409) {
            throw error;
          }
        }
      }

      setMockerMessage({
        type: 'success',
        text:
          createdCount > 0
            ? `Installed ${createdCount} built-in mapping templates`
            : 'Built-in mapping templates already installed',
      });
      await Promise.all([refreshMappings(), loadChunksForAgent(selectedAgent)]);
    } catch (error) {
      setMockerMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Built-in mapping installation failed',
      });
    } finally {
      setMockerActionLoading(null);
    }
  }, [refreshMappings, loadChunksForAgent, selectedAgent]);

>>>>>>> f81199920d6f71cd1754b6eaad7dfc55c74955f8
  return (
    <DndProvider backend={HTML5Backend}>
      <div className="flex h-full min-h-0 flex-col bg-slate-900">
        <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-slate-700/50 bg-slate-800/50 px-3 py-2 sm:gap-3 sm:px-4">
          <div className="flex w-full flex-col items-start gap-2 sm:w-auto sm:flex-row sm:items-center sm:gap-3">
            <div className="flex w-full items-center gap-2 sm:w-auto">
              <span className="hidden text-xs tracking-wide text-slate-500 uppercase sm:inline">App:</span>
              <select
                value={selectedAppId ?? ''}
                onChange={(e) => {
                  setSelectedAppId(e.target.value || null);
                  setSelectedAgent(null);
                  selectChunk(null);
                }}
                className="flex-1 rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-sm text-slate-200 sm:min-w-[160px] sm:flex-none sm:px-3"
              >
                <option value="">All Apps</option>
                {applications.map((app) => (
                  <option key={app.app_id} value={app.app_id}>
                    {app.name} ({app.agent_count})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex w-full items-center gap-2 sm:w-auto">
              <span className="hidden text-xs tracking-wide text-slate-500 uppercase sm:inline">Agent:</span>
              <select
                value={selectedAgent?.agent_id ?? ''}
                onChange={(e) => {
                  const agent = filteredAgents.find((a) => a.agent_id === e.target.value);
                  setSelectedAgent(agent ?? null);
                  selectChunk(null);
                }}
                className="flex-1 rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-sm text-slate-200 sm:min-w-[180px] sm:flex-none sm:px-3"
              >
                <option value="">Select Agent...</option>
                {filteredAgents.map((agent) => (
                  <option key={agent.agent_id} value={agent.agent_id}>
                    {agent.name} ({agent.source_type})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="hidden flex-1 sm:block" />

          {selectedAgent && (
            <div className="flex items-center gap-2 text-sm">
              {activeMappings.length > 0 ? (
                <>
                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
                  <span className="max-w-[150px] truncate text-emerald-400">
                    {activeMappings.length} active mapping{activeMappings.length === 1 ? '' : 's'}
                  </span>
                  <button
                    onClick={() => {
                      void handleDeactivateAndClear();
                    }}
                    disabled={
                      deactivateClearLoading || (!(draftMapping?.id && draftMapping.is_active) && !activeMapping)
                    }
                    className="text-xs text-red-400 underline hover:text-red-300 disabled:text-slate-600"
                  >
                    {deactivateClearLoading ? 'Clearing...' : 'Deactivate'}
                  </button>
                </>
              ) : (
                <span className="text-xs text-slate-500">No active mapping</span>
              )}
            </div>
          )}

<<<<<<< HEAD
=======
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => {
                void handleCreateMappings();
              }}
              disabled={mockerActionLoading !== null}
              className="rounded bg-indigo-600 px-2.5 py-1 text-xs text-white hover:bg-indigo-700 disabled:bg-slate-700 disabled:text-slate-500"
            >
              {mockerActionLoading === 'create' ? 'Installing...' : 'Install built-in mappings'}
            </button>
          </div>
>>>>>>> f81199920d6f71cd1754b6eaad7dfc55c74955f8
        </div>

        <div className="flex shrink-0 border-b border-slate-700/50 bg-slate-800/30 lg:hidden">
          {(['mappings', 'data', 'config'] as const).map((panel) => (
            <button
              key={panel}
              onClick={() => setActivePanel(panel)}
              className={[
                'flex-1 py-2.5 text-xs font-medium capitalize transition-colors',
                activePanel === panel
                  ? 'border-b-2 border-blue-500 text-blue-400'
                  : 'text-slate-500 hover:text-slate-300',
              ].join(' ')}
            >
              {panel}
            </button>
          ))}
        </div>

        <div className="flex min-h-0 flex-1 overflow-hidden">
          <ResizablePanels initialSizes={[15, 50, 35]} minSizes={[200, 300, 250]} className="min-h-0 flex-1">
            <section className="flex min-h-0 flex-col border-r border-slate-700/50 bg-slate-900">
              <div className="shrink-0 border-b border-slate-700/50 bg-slate-800/30 px-3 py-2">
                <h2 className="text-sm font-semibold text-slate-300">Mappings</h2>
                <p className="text-xs text-slate-500">Chunk-matched rules, not agent-bound</p>
              </div>
              <div className="flex-1 space-y-1 overflow-auto p-2">
                {mappingsLoading ? (
                  <div className="py-4 text-center text-sm text-slate-500">Loading...</div>
                ) : availableMappings.length === 0 ? (
                  <div className="py-4 text-center text-sm text-slate-500">No mappings installed yet</div>
                ) : (
                  availableMappings.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => handleSelectMapping(m)}
                      onDoubleClick={() => {
                        void handleActivate(m.id);
                      }}
                      className={[
                        'w-full rounded px-3 py-2 text-left text-sm transition-colors',
                        m.is_active
                          ? 'border border-emerald-500/50 bg-emerald-600/30 text-emerald-300'
                          : 'bg-slate-800/50 text-slate-300 hover:bg-slate-700/50',
                      ].join(' ')}
                    >
                      <div className="flex items-center gap-2">
                        {m.is_active && <span className="h-2 w-2 rounded-full bg-emerald-500" />}
                        <span className="font-medium">{m.name}</span>
                      </div>
                      <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
                        <span>{m.field_mappings?.length ?? 0} fields</span>
                        {m.sample_chunk_id && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              const chunk = chunks.find((c) => c.id === m.sample_chunk_id);
                              if (chunk) selectChunk(chunk);
                            }}
                            className="inline-flex items-center gap-1 font-mono text-amber-400 hover:text-amber-300 hover:underline"
                            title={`Jump to sample chunk: ${m.sample_chunk_id}`}
                          >
                            📌 chunk: {m.sample_chunk_id.slice(0, 8)}...
                          </button>
                        )}
                      </div>
                    </button>
                  ))
                )}

                <button
                  onClick={handleNewMapping}
                  disabled={!selectedAgent}
                  className="mt-2 w-full rounded border border-dashed border-slate-600 bg-slate-800/50 px-3 py-2 text-sm text-slate-300 hover:bg-slate-700/50 disabled:opacity-50"
                >
                  + Create New Mapping
                </button>
              </div>
            </section>

            <section className="flex min-h-0 min-w-0 flex-col bg-slate-900">
              <TimelineSlider
                chunks={chunks}
                selectedChunk={selectedChunk}
                onSelectChunk={selectChunk}
                onPinChunk={handlePinChunk}
                onUnpinChunk={handleUnpinChunk}
                loading={chunksLoading}
                sampleChunkId={draftMapping?.sample_chunk_id}
              />

              <div className="flex-1 overflow-auto">
                {selectedChunk ? (
                  <RawDataPanel
                    data={selectedChunk.data}
                    chunkId={selectedChunk.id}
                    onCreateMapping={handleNewMapping}
                    fieldMappings={draftMapping?.field_mappings ?? []}
                  />
                ) : (
                  <div className="p-8 text-center text-sm text-slate-500">
                    {chunksLoading ? (
                      <div className="flex items-center justify-center gap-2">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-500 border-t-blue-500" />
                        Loading data...
                      </div>
                    ) : selectedAgent ? (
                      <div className="space-y-2">
                        <div className="text-slate-400">No data chunks available</div>
                        <div className="text-xs text-slate-600">The agent has not sent any data yet</div>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <div className="text-slate-400">Select an agent to view data</div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </section>

            <section className="flex min-h-0 flex-col border-l border-slate-700/50 bg-slate-900">
              <div className="shrink-0 border-b border-slate-700/50 bg-slate-800/30 px-3 py-2">
                <h2 className="text-sm font-semibold text-slate-300">
                  {draftMapping?.name ? `Edit: ${draftMapping.name}` : 'New Mapping'}
                </h2>
              </div>
              {draftMapping ? (
                <ResizablePanels
                  direction="vertical"
                  initialSizes={[70, 30]}
                  minSizes={[220, 140]}
                  className="min-h-0 flex-1"
                >
                  <div className="flex min-h-0 flex-col">
                    <ResizablePanels
                      direction="vertical"
                      initialSizes={[50, 50]}
                      minSizes={[150, 150]}
                      className="min-h-0 flex-1"
                    >
                      <div className="min-h-0 overflow-auto">
                        <SchemaBrowser />
                      </div>
                      <div className="min-h-0 overflow-auto bg-slate-800/20">
                        <MappingBuilder onSaved={refreshMappings} />
                      </div>
                    </ResizablePanels>
                  </div>

                  <div className="flex min-h-0 flex-col border-t border-slate-700/50 bg-slate-800/10">
                    <div className="flex shrink-0 items-center gap-2 border-b border-slate-700/50 px-3 py-2">
                      <button
                        onClick={() => {
                          void handlePreview();
                        }}
                        disabled={!selectedChunk || previewLoading || replayLoading}
                        className="rounded bg-blue-600 px-2.5 py-1 text-xs text-white hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500"
                      >
                        Preview
                      </button>
                      <button
                        onClick={() => {
                          void handleApply();
                        }}
                        disabled={!selectedChunk || previewLoading || replayLoading}
                        className="rounded bg-emerald-600 px-2.5 py-1 text-xs text-white hover:bg-emerald-700 disabled:bg-slate-700 disabled:text-slate-500"
                      >
                        Apply
                      </button>
                      <button
                        onClick={() => {
                          void handleReplay();
                        }}
                        disabled={!draftMapping || previewLoading || replayLoading}
                        className="rounded bg-violet-600 px-2.5 py-1 text-xs text-white hover:bg-violet-700 disabled:bg-slate-700 disabled:text-slate-500"
                      >
                        {replayLoading ? 'Replaying...' : 'Replay'}
                      </button>
                      {actionMessage && <span className="text-xs text-slate-400">{actionMessage}</span>}
                      {lastReplayAt && <span className="text-xs text-slate-500">Last replay: {lastReplayAt}</span>}
                    </div>
                    <div className="min-h-0 flex-1 overflow-auto">
                      <PreviewPanel loading={previewLoading} />
                    </div>
                  </div>
                </ResizablePanels>
              ) : (
                <div className="flex min-h-0 flex-1 flex-col">
                  <ResizablePanels
                    direction="vertical"
                    initialSizes={[50, 50]}
                    minSizes={[150, 150]}
                    className="min-h-0 flex-1"
                  >
                    <div className="min-h-0 overflow-auto">
                      <SchemaBrowser />
                    </div>
                    <div className="flex items-center justify-center text-sm text-slate-500">No mapping selected</div>
                  </ResizablePanels>
                </div>
              )}
            </section>
          </ResizablePanels>
        </div>
      </div>
    </DndProvider>
  );
}
