import { useCallback } from "react";
import { fetchAgents, registerAgent } from "../api";
import type { AgentInfo, AgentRegisterRequest } from "../types";
import { useResource } from "../shared/hooks/useResource";

export function useAgents() {
    const fetcher = useCallback(() => fetchAgents(), []);
    const creator = useCallback((req: AgentRegisterRequest) => registerAgent(req), []);

    const { items, loading, error, reload, create } = useResource<
        AgentInfo,
        AgentRegisterRequest,
        Awaited<ReturnType<typeof registerAgent>>
    >({
        fetcher,
        creator,
        loadErrorMessage: "Failed to load agents",
        createErrorMessage: "Failed to register agent",
    });

    return { agents: items, loading, error, reload, register: create };
}
