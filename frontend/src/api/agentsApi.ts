import client from "./client";
import type { AgentInfo, AgentRegisterRequest, AgentRegisterResponse } from "../types";

const BASE = "/agents";

export async function registerAgent(body: AgentRegisterRequest): Promise<AgentRegisterResponse> {
    const { data } = await client.post<AgentRegisterResponse>(`${BASE}/register`, body);
    return data;
}

export async function fetchAgents(): Promise<AgentInfo[]> {
    const { data } = await client.get<AgentInfo[]>(`${BASE}/`);
    return data;
}
