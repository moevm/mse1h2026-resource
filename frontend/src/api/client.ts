import axios from 'axios';

import { useAuthStore } from '../store/authStore';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

const client = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
});

client.interceptors.request.use((config) => {
  (config as { metadata?: { startedAt: number } }).metadata = {
    startedAt: Date.now(),
  };

  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  if (import.meta.env.DEV) {
    console.debug(`[API] ${String(config.method).toUpperCase()} ${config.baseURL ?? ''}${config.url ?? ''}`);
  }
  return config;
});

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach((p) => {
    if (error) p.reject(error);
    else if (token) p.resolve(token);
  });
  failedQueue = [];
}

client.interceptors.response.use(
  (res) => {
    if (import.meta.env.DEV) {
      const metadata = (res.config as { metadata?: { startedAt: number } }).metadata;
      const duration = metadata ? Date.now() - metadata.startedAt : null;
      console.debug(
        `[API] ${res.status} ${String(res.config.method).toUpperCase()} ${res.config.url ?? ''}${
          duration == null ? '' : ` (${duration}ms)`
        }`,
      );
    }
    return res;
  },
  async (err: unknown) => {
    if (!axios.isAxiosError(err)) {
      throw err instanceof Error ? err : new Error('Unknown API error');
    }

    const originalRequest = err.config;
    const status = err.response?.status;

    const reqUrl = originalRequest?.url ?? '';
    const isAuthEndpoint =
      reqUrl.includes('/auth/login') || reqUrl.includes('/auth/register') || reqUrl.includes('/auth/refresh');

    if (status === 401 && originalRequest && !isAuthEndpoint && !(originalRequest as { _retry?: boolean })._retry) {
      const refreshToken = useAuthStore.getState().refreshToken;
      if (!refreshToken) {
        void useAuthStore.getState().logout();
        throw err;
      }

      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return client(originalRequest);
        });
      }

      (originalRequest as { _retry?: boolean })._retry = true;
      isRefreshing = true;

      try {
        const newToken = await useAuthStore.getState().refreshAccessToken();
        if (newToken) {
          processQueue(null, newToken);
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return client(originalRequest);
        }
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        void useAuthStore.getState().logout();
      } finally {
        isRefreshing = false;
      }
    }

    const rawDetail = (err.response?.data as { detail?: unknown } | undefined)?.detail;
    let detail: string;
    if (typeof rawDetail === 'string') {
      detail = rawDetail;
    } else if (Array.isArray(rawDetail)) {
      detail = rawDetail
        .map((e: { msg?: string; message?: string; loc?: unknown[] } | string) => {
          if (typeof e === 'string') return e;
          const field = Array.isArray(e.loc) ? e.loc.filter((p) => p !== 'body').join('.') : '';
          const msg = e.msg ?? e.message ?? JSON.stringify(e);
          return field ? `${field}: ${msg}` : msg;
        })
        .join('; ');
    } else if (rawDetail && typeof rawDetail === 'object') {
      detail = JSON.stringify(rawDetail);
    } else if (status && status >= 500) {
      detail = 'Server error. Please try again later.';
    } else {
      detail = err.message ?? 'Unknown error';
    }

    let message = detail;
    if (err.code === 'ECONNABORTED') {
      message = 'Request timed out. Please try again.';
    } else if (!err.response) {
      message = 'Network error. Please check your connection.';
    }

    console.error(`[API] Error ${String(status ?? 'network')}: ${message}`);
    throw new Error(message);
  },
);

export default client;
