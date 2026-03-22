import type { AuthSession } from "@/lib/api/modules/auth";

const AUTH_STORAGE_KEY = "career-pilot.auth";

function normalizeStoredSession(raw: unknown): AuthSession | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }

  const payload = raw as Record<string, unknown>;
  const accessToken =
    typeof payload.accessToken === "string"
      ? payload.accessToken.trim()
      : typeof payload.access_token === "string"
        ? payload.access_token.trim()
        : "";
  const expiresIn =
    typeof payload.expiresIn === "number"
      ? payload.expiresIn
      : typeof payload.expires_in === "number"
        ? payload.expires_in
        : 0;
  const user =
    payload.user && typeof payload.user === "object"
      ? (payload.user as AuthSession["user"])
      : null;

  if (!accessToken || !user?.id || !user.email) {
    return null;
  }

  return {
    accessToken,
    expiresIn,
    user,
  };
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
    const parsed = normalizeStoredSession(JSON.parse(rawValue));
    if (!parsed) {
      window.localStorage.removeItem(AUTH_STORAGE_KEY);
      return null;
    }
    return parsed;
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
