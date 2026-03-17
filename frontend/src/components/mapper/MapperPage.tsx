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
    setChunks,
    selectChunk,
    setChunksLoading,
    setDraftMapping,
  } = useMapperStore();

  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);

  const [activeMapping, setActiveMapping] = useState<MappingConfig | null>(null);
  const [availableMappings, setAvailableMappings] = useState<MappingConfig[]>([]);
  const [mappingsLoading, setMappingsLoading] = useState(false);

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

  // Deactivate current mapping
  const handleDeactivate = useCallback(async () => {
    if (!activeMapping) return;
    try {
      await mapperApi.deactivateMapping(activeMapping.id);
      setActiveMapping(null);
    } catch (error) {
      console.error("Failed to deactivate mapping:", error);
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
  }, [selectedAgent, selectedChunk, setDraftMapping]);

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
                    onClick={handleDeactivate}
                    className="text-slate-400 hover:text-slate-200 text-xs underline"
                  >
                    Deactivate
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
                <MappingBuilder />
              </div>
            )}
          </section>
        </div>
      </div>
    </DndProvider>
  );
}
