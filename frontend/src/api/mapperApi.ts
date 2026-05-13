import type {
  ApplyResponse,
  EdgePreset,
  EdgePresetCreate,
  EdgePresetListResponse,
  EdgePresetUpdate,
  MappingConfig,
  MappingListResponse,
  MappingTemplateInstantiateRequest,
  MappingTemplateListResponse,
  MockerCommandResponse,
  PreviewResponse,
  RawDataChunk,
  RawDataListResponse,
  RawDataSource,
} from '../types/mapper';
import client from './client';

export async function listChunks(params?: {
  agent_id?: string;
  source_type?: RawDataSource;
  limit?: number;
}): Promise<RawDataListResponse> {
  const res = await client.get('/receiver/raw', { params });
  return res.data;
}

export async function getChunk(chunkId: string): Promise<RawDataChunk> {
  const res = await client.get(`/receiver/raw/${chunkId}`);
  return res.data;
}

export async function deleteChunk(chunkId: string): Promise<void> {
  await client.delete(`/receiver/raw/${chunkId}`);
}

export async function pinChunk(chunkId: string): Promise<{ chunk_id: string; is_pinned: boolean }> {
  const res = await client.post(`/receiver/raw/${chunkId}/pin`);
  return res.data;
}

export async function unpinChunk(chunkId: string): Promise<{ chunk_id: string; is_pinned: boolean }> {
  const res = await client.post(`/receiver/raw/${chunkId}/unpin`);
  return res.data;
}

export async function listMappings(params?: {
  source_type?: string;
  is_active?: boolean;
  limit?: number;
}): Promise<MappingListResponse> {
  const res = await client.get('/mapper/', { params });
  return res.data;
}

export async function listMappingTemplates(): Promise<MappingTemplateListResponse> {
  const res = await client.get('/mapper/templates');
  return res.data;
}

export async function instantiateMappingTemplate(
  templateId: string,
  payload?: MappingTemplateInstantiateRequest,
): Promise<MappingConfig> {
  const res = await client.post(`/mapper/templates/${templateId}/instantiate`, payload ?? {});
  return res.data;
}

export async function getMapping(mappingId: string): Promise<MappingConfig> {
  const res = await client.get(`/mapper/${mappingId}`);
  return res.data;
}

export async function createMapping(config: Partial<MappingConfig>): Promise<MappingConfig> {
  const res = await client.post('/mapper/', config);
  return res.data;
}

export async function updateMapping(mappingId: string, config: Partial<MappingConfig>): Promise<MappingConfig> {
  const res = await client.put(`/mapper/${mappingId}`, config);
  return res.data;
}

export async function deleteMapping(mappingId: string): Promise<void> {
  await client.delete(`/mapper/${mappingId}`);
}

export async function activateMapping(mappingId: string): Promise<MappingConfig> {
  const res = await client.post(`/mapper/${mappingId}/activate`);
  return res.data;
}

export async function deactivateMapping(mappingId: string): Promise<MappingConfig> {
  const res = await client.post(`/mapper/${mappingId}/deactivate`);
  return res.data;
}

export async function deactivateAndClearMapping(mappingId: string): Promise<{
  mapping_id: string;
  source_type: string;
  deactivated: boolean;
  sources: string[];
  deleted_nodes: number;
  deleted_edges: number;
}> {
  const res = await client.post(`/mapper/${mappingId}/deactivate-and-clear`);
  return res.data;
}

export async function getActiveMapping(sourceType: string): Promise<MappingConfig | null> {
  const res = await client.get(`/mapper/active/${sourceType}`);
  return res.data;
}

export async function replayMapping(
  mappingId: string,
  params?: {
    agent_id?: string;
    from_timestamp?: string;
    to_timestamp?: string;
  },
): Promise<{
  chunks_processed: number;
  nodes_created: number;
  edges_created: number;
  errors: string[];
}> {
  const res = await client.post(`/mapper/${mappingId}/replay`, params ?? {});
  return res.data;
}

export async function preview(chunkId: string, mappingId: string): Promise<PreviewResponse> {
  const res = await client.post('/mapper/preview', {
    chunk_id: chunkId,
    mapping_id: mappingId,
  });
  return res.data;
}

export async function apply(chunkId: string, mappingId: string): Promise<ApplyResponse> {
  const res = await client.post('/mapper/apply', {
    chunk_id: chunkId,
    mapping_id: mappingId,
  });
  return res.data;
}

export async function previewRaw(rawData: Record<string, unknown>, mappingId: string): Promise<PreviewResponse> {
  const res = await client.post(`/mapper/preview-raw?mapping_id=${mappingId}`, rawData);
  return res.data;
}

export async function listEdgePresets(): Promise<EdgePresetListResponse> {
  const res = await client.get('/edge-presets');
  return res.data;
}

export async function getEdgePreset(presetId: string): Promise<EdgePreset> {
  const res = await client.get(`/edge-presets/${presetId}`);
  return res.data;
}

export async function createEdgePreset(data: EdgePresetCreate): Promise<EdgePreset> {
  const res = await client.post('/edge-presets', data);
  return res.data;
}

export async function updateEdgePreset(presetId: string, data: EdgePresetUpdate): Promise<EdgePreset> {
  const res = await client.put(`/edge-presets/${presetId}`, data);
  return res.data;
}

export async function deleteEdgePreset(presetId: string): Promise<void> {
  await client.delete(`/edge-presets/${presetId}`);
}

export async function runMockerFull(): Promise<MockerCommandResponse> {
  const res = await client.post('/mocker/run-full', undefined, { timeout: 10 * 60 * 1000 });
  return res.data;
}

export async function createMappingsFromMocker(): Promise<MockerCommandResponse> {
  const res = await client.post('/mocker/create-mappings', undefined, { timeout: 10 * 60 * 1000 });
  return res.data;
}

export const mapperApi = {
  listChunks,
  getChunk,
  deleteChunk,
  pinChunk,
  unpinChunk,
  listMappings,
  listMappingTemplates,
  instantiateMappingTemplate,
  getMapping,
  createMapping,
  updateMapping,
  deleteMapping,
  activateMapping,
  deactivateMapping,
  deactivateAndClearMapping,
  getActiveMapping,
  replayMapping,
  preview,
  apply,
  previewRaw,
  listEdgePresets,
  getEdgePreset,
  createEdgePreset,
  updateEdgePreset,
  deleteEdgePreset,
  runMockerFull,
  createMappingsFromMocker,
};
