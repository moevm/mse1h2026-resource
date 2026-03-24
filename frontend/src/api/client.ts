import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

const client = axios.create({
    baseURL: `${API_BASE}/api/v1`,
    headers: { "Content-Type": "application/json" },
    timeout: 30_000,
});

client.interceptors.request.use((config) => {
    (config as { metadata?: { startedAt: number } }).metadata = {
        startedAt: Date.now(),
    };

    if (import.meta.env.DEV) {
        console.debug(
            `[API] ${String(config.method).toUpperCase()} ${config.baseURL ?? ""}${config.url ?? ""}`,
        );
    }
    return config;
});

client.interceptors.response.use(
    (res) => {
        if (import.meta.env.DEV) {
            const metadata = (res.config as { metadata?: { startedAt: number } }).metadata;
            const duration = metadata ? Date.now() - metadata.startedAt : null;
            console.debug(
                `[API] ${res.status} ${String(res.config.method).toUpperCase()} ${res.config.url ?? ""}${
                    duration == null ? "" : ` (${duration}ms)`
                }`,
            );
        }
        return res;
    },
    (err: unknown) => {
        if (!axios.isAxiosError(err)) {
            return Promise.reject(err instanceof Error ? err : new Error("Unknown API error"));
        }

        const status = err.response?.status;
        const detail =
            (err.response?.data as { detail?: string } | undefined)?.detail ??
            err.message ??
            "Unknown error";

        let message = detail;
        if (err.code === "ECONNABORTED") {
            message = "Request timed out. Please try again.";
        } else if (!err.response) {
            message = "Network error. Please check your connection.";
        }

        console.error(`[API] Error ${String(status ?? "network")}: ${message}`);
        return Promise.reject(new Error(message));
    },
);

export default client;
