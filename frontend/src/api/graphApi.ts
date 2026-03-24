import client from "./client";
import type {
    GraphResponse,
    GraphStats,
    GraphAnalytics,
    LayoutGraphResponse,
    SubgraphRequest,
    PathRequest,
    ImpactRequest,
    ExportRequest,
    ExportFormat,
    ExportFormatInfo,
    TraversalRule,
    TraversalPreset,
} from "../types";

interface ExportFormatApiItem {
    id: ExportFormat;
    name: string;
    description: string;
    extension: string;
}

const BASE = "/graph";

export async function fetchFullGraph(limit = 500, appId?: string): Promise<GraphResponse> {
    const params: Record<string, unknown> = { limit };
    if (appId) {
        params.app_id = appId;
    }
    const { data } = await client.get<GraphResponse>(`${BASE}/full`, { params });
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

export async function fetchLayout(limit = 500, layout = "spring"): Promise<LayoutGraphResponse> {
    const { data } = await client.get<LayoutGraphResponse>(`${BASE}/layout`, {
        params: { limit, layout },
    });
    return data;
}

const EXPORT_BASE = "/export";

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
        responseType: "blob",
    });
    return data;
}

const TRAVERSAL_BASE = "/traversal";

export async function fetchTraversalPresets(): Promise<TraversalPreset[]> {
    const { data } = await client.get<TraversalPreset[]>(`${TRAVERSAL_BASE}/presets`);
    return data;
}

export async function executeTraversal(body: TraversalRule): Promise<GraphResponse> {
    const { data } = await client.post<GraphResponse>(`${TRAVERSAL_BASE}/execute`, body);
    return data;
}
