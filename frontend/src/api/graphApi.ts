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
    ExportFormatInfo,
    TraversalRule,
    TraversalPreset,
} from "../types";

const BASE = "/graph";

export async function fetchFullGraph(limit = 500): Promise<GraphResponse> {
    const { data } = await client.get<GraphResponse>(`${BASE}/full`, {
        params: { limit },
    });
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
    const { data } = await client.get<ExportFormatInfo[]>(`${EXPORT_BASE}/formats`);
    return data;
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
