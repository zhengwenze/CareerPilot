import { apiRequest } from "@/lib/api/client";

export type AuthUser = {
  id: string;
  email: string;
  nickname: string | null;
  role: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type AuthSession = {
  accessToken: string;
  expiresIn: number;
  user: AuthUser;
};

type AuthResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
};

type RegisterPayload = {
  email: string;
  password: string;
  nickname?: string;
};

type LoginPayload = {
  email: string;
  password: string;
};

type LogoutResponse = {
  message: string;
};

function normalizeSession(payload: AuthResponse): AuthSession {
  return {
    accessToken: payload.access_token,
    expiresIn: payload.expires_in,
    user: payload.user,
  };
}

export async function registerRequest(
  payload: RegisterPayload
): Promise<AuthSession> {
  const response = await apiRequest<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  return normalizeSession(response);
}

export async function loginRequest(
  payload: LoginPayload
): Promise<AuthSession> {
  const response = await apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  return normalizeSession(response);
}

export async function logoutRequest(token: string): Promise<LogoutResponse> {
  return apiRequest<LogoutResponse>("/auth/logout", {
    method: "POST",
    token,
  });
}

export async function fetchCurrentUser(token: string): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/me", {
    method: "GET",
    token,
  });
}
