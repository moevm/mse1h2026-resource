import { create } from "zustand";
import type {
  RawDataChunk,
  MappingConfig,
  FieldMapping,
  RawDataSource,
  UnresolvedReference,
} from "../types/mapper";
import { mapperApi } from "../api/mapperApi";

export interface MapperState {
  // Raw data
  chunks: RawDataChunk[];
  selectedChunk: RawDataChunk | null;
  chunksLoading: boolean;

  // Mappings
  mappings: MappingConfig[];
  selectedMapping: MappingConfig | null;
  mappingsLoading: boolean;

  // Draft mapping being edited
  draftMapping: Partial<MappingConfig> | null;

  // Preview
  previewNodes: Record<string, unknown>[];
  previewEdges: Record<string, unknown>[];
  previewWarnings: string[];
  unresolvedReferences: UnresolvedReference[];
  previewLoading: boolean;

  // UI State
  selectedSourceType: RawDataSource | null;
  expandedJsonPaths: Set<string>;
  selectedFieldPath: string | null;
  activeNodeTypes: Set<string>;

  // Actions
  setChunks: (chunks: RawDataChunk[]) => void;
  selectChunk: (chunk: RawDataChunk | null) => void;
  setChunksLoading: (loading: boolean) => void;

  setMappings: (mappings: MappingConfig[]) => void;
  selectMapping: (mapping: MappingConfig | null) => void;
  setMappingsLoading: (loading: boolean) => void;

  setDraftMapping: (mapping: Partial<MappingConfig> | null) => void;
  updateDraftMapping: (updates: Partial<MappingConfig>) => void;
  addFieldMapping: (mapping: FieldMapping) => void;
  updateFieldMapping: (id: string, updates: Partial<FieldMapping>) => void;
  removeFieldMapping: (id: string) => void;
  saveDraftMapping: () => Promise<void>;

  setPreview: (
    nodes: Record<string, unknown>[],
    edges: Record<string, unknown>[],
    warnings: string[],
    unresolvedReferences: UnresolvedReference[]
  ) => void;
  setPreviewLoading: (loading: boolean) => void;
  clearPreview: () => void;

  setSelectedSourceType: (sourceType: RawDataSource | null) => void;
  toggleJsonPath: (path: string) => void;
  expandAllPaths: () => void;
  collapseAllPaths: () => void;
  setSelectedFieldPath: (path: string | null) => void;
  toggleActiveNodeType: (type: string) => void;

  reset: () => void;
}

const initialState = {
  chunks: [] as RawDataChunk[],
  selectedChunk: null,
  chunksLoading: false,

  mappings: [] as MappingConfig[],
  selectedMapping: null,
  mappingsLoading: false,

  draftMapping: null as Partial<MappingConfig> | null,

  previewNodes: [] as Record<string, unknown>[],
  previewEdges: [] as Record<string, unknown>[],
  previewWarnings: [] as string[],
  unresolvedReferences: [] as UnresolvedReference[],
  previewLoading: false,

  selectedSourceType: null as RawDataSource | null,
  expandedJsonPaths: new Set<string>(),
  selectedFieldPath: null,
  activeNodeTypes: new Set<string>(["Service"]),
};

