import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react';
import { api, post } from './api';
import type { RoleCode, User } from './types';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hasRole: (...roles: RoleCode[]) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!document.cookie.split('; ').some((item) => item.startsWith('csrf_token='))) {
      setLoading(false);
      return;
    }
    api<User>('/auth/me').then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    login: async (username, password) => setUser(await post<User>('/auth/login', { username, password })),
    logout: async () => { await post<void>('/auth/logout'); setUser(null); },
    hasRole: (...roles) => Boolean(user?.roles.some((role) => roles.includes(role.code))),
  }), [loading, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
