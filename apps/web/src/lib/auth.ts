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

const AUTH_STORAGE_KEY = "career-pilot.auth";
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function normalizeSession(payload: AuthResponse): AuthSession {
  return {
    accessToken: payload.access_token,
    expiresIn: payload.expires_in,
    user: payload.user,
  };
}

async function parseError(response: Response): Promise<never> {
  let message = "请求失败，请稍后重试。";

  try {
    const payload = (await response.json()) as {
      detail?: string | Array<{ msg?: string }>;
    };

    if (typeof payload.detail === "string") {
      message = payload.detail;
    } else if (Array.isArray(payload.detail) && payload.detail.length > 0) {
      message = payload.detail
        .map((item) => item.msg ?? "请求参数有误")
        .join("；");
    }
  } catch {
    message = "服务暂时不可用，请检查后端是否已启动。";
  }

  throw new ApiError(message, response.status);
}

async function apiRequest<T>(
  path: string,
  init: RequestInit & { token?: string } = {},
): Promise<T> {
  const { token, headers, ...rest } = init;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    cache: "no-store",
    headers: {
      ...(rest.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(headers ?? {}),
    },
  });

  if (!response.ok) {
    await parseError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function readStoredSession(): AuthSession | null {
  if (typeof window === "undefined") {
    return null;
  }

  const rawValue = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    return JSON.parse(rawValue) as AuthSession;
  } catch {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

export function writeStoredSession(session: AuthSession): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

export function clearStoredSession(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}

export async function registerRequest(
  payload: RegisterPayload,
): Promise<AuthSession> {
  const response = await apiRequest<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  return normalizeSession(response);
}

export async function loginRequest(payload: LoginPayload): Promise<AuthSession> {
  const response = await apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  return normalizeSession(response);
}

export async function logoutRequest(token: string): Promise<void> {
  await apiRequest("/auth/logout", {
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
