import { useEffect, useCallback, useState } from "react";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { useMapperStore } from "../../store/mapperStore";
import { mapperApi } from "../../api/mapperApi";
import { fetchApplications } from "../../api/applicationsApi";
import { fetchAgents } from "../../api/agentsApi";
import { RawDataPanel } from "./RawDataPanel";
import { SchemaBrowser } from "./SchemaBrowser";
import { MappingBuilder } from "./MappingBuilder";
import { TimelineSlider } from "./TimelineSlider";
import { ResizablePanels } from "./ResizablePanels";
import { PreviewPanel } from "./PreviewPanel";
import type { MappingConfig, RawDataSource } from "../../types/mapper";

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

type MobilePanel = "mappings" | "data" | "config";

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

  const [activePanel, setActivePanel] = useState<MobilePanel>("data");

  useEffect(() => {
    async function loadApplications() {
      try {
        const data = await fetchApplications();
        setApplications(data);
      } catch (error) {
        console.error("Failed to load applications:", error);
      }
    }
    loadApplications();
  }, []);

  useEffect(() => {
    async function loadAgents() {
      try {
        const data = await fetchAgents();
        setAgents(data);
      } catch (error) {
        console.error("Failed to load agents:", error);
      }
    }
    loadAgents();
  }, []);

  const filteredAgents = selectedAppId
    ? agents.filter((a) => a.app_id === selectedAppId)
    : agents;

  useEffect(() => {
    async function loadMappings() {
      if (!selectedAgent) {
        setActiveMapping(null);
        setAvailableMappings([]);
        return;
      }

      setMappingsLoading(true);
      try {
        const active = await mapperApi.getActiveMapping(selectedAgent.source_type);
        setActiveMapping(active);
        if (active) {
          setDraftMapping(active);
        }

        const response = await mapperApi.listMappings({
          source_type: selectedAgent.source_type,
          limit: 50,
        });
        setAvailableMappings(response.mappings);
      } catch (error) {
        console.error("Failed to load mappings:", error);
      } finally {
        setMappingsLoading(false);
      }
    }
    loadMappings();
  }, [selectedAgent, setDraftMapping]);

  useEffect(() => {
    async function loadChunks() {
      if (!selectedAgent) {
        setChunks([]);
        return;
      }
      setChunksLoading(true);
      try {
        const response = await mapperApi.listChunks({
          source_type: selectedAgent.source_type as RawDataSource,
          limit: 100,
        });
        setChunks(response.chunks);
        if (response.chunks.length > 0 && !selectedChunk) {
          selectChunk(response.chunks[0]);
        }
      } catch (error) {
        console.error("Failed to load chunks:", error);
      } finally {
        setChunksLoading(false);
      }
    }
    loadChunks();
  }, [selectedAgent, setChunks, setChunksLoading, selectChunk, selectedChunk]);

  const handleActivate = useCallback(async (mappingId: string) => {
    try {
      const updated = await mapperApi.activateMapping(mappingId);
      setActiveMapping(updated);
      setDraftMapping(updated);
      if (selectedAgent) {
        const response = await mapperApi.listMappings({
          source_type: selectedAgent.source_type,
          limit: 50,
        });
        setAvailableMappings(response.mappings);
      }
    } catch (error) {
      console.error("Failed to activate mapping:", error);
    }
  }, [selectedAgent, setDraftMapping]);

  const handleSelectMapping = useCallback((mapping: MappingConfig) => {
    setDraftMapping(mapping);
  }, [setDraftMapping]);

  const handleDeactivateAndClear = useCallback(async () => {
    if (!activeMapping) return;
    setDeactivateClearLoading(true);
    try {
      const result = await mapperApi.deactivateAndClearMapping(activeMapping.id);
      setActiveMapping(null);
      setActionMessage(
        `Deactivated + cleared: ${result.deleted_nodes} nodes, ${result.deleted_edges} edges`
      );
    } catch (error) {
      console.error("Failed to deactivate and clear mapping:", error);
      setActionMessage("Deactivate + clear failed");
    } finally {
      setDeactivateClearLoading(false);
    }
  }, [activeMapping]);

  const handleNewMapping = useCallback(() => {
    setDraftMapping({
      name: "New Mapping",
      source_type: selectedAgent?.source_type || "custom",
      field_mappings: [],
      conditional_rules: [],
      edge_preset_id: "default",
      sample_chunk_id: selectedChunk?.id || null,
    });
    clearPreview();
    setActionMessage(null);
  }, [selectedAgent, selectedChunk, setDraftMapping]);

  const ensureDraftMappingId = useCallback(async (): Promise<string | null> => {
    if (!draftMapping) return null;
    if (draftMapping.id) return draftMapping.id;

    await saveDraftMapping();
    return useMapperStore.getState().draftMapping?.id || null;
  }, [draftMapping, saveDraftMapping]);

  const handlePreview = useCallback(async () => {
    if (!selectedChunk) {
      setActionMessage("Select a data chunk first");
      return;
    }

    setPreviewLoading(true);
    setActionMessage(null);

    try {
      const mappingId = await ensureDraftMappingId();
      if (!mappingId) {
        setActionMessage("Create or save a mapping first");
        return;
      }

      const result = await mapperApi.preview(selectedChunk.id, mappingId);
      setPreview(
        result.nodes,
        result.edges,
        result.warnings,
        result.unresolved_references
      );
      setActionMessage(`Preview: ${result.nodes.length} nodes, ${result.edges.length} edges`);
    } catch (error) {
      console.error("Preview failed:", error);
      setActionMessage("Preview failed");
    } finally {
      setPreviewLoading(false);
    }
  }, [selectedChunk, ensureDraftMappingId, setPreview, setPreviewLoading]);

  const handleApply = useCallback(async () => {
    if (!selectedChunk) {
      setActionMessage("Select a data chunk first");
      return;
    }

    setPreviewLoading(true);
    setActionMessage(null);

    try {
      const mappingId = await ensureDraftMappingId();
      if (!mappingId) {
        setActionMessage("Create or save a mapping first");
        return;
      }

      const result = await mapperApi.apply(selectedChunk.id, mappingId);
      if (result.success) {
        setActionMessage(`Applied: ${result.nodes_processed} nodes, ${result.edges_processed} edges`);
      } else {
        setActionMessage(`Apply finished with errors (${result.errors.length})`);
      }

      const preview = await mapperApi.preview(selectedChunk.id, mappingId);
      setPreview(
        preview.nodes,
        preview.edges,
        preview.warnings,
        preview.unresolved_references
      );
    } catch (error) {
      console.error("Apply failed:", error);
      setActionMessage("Apply failed");
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
        setActionMessage("Create or save a mapping first");
        return;
      }

      const result = await mapperApi.replayMapping(mappingId, {
        agent_id: selectedAgent?.agent_id,
      });

      if (result.errors.length > 0) {
        setActionMessage(
          `Replay: ${result.chunks_processed} chunks, ${result.nodes_created} nodes, ${result.edges_created} edges, errors: ${result.errors.length}`
        );
      } else {
        setActionMessage(
          `Replay complete: ${result.chunks_processed} chunks, ${result.nodes_created} nodes, ${result.edges_created} edges`
        );
        setLastReplayAt(new Date().toLocaleString());
      }
    } catch (error) {
      console.error("Replay failed:", error);
      setActionMessage("Replay failed");
    } finally {
      setReplayLoading(false);
    }
  }, [ensureDraftMappingId, selectedAgent?.agent_id]);

  const refreshMappings = useCallback(async () => {
    if (!selectedAgent) return;
    try {
      const response = await mapperApi.listMappings({
        source_type: selectedAgent.source_type,
        limit: 50,
      });
      setAvailableMappings(response.mappings);
    } catch (error) {
      console.error("Failed to refresh mappings:", error);
    }
  }, [selectedAgent]);

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="h-full flex flex-col bg-slate-900">
        
        <div className="flex flex-wrap items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 bg-slate-800/50 border-b border-slate-700/50 shrink-0">
          
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3 w-full sm:w-auto">
            
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <span className="text-xs text-slate-500 uppercase tracking-wide hidden sm:inline">App:</span>
              <select
                value={selectedAppId || ""}
                onChange={(e) => {
                  setSelectedAppId(e.target.value || null);
                  setSelectedAgent(null);
                  selectChunk(null);
                }}
                className="flex-1 sm:flex-none bg-slate-800 text-slate-200 px-2 sm:px-3 py-1.5 rounded border border-slate-600 text-sm sm:min-w-[160px]"
              >
                <option value="">All Apps</option>
                {applications.map((app) => (
                  <option key={app.app_id} value={app.app_id}>
                    {app.name} ({app.agent_count})
                  </option>
                ))}
              </select>
            </div>

            
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <span className="text-xs text-slate-500 uppercase tracking-wide hidden sm:inline">Agent:</span>
              <select
                value={selectedAgent?.agent_id || ""}
                onChange={(e) => {
                  const agent = filteredAgents.find((a) => a.agent_id === e.target.value);
                  setSelectedAgent(agent || null);
                  selectChunk(null);
                }}
                className="flex-1 sm:flex-none bg-slate-800 text-slate-200 px-2 sm:px-3 py-1.5 rounded border border-slate-600 text-sm sm:min-w-[180px]"
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

          <div className="hidden sm:block flex-1" />

          
          {selectedAgent && (
            <div className="flex items-center gap-2 text-sm">
              {activeMapping ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-emerald-400 truncate max-w-[150px]">
                    {activeMapping.name}
                  </span>
                  <button
                    onClick={handleDeactivateAndClear}
                    disabled={deactivateClearLoading}
                    className="text-red-400 hover:text-red-300 text-xs underline disabled:text-slate-600"
                  >
                    {deactivateClearLoading ? "Clearing..." : "Deactivate"}
                  </button>
                </>
              ) : (
                <span className="text-slate-500 text-xs">No active mapping</span>
              )}
            </div>
          )}
        </div>

        
        <div className="flex lg:hidden border-b border-slate-700/50 bg-slate-800/30 shrink-0">
          {(["mappings", "data", "config"] as const).map((panel) => (
            <button
              key={panel}
              onClick={() => setActivePanel(panel)}
              className={[
                "flex-1 py-2.5 text-xs font-medium capitalize transition-colors",
                activePanel === panel
                  ? "text-blue-400 border-b-2 border-blue-500"
                  : "text-slate-500 hover:text-slate-300",
              ].join(" ")}
            >
              {panel}
            </button>
          ))}
        </div>

        
        <div className="flex-1 flex overflow-hidden min-h-0">
          <ResizablePanels
            initialSizes={[15, 50, 35]}
            minSizes={[200, 300, 250]}
            className="flex-1"
          >
            
            <section className="border-r border-slate-700/50 bg-slate-900 flex flex-col">
              <div className="px-3 py-2 border-b border-slate-700/50 bg-slate-800/30 shrink-0">
                <h2 className="text-sm font-semibold text-slate-300">Mappings</h2>
                <p className="text-xs text-slate-500">
                  {selectedAgent?.source_type || "Select agent"}
                </p>
              </div>
              <div className="flex-1 overflow-auto p-2 space-y-1">
                {mappingsLoading ? (
                  <div className="text-slate-500 text-sm text-center py-4">Loading...</div>
                ) : availableMappings.length === 0 ? (
                  <div className="text-slate-500 text-sm text-center py-4">
                    No mappings for this source type
                  </div>
                ) : (
                  availableMappings.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => handleSelectMapping(m)}
                      onDoubleClick={() => handleActivate(m.id)}
                      className={[
                        "w-full text-left px-3 py-2 rounded text-sm transition-colors",
                        m.id === activeMapping?.id
                          ? "bg-emerald-600/30 border border-emerald-500/50 text-emerald-300"
                          : "bg-slate-800/50 hover:bg-slate-700/50 text-slate-300",
                      ].join(" ")}
                    >
                      <div className="flex items-center gap-2">
                        {m.id === activeMapping?.id && (
                          <span className="w-2 h-2 rounded-full bg-emerald-500" />
                        )}
                        <span className="font-medium">{m.name}</span>
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5 flex items-center gap-1.5 flex-wrap">
                        <span>{m.field_mappings?.length || 0} fields</span>
                        {m.sample_chunk_id && (
                          <span className="text-blue-400 font-mono" title={m.sample_chunk_id}>
                            • chunk: {m.sample_chunk_id.slice(0, 8)}...
                          </span>
                        )}
                      </div>
                    </button>
                  ))
                )}

                <button
                  onClick={handleNewMapping}
                  disabled={!selectedAgent}
                  className="w-full mt-2 bg-slate-800/50 hover:bg-slate-700/50 disabled:opacity-50 text-slate-300 px-3 py-2 rounded text-sm border border-dashed border-slate-600"
                >
                  + Create New Mapping
                </button>
              </div>
            </section>

            
            <section className="flex flex-col min-w-0 bg-slate-900">
              
              <TimelineSlider
                chunks={chunks}
                selectedChunk={selectedChunk}
                onSelectChunk={selectChunk}
                loading={chunksLoading}
                sampleChunkId={draftMapping?.sample_chunk_id}
              />

              
              <div className="flex-1 overflow-auto">
                {selectedChunk ? (
                  <RawDataPanel
                    data={selectedChunk.data}
                    chunkId={selectedChunk.id}
                    onCreateMapping={handleNewMapping}
                    fieldMappings={draftMapping?.field_mappings || []}
                  />
                ) : (
                  <div className="p-8 text-slate-500 text-center text-sm">
                    {chunksLoading ? (
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-4 h-4 border-2 border-slate-500 border-t-blue-500 rounded-full animate-spin" />
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

            
            <section className="bg-slate-900 flex flex-col border-l border-slate-700/50">
              <div className="px-3 py-2 border-b border-slate-700/50 bg-slate-800/30 shrink-0">
                <h2 className="text-sm font-semibold text-slate-300">
                  {activeMapping ? `Edit: ${activeMapping.name}` : "New Mapping"}
                </h2>
              </div>
              <div className="flex-1 flex flex-col min-h-0">
                <ResizablePanels
                  direction="vertical"
                  initialSizes={[50, 50]}
                  minSizes={[150, 150]}
                  className="flex-1"
                >
                  
                  <div className="overflow-auto min-h-0">
                    <SchemaBrowser />
                  </div>
                  
                  {draftMapping ? (
                    <div className="overflow-auto min-h-0 bg-slate-800/20">
                      <MappingBuilder onSaved={refreshMappings} />
                    </div>
                  ) : (
                    <div className="flex items-center justify-center text-slate-500 text-sm">
                      No mapping selected
                    </div>
                  )}
                </ResizablePanels>
              </div>

              {draftMapping && (
                <div className="border-t border-slate-700/50 bg-slate-800/10 shrink-0">
                  <div className="px-3 py-2 border-b border-slate-700/50 flex items-center gap-2">
                    <button
                      onClick={handlePreview}
                      disabled={!selectedChunk || previewLoading || replayLoading}
                      className="text-xs bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500 text-white px-2.5 py-1 rounded"
                    >
                      Preview
                    </button>
                    <button
                      onClick={handleApply}
                      disabled={!selectedChunk || previewLoading || replayLoading}
                      className="text-xs bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-700 disabled:text-slate-500 text-white px-2.5 py-1 rounded"
                    >
                      Apply
                    </button>
                    <button
                      onClick={handleReplay}
                      disabled={!draftMapping || previewLoading || replayLoading}
                      className="text-xs bg-violet-600 hover:bg-violet-700 disabled:bg-slate-700 disabled:text-slate-500 text-white px-2.5 py-1 rounded"
                    >
                      {replayLoading ? "Replaying..." : "Replay"}
                    </button>
                    {actionMessage && (
                      <span className="text-xs text-slate-400">{actionMessage}</span>
                    )}
                    {lastReplayAt && (
                      <span className="text-xs text-slate-500">Last replay: {lastReplayAt}</span>
                    )}
                  </div>
                  <div className="max-h-60 overflow-auto">
                    <PreviewPanel loading={previewLoading} />
                  </div>
                </div>
              )}
            </section>
          </ResizablePanels>
        </div>
      </div>
    </DndProvider>
  );
}
