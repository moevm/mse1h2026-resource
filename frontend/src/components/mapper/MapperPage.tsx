import { useEffect, useCallback, useState } from "react";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { useMapperStore } from "../../store/mapperStore";
import { mapperApi } from "../../api/mapperApi";
import { fetchApplications } from "../../api/applicationsApi";
import { RawDataPanel } from "./RawDataPanel";
import { SchemaBrowser } from "./SchemaBrowser";
import { MappingBuilder } from "./MappingBuilder";
import { TimelineSlider } from "./TimelineSlider";
import { PreviewPanel } from "./PreviewPanel";
import type { MappingConfig } from "../../types/mapper";

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

  // Load applications first
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

  // Load agents
  useEffect(() => {
    async function loadAgents() {
      try {
        const response = await fetch("/api/v1/agents/");
        const data = await response.json();
        setAgents(data);
      } catch (error) {
        console.error("Failed to load agents:", error);
      }
    }
    loadAgents();
  }, []);

  // Filter agents by selected application
  const filteredAgents = selectedAppId
    ? agents.filter((a) => a.app_id === selectedAppId)
    : agents;

  // Load active mapping and available mappings when agent changes
  useEffect(() => {
    async function loadMappings() {
      if (!selectedAgent) {
        setActiveMapping(null);
        setAvailableMappings([]);
        return;
      }

      setMappingsLoading(true);
      try {
        // Load active mapping for this source type
        const active = await mapperApi.getActiveMapping(selectedAgent.source_type);
        setActiveMapping(active);
        // Load active mapping into draft for editing
        if (active) {
          setDraftMapping(active);
        }

        // Load all mappings for this source type
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
  }, [selectedAgent]);

  // Load chunks when agent is selected
  useEffect(() => {
    async function loadChunks() {
      if (!selectedAgent) {
        setChunks([]);
        return;
      }
      setChunksLoading(true);
      try {
        const response = await mapperApi.listChunks({
          agent_id: selectedAgent.agent_id,
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
  }, [selectedAgent]);

  // Activate and load a mapping for editing
  const handleActivate = useCallback(async (mappingId: string) => {
    try {
      const updated = await mapperApi.activateMapping(mappingId);
      setActiveMapping(updated);
      // Load into draft for editing
      setDraftMapping(updated);
      // Refresh list
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

  // Load a mapping for viewing/editing without activating
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

  // Create new mapping from selected chunk
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
        {/* Toolbar */}
        <div className="flex items-center gap-3 px-4 py-2 bg-slate-800/50 border-b border-slate-700/50 shrink-0">
          {/* Application Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 uppercase tracking-wide">App:</span>
            <select
              value={selectedAppId || ""}
              onChange={(e) => {
                setSelectedAppId(e.target.value || null);
                setSelectedAgent(null);
                selectChunk(null);
              }}
              className="bg-slate-800 text-slate-200 px-3 py-1.5 rounded border border-slate-600 text-sm min-w-[180px]"
            >
              <option value="">All Applications</option>
              {applications.map((app) => (
                <option key={app.app_id} value={app.app_id}>
                  {app.name} ({app.agent_count})
                </option>
              ))}
            </select>
          </div>

          <div className="h-4 w-px bg-slate-600" />

          {/* Agent Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 uppercase tracking-wide">Agent:</span>
            <select
              value={selectedAgent?.agent_id || ""}
              onChange={(e) => {
                const agent = filteredAgents.find((a) => a.agent_id === e.target.value);
                setSelectedAgent(agent || null);
                selectChunk(null);
              }}
              className="bg-slate-800 text-slate-200 px-3 py-1.5 rounded border border-slate-600 text-sm min-w-[220px]"
            >
              <option value="">Select Agent...</option>
              {filteredAgents.map((agent) => (
                <option key={agent.agent_id} value={agent.agent_id}>
                  {agent.name} ({agent.source_type})
                </option>
              ))}
            </select>
          </div>

          <div className="flex-1" />

          {/* Active Mapping Status */}
          {selectedAgent && (
            <div className="flex items-center gap-2 text-sm">
              {activeMapping ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-emerald-400">
                    Active: {activeMapping.name}
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
                <span className="text-slate-500">No active mapping</span>
              )}
            </div>
          )}
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden min-h-0">
          {/* Left: Mappings List */}
          <section className="w-64 border-r border-slate-700/50 bg-slate-900 flex flex-col shrink-0">
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
                        : m.id === draftMapping?.id
                        ? "bg-blue-600/20 border border-blue-500/50 text-blue-200"
                        : "bg-slate-800/50 hover:bg-slate-700/50 text-slate-300",
                    ].join(" ")}
                  >
                    <div className="flex items-center gap-2">
                      {m.id === activeMapping?.id && (
                        <span className="w-2 h-2 rounded-full bg-emerald-500" />
                      )}
                      <span className="font-medium">{m.name}</span>
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {m.field_mappings?.length || 0} fields
                      {m.sample_chunk_id && (
                        <span className="text-blue-400 ml-2">
                          • from chunk
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

          {/* Center: Timeline & Raw Data */}
          <section className="flex-1 flex flex-col min-w-0">
            {/* Timeline */}
            <TimelineSlider
              chunks={chunks}
              selectedChunk={selectedChunk}
              onSelectChunk={selectChunk}
              loading={chunksLoading}
            />

            {/* Raw Data Preview */}
            <div className="flex-1 overflow-auto">
              {selectedChunk ? (
                <RawDataPanel
                  data={selectedChunk.data}
                  chunkId={selectedChunk.id}
                  onCreateMapping={handleNewMapping}
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

          {/* Right: Mapping Config */}
          <section className="w-80 bg-slate-900 flex flex-col border-l border-slate-700/50 shrink-0">
            <div className="px-3 py-2 border-b border-slate-700/50 bg-slate-800/30 shrink-0">
              <h2 className="text-sm font-semibold text-slate-300">
                {activeMapping ? `Edit: ${activeMapping.name}` : "New Mapping"}
              </h2>
            </div>
            <div className="flex-1 overflow-auto">
              <SchemaBrowser />
            </div>
            {draftMapping && (
              <div className="border-t border-slate-700/50 bg-slate-800/20 max-h-[50%] overflow-auto shrink-0">
                <MappingBuilder onSaved={refreshMappings} />
              </div>
            )}

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
        </div>
      </div>
    </DndProvider>
  );
}
