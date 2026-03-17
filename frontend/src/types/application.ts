export interface ApplicationRegisterRequest {
    name: string;
    description?: string;
    owner?: string;
}

export interface ApplicationRegisterResponse {
    app_id: string;
    app_token: string;
    name: string;
    description?: string;
    owner?: string;
    created_at: string;
}

export interface ApplicationInfo {
    app_id: string;
    name: string;
    description?: string;
    owner?: string;
    created_at?: string;
    agent_count: number;
}

import type { AgentInfo } from "./agent";

export interface ApplicationDetail extends ApplicationInfo {
    agents: AgentInfo[];
}
