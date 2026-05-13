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

export async function fetchSnapshotStats(atTime: string): Promise<SnapshotStats> {
  const { data } = await client.get<SnapshotStats>(`${BASE}/snapshot-stats`, {
    params: { at_time: atTime },
  });
  return data;
}
