import { useState, useEffect, useCallback } from "react";
import { fetchApplications, registerApplication } from "../api/applicationsApi";
import type { ApplicationInfo, ApplicationRegisterRequest, ApplicationRegisterResponse } from "../types/application";

export function useApplications() {
    const [applications, setApplications] = useState<ApplicationInfo[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const data = await fetchApplications();
            setApplications(data);
            setError(null);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to load applications");
        } finally {
            setLoading(false);
        }
    }, []);

    const register = useCallback(
        async (req: ApplicationRegisterRequest): Promise<ApplicationRegisterResponse> => {
            setLoading(true);
            try {
                const res = await registerApplication(req);
                await load();
                return res;
            } catch (e: unknown) {
                setError(e instanceof Error ? e.message : "Failed to register application");
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

    return { applications, loading, error, reload: load, register };
}
