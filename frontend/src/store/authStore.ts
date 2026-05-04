import { create } from "zustand";
import { loginUser as apiLogin, registerUser as apiRegister, refreshToken as apiRefresh, logoutUser as apiLogout } from "../api/authApi";
import type { User, LoginRequest, RegisterRequest } from "../types/auth";

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

interface AuthState {
    user: User | null;
    accessToken: string | null;
    refreshToken: string | null;
    isLoading: boolean;
    isInitialized: boolean;
    error: string | null;

    login: (data: LoginRequest) => Promise<void>;
    register: (data: RegisterRequest) => Promise<void>;
    logout: () => Promise<void>;
    refreshAccessToken: () => Promise<string | null>;
    initializeAuth: () => Promise<void>;
    setTokens: (access: string, refresh: string) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
    user: null,
    accessToken: localStorage.getItem(ACCESS_TOKEN_KEY),
    refreshToken: localStorage.getItem(REFRESH_TOKEN_KEY),
    isLoading: false,
    isInitialized: false,
    error: null,

    setTokens: (access: string, refresh: string) => {
        localStorage.setItem(ACCESS_TOKEN_KEY, access);
        localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
        set({ accessToken: access, refreshToken: refresh });
    },

    login: async (data: LoginRequest) => {
        set({ isLoading: true, error: null });
        try {
            const tokens = await apiLogin(data);
            get().setTokens(tokens.access_token, tokens.refresh_token);

            const payload = JSON.parse(atob(tokens.access_token.split(".")[1]));
            set({
                user: {
                    user_id: payload.sub,
                    email: "",
                    username: "",
                    is_active: true,
                    created_at: null,
                },
                isLoading: false,
            });
        } catch (err) {
            set({
                error: err instanceof Error ? err.message : "Login failed",
                isLoading: false,
            });
            throw err;
        }
    },

    register: async (data: RegisterRequest) => {
        set({ isLoading: true, error: null });
        try {
            await apiRegister(data);
            await get().login({ email: data.email, password: data.password });
        } catch (err) {
            set({
                error: err instanceof Error ? err.message : "Registration failed",
                isLoading: false,
            });
            throw err;
        }
    },

    logout: async () => {
        const { refreshToken } = get();
        try {
            if (refreshToken) {
                await apiLogout(refreshToken);
            }
        } catch {
        }
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        set({ user: null, accessToken: null, refreshToken: null, error: null });
    },

    refreshAccessToken: async () => {
        const { refreshToken } = get();
        if (!refreshToken) return null;

        try {
            const tokens = await apiRefresh(refreshToken);
            get().setTokens(tokens.access_token, tokens.refresh_token);
            return tokens.access_token;
        } catch {
            localStorage.removeItem(ACCESS_TOKEN_KEY);
            localStorage.removeItem(REFRESH_TOKEN_KEY);
            set({ user: null, accessToken: null, refreshToken: null });
            return null;
        }
    },

    initializeAuth: async () => {
        const { accessToken, refreshToken } = get();

        try {
            if (accessToken) {
                try {
                    const payload = JSON.parse(atob(accessToken.split(".")[1]));
                    const exp = payload.exp * 1000;
                    if (exp > Date.now()) {
                        set({
                            user: {
                                user_id: payload.sub,
                                email: "",
                                username: "",
                                is_active: true,
                                created_at: null,
                            },
                        });
                        return;
                    }
                } catch {
                    }
            }

            if (refreshToken) {
                const newToken = await get().refreshAccessToken();
                if (newToken) {
                    try {
                        const payload = JSON.parse(atob(newToken.split(".")[1]));
                        set({
                            user: {
                                user_id: payload.sub,
                                email: "",
                                username: "",
                                is_active: true,
                                created_at: null,
                            },
                        });
                    } catch {
                    }
                }
            }
        } finally {
            set({ isInitialized: true });
        }
    },
}));
