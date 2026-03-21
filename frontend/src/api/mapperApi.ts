import client from "./client";
import type {
  RawDataChunk,
  RawDataListResponse,
  RawDataSource,
  MappingConfig,
  MappingListResponse,
  PreviewResponse,
  ApplyResponse,
  EdgePreset,
  EdgePresetCreate,
  EdgePresetUpdate,
  EdgePresetListResponse,
} from "../types/mapper";

export const mapperApi = {
  // Raw Data endpoints
  async listChunks(params?: {
    agent_id?: string;
    source_type?: RawDataSource;
    limit?: number;
  }): Promise<RawDataListResponse> {
    const res = await client.get("/receiver/raw", { params });
    return res.data;
  },

  async getChunk(chunkId: string): Promise<RawDataChunk> {
    const res = await client.get(`/receiver/raw/${chunkId}`);
    return res.data;
  },

  async deleteChunk(chunkId: string): Promise<void> {
    await client.delete(`/receiver/raw/${chunkId}`);
  },

  // Mapping CRUD
  async listMappings(params?: {
    source_type?: string;
    is_active?: boolean;
    limit?: number;
  }): Promise<MappingListResponse> {
    const res = await client.get("/mapper/", { params });
    return res.data;
  },

  async getMapping(mappingId: string): Promise<MappingConfig> {
    const res = await client.get(`/mapper/${mappingId}`);
    return res.data;
  },

  async createMapping(config: Partial<MappingConfig>): Promise<MappingConfig> {
    const res = await client.post("/mapper/", config);
    return res.data;
  },

  async updateMapping(
    mappingId: string,
    config: Partial<MappingConfig>
  ): Promise<MappingConfig> {
    const res = await client.put(`/mapper/${mappingId}`, config);
    return res.data;
  },

  async deleteMapping(mappingId: string): Promise<void> {
    await client.delete(`/mapper/${mappingId}`);
  },

  async activateMapping(mappingId: string): Promise<MappingConfig> {
    const res = await client.post(`/mapper/${mappingId}/activate`);
    return res.data;
  },

  async deactivateMapping(mappingId: string): Promise<MappingConfig> {
    const res = await client.post(`/mapper/${mappingId}/deactivate`);
    return res.data;
  },

  async deactivateAndClearMapping(mappingId: string): Promise<{
    mapping_id: string;
    source_type: string;
    deactivated: boolean;
    sources: string[];
    deleted_nodes: number;
    deleted_edges: number;
  }> {
    const res = await client.post(`/mapper/${mappingId}/deactivate-and-clear`);
    return res.data;
  },

  async getActiveMapping(sourceType: string): Promise<MappingConfig | null> {
    const res = await client.get(`/mapper/active/${sourceType}`);
    return res.data;
  },

  async replayMapping(
    mappingId: string,
    params?: {
      agent_id?: string;
      from_timestamp?: string;
      to_timestamp?: string;
    }
  ): Promise<{
    chunks_processed: number;
    nodes_created: number;
    edges_created: number;
    errors: string[];
  }> {
    const res = await client.post(`/mapper/${mappingId}/replay`, params || {});
    return res.data;
  },

  // Preview & Apply
  async preview(chunkId: string, mappingId: string): Promise<PreviewResponse> {
    const res = await client.post("/mapper/preview", {
      chunk_id: chunkId,
      mapping_id: mappingId,
    });
    return res.data;
  },

  async apply(chunkId: string, mappingId: string): Promise<ApplyResponse> {
    const res = await client.post("/mapper/apply", {
      chunk_id: chunkId,
      mapping_id: mappingId,
    });
    return res.data;
  },

  async previewRaw(
    rawData: Record<string, unknown>,
    mappingId: string
  ): Promise<PreviewResponse> {
    const res = await client.post(`/mapper/preview-raw?mapping_id=${mappingId}`, rawData);
    return res.data;
  },

  // Edge Presets
  async listEdgePresets(): Promise<EdgePresetListResponse> {
    const res = await client.get("/edge-presets");
    return res.data;
  },

  async getEdgePreset(presetId: string): Promise<EdgePreset> {
    const res = await client.get(`/edge-presets/${presetId}`);
    return res.data;
  },

  async createEdgePreset(data: EdgePresetCreate): Promise<EdgePreset> {
    const res = await client.post("/edge-presets", data);
    return res.data;
  },

  async updateEdgePreset(
    presetId: string,
    data: EdgePresetUpdate
  ): Promise<EdgePreset> {
    const res = await client.put(`/edge-presets/${presetId}`, data);
    return res.data;
  },

  async deleteEdgePreset(presetId: string): Promise<void> {
    await client.delete(`/edge-presets/${presetId}`);
  },
};
