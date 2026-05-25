import type { AgentInfo, AgentRegisterRequest, AgentRegisterResponse } from '../types';
import client from './client';

const BASE = '/agents';

export async function registerAgent(body: AgentRegisterRequest): Promise<AgentRegisterResponse> {
  const { data } = await client.post<AgentRegisterResponse>(`${BASE}/register`, body);
  return data;
}

export async function fetchAgents(): Promise<AgentInfo[]> {
  const { data } = await client.get<AgentInfo[]>(`${BASE}/`);
  return data;
}

export async function deleteAgent(agentId: string): Promise<void> {
  await client.delete(`${BASE}/${agentId}`);
}
