import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api } from '../api';
import type { User } from '../types';

interface AuthValue {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<User>;
  signUp: (name: string, email: string, password: string) => Promise<User>;
  demo: () => Promise<User>;
  signOut: () => Promise<void>;
}

const AuthCtx = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    api.auth
      .me()
      .then((u) => {
        if (!alive) return;
        setUser(u);
        setLoading(false);
      })
      .catch(() => {
        if (!alive) return;
        setUser(null);
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const value = useMemo<AuthValue>(
    () => ({
      user,
      loading,
      signIn: async (email, password) => {
        const u = await api.auth.signIn(email, password);
        setUser(u);
        return u;
      },
      signUp: async (name, email, password) => {
        const u = await api.auth.signUp(name, email, password);
        setUser(u);
        return u;
      },
      demo: async () => {
        const u = await api.auth.demo();
        setUser(u);
        return u;
      },
      signOut: async () => {
        await api.auth.signOut();
        setUser(null);
      },
    }),
    [user, loading],
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
