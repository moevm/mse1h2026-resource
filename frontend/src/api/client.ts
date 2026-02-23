import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

const client = axios.create({
    baseURL: `${API_BASE}/api/v1`,
    headers: { "Content-Type": "application/json" },
    timeout: 30_000,
});

client.interceptors.request.use((config) => {
    return config;
});

client.interceptors.response.use(
    (res) => {
        return res;
    },
    (err: unknown) => {
        const axErr = err as {
            response?: { status?: number; data?: { detail?: string } };
            message?: string;
        };
        const status = axErr?.response?.status;
        const detail = axErr?.response?.data?.detail;
        const msg = detail ?? axErr?.message ?? "Unknown error";
        console.error(`[API] Error ${String(status)}: ${msg}`);
        return Promise.reject(err instanceof Error ? err : new Error(msg));
    },
);

export default client;
