export interface AgentRegisterRequest {
  name: string;
  description?: string;
  token?: string;
  app_token?: string;
}

export interface AgentRegisterResponse {
  agent_id: string;
  token: string;
  name: string;
  registered_at: string;
}

export interface AgentInfo {
  agent_id: string;
  name: string;
  description?: string;
  registered_at?: string;
  last_seen_at?: string;
  app_id?: string;
  app_name?: string;
}
