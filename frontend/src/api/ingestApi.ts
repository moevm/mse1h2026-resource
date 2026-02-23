import client from "./client";
import type { IngestTopologyRequest, IngestResult } from "../types";

const BASE = "/ingest";

export async function sendTopologyUpdate(
    body: IngestTopologyRequest,
    agentToken: string,
): Promise<IngestResult> {
    const { data } = await client.post<IngestResult>(`${BASE}/topology`, body, {
        headers: { "X-Agent-Token": agentToken },
    });
    return data;
}
