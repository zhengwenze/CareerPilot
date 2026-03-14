"use client";

import {
  createContext,
  useContext,
  useEffect,
  useEffectEvent,
  useState,
} from "react";

import {
  clearStoredSession,
  fetchCurrentUser,
  loginRequest,
  logoutRequest,
  readStoredSession,
  registerRequest,
  writeStoredSession,
  type AuthSession,
  type AuthUser,
} from "@/lib/auth";

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
};

const AuthContext = createContext<AuthContextValue | null>(null);

function persistSession(nextSession: AuthSession) {
  writeStoredSession(nextSession);
  return nextSession;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);

  const restoreSession = useEffectEvent(async (storedSession: AuthSession) => {
    try {
      const user = await fetchCurrentUser(storedSession.accessToken);
      const nextSession = persistSession({
        ...storedSession,
        user,
      });
      setSession(nextSession);
    } catch {
      clearStoredSession();
      setSession(null);
    } finally {
      setIsBootstrapping(false);
    }
  });

  useEffect(() => {
    const storedSession = readStoredSession();

    if (!storedSession) {
      setIsBootstrapping(false);
      return;
    }

    void restoreSession(storedSession);
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
