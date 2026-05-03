export interface User {
    user_id: string;
    email: string;
    username: string;
    is_active: boolean;
    created_at: string | null;
}

export interface LoginRequest {
    email: string;
    password: string;
}

export interface RegisterRequest {
    email: string;
    username: string;
    password: string;
}

export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}
