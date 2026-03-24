import { useCallback } from "react";
import { fetchApplications, registerApplication } from "../api/applicationsApi";
import type { ApplicationInfo, ApplicationRegisterRequest, ApplicationRegisterResponse } from "../types/application";
import { useResource } from "../shared/hooks/useResource";

export function useApplications() {
    const fetcher = useCallback(() => fetchApplications(), []);
    const creator = useCallback((req: ApplicationRegisterRequest) => registerApplication(req), []);

    const { items, loading, error, reload, create } = useResource<
        ApplicationInfo,
        ApplicationRegisterRequest,
        ApplicationRegisterResponse
    >({
        fetcher,
        creator,
        loadErrorMessage: "Failed to load applications",
        createErrorMessage: "Failed to register application",
    });

    return { applications: items, loading, error, reload, register: create };
}
