import client from "./client";
import type {
    ApplicationInfo,
    ApplicationDetail,
    ApplicationRegisterRequest,
    ApplicationRegisterResponse,
} from "../types/application";

const BASE = "/apps";

export async function registerApplication(
    body: ApplicationRegisterRequest
): Promise<ApplicationRegisterResponse> {
    const { data } = await client.post<ApplicationRegisterResponse>(`${BASE}/register`, body);
    return data;
}

export async function fetchApplications(): Promise<ApplicationInfo[]> {
    const { data } = await client.get<ApplicationInfo[]>(`${BASE}/`);
    return data;
}

export async function fetchApplication(appId: string): Promise<ApplicationDetail> {
    const { data } = await client.get<ApplicationDetail>(`${BASE}/${appId}`);
    return data;
}
