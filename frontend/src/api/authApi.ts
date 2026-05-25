import type { LoginRequest, RegisterRequest, TokenResponse, User } from '../types/auth';
import client from './client';

export async function registerUser(data: RegisterRequest): Promise<User> {
  const { data: user } = await client.post<User>('/auth/register', data);
  return user;
}

export async function loginUser(data: LoginRequest): Promise<TokenResponse> {
  const { data: tokens } = await client.post<TokenResponse>('/auth/login', data);
  return tokens;
}

export async function refreshToken(refresh_token: string): Promise<TokenResponse> {
  const { data: tokens } = await client.post<TokenResponse>('/auth/refresh', {
    refresh_token,
  });
  return tokens;
}

export async function logoutUser(refresh_token: string): Promise<void> {
  await client.post('/auth/logout', { refresh_token });
}
