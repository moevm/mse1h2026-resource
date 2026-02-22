import { useState, useEffect, useCallback } from "react";
import { fetchAgents, registerAgent } from "../api";
import type { AgentInfo, AgentRegisterRequest } from "../types";

export function useAgents() {
    const [agents, setAgents] = useState<AgentInfo[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const data = await fetchAgents();
            setAgents(data);
            setError(null);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to load agents");
        } finally {
            setLoading(false);
        }
    }, []);

    const register = useCallback(
        async (req: AgentRegisterRequest) => {
            setLoading(true);
            try {
                const res = await registerAgent(req);
                await load();
                return res;
            } catch (e: unknown) {
                setError(e instanceof Error ? e.message : "Failed to register agent");
                throw e;
            } finally {
                setLoading(false);
            }
        },
        [load],
    );

    useEffect(() => {
        void load();
    }, [load]);

    return { agents, loading, error, reload: load, register };
}
