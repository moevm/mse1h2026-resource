import client from './client';

const BASE = '/timeline';

export interface TimelineEvent {
  timestamp: string;
  nodes_added: number;
  edges_added: number;
  node_types: Record<string, number>;
  running_total_nodes: number;
  running_total_edges: number;
}

export interface TimelineEventsResponse {
  events: TimelineEvent[];
  min_time: string | null;
  max_time: string | null;
}

export interface SnapshotStats {
  at_time: string;
  total_nodes: number;
  total_edges: number;
  nodes_by_type: Record<string, number>;
  edges_by_type: Record<string, number>;
}

export async function fetchTimelineEvents(
  bucketSeconds = 30,
  fromTime?: string,
  toTime?: string,
): Promise<TimelineEventsResponse> {
  const params: Record<string, unknown> = { bucket_seconds: bucketSeconds };
  if (fromTime) params.from_time = fromTime;
  if (toTime) params.to_time = toTime;
  const { data } = await client.get<TimelineEventsResponse>(`${BASE}/events`, { params });
  return data;
}

export interface TraceActivityBucket {
  bucket_ts: number;
  timestamp: string;
  span_count: number;
  error_count: number;
}

export interface TraceActivityResponse {
  buckets: TraceActivityBucket[];
  bucket_seconds: number;
}

export async function fetchTraceActivity(
  bucketSeconds = 30,
  fromTime?: string,
  toTime?: string,
): Promise<TraceActivityResponse> {
  const params: Record<string, unknown> = { bucket_seconds: bucketSeconds };
  if (fromTime) params.from_time = fromTime;
  if (toTime) params.to_time = toTime;
  const { data } = await client.get<TraceActivityResponse>(`${BASE}/trace-activity`, { params });
  return data;
}

export interface TraceReplayHop {
  caller_service: string;
  callee_service: string;
  callee_kind?: string;
  span_name: string;
  start_offset_ms: number;
  duration_ms: number;
  is_error: boolean;
}

export interface TraceReplayResponse {
  trace_id: string | null;
  hops: TraceReplayHop[];
}

export async function fetchLatestTraceReplay(
  lookbackSeconds = 300,
  excludeTraceId?: string,
): Promise<TraceReplayResponse> {
  const params: Record<string, unknown> = { lookback_seconds: lookbackSeconds };
  if (excludeTraceId) params.exclude_trace_id = excludeTraceId;
  const { data } = await client.get<TraceReplayResponse>(`${BASE}/trace-replay/latest`, { params });
  return data;
}

export async function fetchTraceReplayById(traceId: string): Promise<TraceReplayResponse> {
  const { data } = await client.get<TraceReplayResponse>(`${BASE}/trace-replay/${traceId}`);
  return data;
}

export interface TraceSummary {
  trace_id: string;
  root_service: string;
  root_name: string;
  start_time: string | null;
  duration_ms: number;
  hop_count: number;
  service_count: number;
  services_involved: string[];
  has_errors: boolean;
}

export interface TracesListResponse {
  traces: TraceSummary[];
  window_start: number;
  window_end: number;
}

export async function fetchTracesList(opts: {
  windowStart?: string;
  windowEnd?: string;
  limit?: number;
  services?: string[];
  multiHop?: boolean;
}): Promise<TracesListResponse> {
  const params: Record<string, unknown> = {};
  if (opts.windowStart) params.window_start = opts.windowStart;
  if (opts.windowEnd) params.window_end = opts.windowEnd;
  if (opts.limit !== undefined) params.limit = opts.limit;
  if (opts.services && opts.services.length > 0) params.services = opts.services.join(',');
  if (opts.multiHop !== undefined) params.multi_hop = opts.multiHop;
  const { data } = await client.get<TracesListResponse>(`${BASE}/traces`, { params });
  return data;
}

export async function fetchSnapshotStats(atTime: string): Promise<SnapshotStats> {
  const { data } = await client.get<SnapshotStats>(`${BASE}/snapshot-stats`, {
    params: { at_time: atTime },
  });
  return data;
}