export const useMapperStore = create<MapperState>((set) => ({
  ...initialState,

  setChunks: (chunks) => set({ chunks }),
  selectChunk: (chunk) => set({ selectedChunk: chunk }),
  setChunksLoading: (loading) => set({ chunksLoading: loading }),

  setMappings: (mappings) => set({ mappings }),
  selectMapping: (mapping) => set({ selectedMapping: mapping }),
  setMappingsLoading: (loading) => set({ mappingsLoading: loading }),

  setDraftMapping: (mapping) => set({ draftMapping: mapping }),
  updateDraftMapping: (updates) =>
    set((state) => ({
      draftMapping: { ...state.draftMapping, ...updates },
    })),

  addFieldMapping: (mapping) =>
    set((state) => ({
      draftMapping: {
        ...state.draftMapping,
        field_mappings: [...(state.draftMapping?.field_mappings || []), mapping],
      },
    })),

  updateFieldMapping: (id, updates) =>
    set((state) => ({
      draftMapping: {
        ...state.draftMapping,
        field_mappings:
          state.draftMapping?.field_mappings?.map((fm) =>
            fm.id === id ? { ...fm, ...updates } : fm
          ) || [],
      },
    })),

  removeFieldMapping: (id) =>
    set((state) => ({
      draftMapping: {
        ...state.draftMapping,
        field_mappings:
          state.draftMapping?.field_mappings?.filter((fm) => fm.id !== id) || [],
      },
    })),

  saveDraftMapping: async () => {
    const state = useMapperStore.getState();
    const draft = state.draftMapping;
    if (!draft) return;

    try {
      if (draft.id) {
        // Update existing
        const updated = await mapperApi.updateMapping(draft.id, draft as MappingConfig);
        set({ draftMapping: updated, selectedMapping: updated });
      } else {
        // Create new
        const generatedId =
          typeof crypto !== "undefined" && "randomUUID" in crypto
            ? crypto.randomUUID()
            : `mapping-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

        const createPayload: Partial<MappingConfig> = {
          id: generatedId,
          name: draft.name || "New Mapping",
          source_type: draft.source_type || "custom",
          version: draft.version || "1.0.0",
          is_active: draft.is_active ?? false,
          created_by: draft.created_by || "ui",
          description: draft.description ?? null,
          sample_chunk_id: draft.sample_chunk_id ?? null,
          field_mappings: draft.field_mappings || [],
          conditional_rules: draft.conditional_rules || [],
          auto_edge_rules: draft.auto_edge_rules || [],
          edge_preset_id: draft.edge_preset_id ?? "default",
          edge_source_path: draft.edge_source_path ?? null,
          edge_target_path: draft.edge_target_path ?? null,
          edge_type_path: draft.edge_type_path ?? null,
          edge_type_default: draft.edge_type_default ?? "dependson",
        };

        const created = await mapperApi.createMapping(createPayload);
        set({ draftMapping: created, selectedMapping: created });
      }
    } catch (error) {
      console.error("Failed to save mapping:", error);
      throw error;
    }
  },

  setPreview: (nodes, edges, warnings, unresolvedReferences) =>
    set({
      previewNodes: nodes,
      previewEdges: edges,
      previewWarnings: warnings,
      unresolvedReferences,
    }),

  setPreviewLoading: (loading) => set({ previewLoading: loading }),
  clearPreview: () =>
    set({
      previewNodes: [],
      previewEdges: [],
      previewWarnings: [],
      unresolvedReferences: [],
    }),

  setSelectedSourceType: (sourceType) => set({ selectedSourceType: sourceType }),

  toggleJsonPath: (path) =>
    set((state) => {
      const next = new Set(state.expandedJsonPaths);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return { expandedJsonPaths: next };
    }),

  expandAllPaths: () => {
    // Get all paths from selected chunk data
    const state = useMapperStore.getState();
    const data = state.selectedChunk?.data;
    if (!data) return;

    const allPaths = new Set<string>();
    const collectPaths = (obj: unknown, prefix: string = "") => {
      if (typeof obj !== "object" || obj === null) return;
      if (Array.isArray(obj)) {
        allPaths.add(prefix);
        obj.forEach((item, index) => {
          collectPaths(item, `${prefix}[${index}]`);
        });
      } else {
        allPaths.add(prefix);
        Object.entries(obj as Record<string, unknown>).forEach(([key, value]) => {
          const path = prefix ? `${prefix}.${key}` : key;
          collectPaths(value, path);
        });
      }
    };
    collectPaths(data);
    set({ expandedJsonPaths: allPaths });
  },

  collapseAllPaths: () => set({ expandedJsonPaths: new Set<string>() }),

  setSelectedFieldPath: (path) => set({ selectedFieldPath: path }),

  toggleActiveNodeType: (type) =>
    set((state) => {
      const next = new Set(state.activeNodeTypes);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return { activeNodeTypes: next };
    }),

  reset: () => set(initialState),
}));
