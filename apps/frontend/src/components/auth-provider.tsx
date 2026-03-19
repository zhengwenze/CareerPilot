"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  fetchCurrentUser,
  loginRequest,
  logoutRequest,
  registerRequest,
  type AuthSession,
  type AuthUser,
} from "@/lib/api/modules/auth";
import {
  clearStoredSession,
  readStoredSession,
  writeStoredSession,
} from "@/lib/auth-storage";

type Credentials = {
  email: string;
  password: string;
};

type Registration = Credentials & {
  nickname?: string;
};

type AuthContextValue = {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  login: (payload: Credentials) => Promise<AuthSession>;
  register: (payload: Registration) => Promise<AuthSession>;
  logout: () => Promise<void>;
  refreshCurrentUser: () => Promise<AuthUser | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function persistSession(nextSession: AuthSession) {
  writeStoredSession(nextSession);
  return nextSession;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const storedSession = readStoredSession();

    if (!storedSession) {
      setIsBootstrapping(false);
      return;
    }
    const initialSession = storedSession;

    async function restoreSession() {
      try {
        const user = await fetchCurrentUser(initialSession.accessToken);
        if (cancelled) {
          return;
        }
        const nextSession = persistSession({
          ...initialSession,
          user,
        });
        setSession(nextSession);
      } catch {
        if (cancelled) {
          return;
        }
        clearStoredSession();
        setSession(null);
      } finally {
        if (!cancelled) {
          setIsBootstrapping(false);
        }
      }
    }

    void restoreSession();

    return () => {
      cancelled = true;
    };
  }, []);

  async function login(payload: Credentials) {
    const nextSession = persistSession(await loginRequest(payload));
    setSession(nextSession);
    return nextSession;
  }

  async function register(payload: Registration) {
    const nextSession = persistSession(await registerRequest(payload));
    setSession(nextSession);
    return nextSession;
  }

  async function logout() {
    const currentToken = session?.accessToken;

    try {
      if (currentToken) {
        await logoutRequest(currentToken);
      }
    } finally {
      clearStoredSession();
      setSession(null);
    }
  }

  async function refreshCurrentUser() {
    if (!session?.accessToken) {
      setSession(null);
      return null;
    }

    try {
      const user = await fetchCurrentUser(session.accessToken);
      const nextSession = persistSession({
        ...session,
        user,
      });
      setSession(nextSession);
      return user;
    } catch {
      clearStoredSession();
      setSession(null);
      return null;
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user: session?.user ?? null,
        token: session?.accessToken ?? null,
        isAuthenticated: Boolean(session?.accessToken),
        isBootstrapping,
        login,
        register,
        logout,
        refreshCurrentUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return context;
}
