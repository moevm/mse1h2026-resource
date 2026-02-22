import axios from "axios";
import type { HealthResponse } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export async function fetchHealth(): Promise<HealthResponse> {
    const { data } = await axios.get<HealthResponse>(`${API_BASE}/health`, {
        timeout: 5_000,
    });
    return data;
}

export * from "./graphApi";
export * from "./agentsApi";
export * from "./ingestApi";
