import type {
  ExportFormat,
  ExportFormatInfo,
  ExportRequest,
  GraphAnalytics,
  GraphResponse,
  GraphStats,
  HealthResponse,
  ImpactRequest,
  LayoutGraphResponse,
  PathRequest,
  SubgraphRequest,
  TraversalPreset,
  TraversalRule,
} from '../types';
import client from './client';

interface ExportFormatApiItem {
  id: ExportFormat;
  name: string;
  description: string;
  extension: string;
}

const BASE = '/graph';

export interface GraphFetchOptions {
  appId?: string;
  asOf?: string;
  windowStart?: string;
  windowEnd?: string;
}

export async function fetchFullGraph(
  limit = 500,
  appIdOrOpts?: string | GraphFetchOptions,
  asOf?: string,
): Promise<GraphResponse> {
  let opts: GraphFetchOptions;
  if (typeof appIdOrOpts === 'object' && appIdOrOpts !== null) {
    opts = appIdOrOpts;
  } else {
    opts = { appId: appIdOrOpts, asOf };
  }

  const params: Record<string, unknown> = { limit };
  if (opts.appId) params.app_id = opts.appId;
  if (opts.asOf) params.as_of = opts.asOf;
  if (opts.windowStart) params.window_start = opts.windowStart;
  if (opts.windowEnd) params.window_end = opts.windowEnd;
  const { data } = await client.get<GraphResponse>(`${BASE}/full`, { params });
  return data;
}

export interface TimelineRange {
  min_time: string | null;
  max_time: string | null;
  total_nodes: number;
  total_edges: number;
}

export async function fetchTimelineRange(): Promise<TimelineRange> {
  const { data } = await client.get<TimelineRange>('/timeline/range');
  return data;
}

export async function fetchSubgraph(body: SubgraphRequest): Promise<GraphResponse> {
  const { data } = await client.post<GraphResponse>(`${BASE}/subgraph`, body);
  return data;
}

export async function fetchShortestPath(body: PathRequest): Promise<GraphResponse> {
  const { data } = await client.post<GraphResponse>(`${BASE}/path`, body);
  return data;
}

export async function fetchImpact(body: ImpactRequest): Promise<GraphResponse> {
  const { data } = await client.post<GraphResponse>(`${BASE}/impact`, body);
  return data;
}

export async function fetchStats(): Promise<GraphStats> {
  const { data } = await client.get<GraphStats>(`${BASE}/stats`);
  return data;
}

export async function fetchAnalytics(limit = 1000): Promise<GraphAnalytics> {
  const { data } = await client.get<GraphAnalytics>(`${BASE}/analytics`, {
    params: { limit },
  });
  return data;
}

export async function fetchLayout(limit = 500, layout = 'spring'): Promise<LayoutGraphResponse> {
  const { data } = await client.get<LayoutGraphResponse>(`${BASE}/layout`, {
    params: { limit, layout },
  });
  return data;
}

const EXPORT_BASE = '/export';

export async function fetchExportFormats(): Promise<ExportFormatInfo[]> {
  const { data } = await client.get<ExportFormatApiItem[]>(`${EXPORT_BASE}/formats`);
  return data.map((item) => ({
    format: item.id,
    label: item.name,
    description: item.description,
    extension: item.extension,
  }));
}

export async function downloadExport(body: ExportRequest): Promise<Blob> {
  const { data } = await client.post(`${EXPORT_BASE}/download`, body, {
    responseType: 'blob',
  });
  return data;
}

const TRAVERSAL_BASE = '/traversal';

export async function fetchTraversalPresets(): Promise<TraversalPreset[]> {
  const { data } = await client.get<TraversalPreset[]>(`${TRAVERSAL_BASE}/presets`);
  return data;
}

export interface TraversalExecuteOptions {
  appId?: string | null;
}

export async function executeTraversal(
  body: TraversalRule,
  options: TraversalExecuteOptions = {},
): Promise<GraphResponse> {
  const params = options.appId ? { app_id: options.appId } : undefined;
  const { data } = await client.post<GraphResponse>(`${TRAVERSAL_BASE}/execute`, body, { params });
  return data;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await client.get<HealthResponse>('/health');
  return data;
}
