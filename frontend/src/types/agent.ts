export interface AgentRegisterRequest {
    name: string;
    source_type: string;
    description?: string;
}

export interface AgentRegisterResponse {
    agent_id: string;
    token: string;
    name: string;
    source_type: string;
    registered_at: string;
}

export interface AgentInfo {
    agent_id: string;
    name: string;
    source_type: string;
    description?: string;
    registered_at?: string;
    last_seen_at?: string;
}
