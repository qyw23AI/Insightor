/* Auth context — JWT token management */

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { getMe } from '../api/client';
import type { UserInfo } from '../types/urf';

interface AuthState {
  token: string | null;
  user: UserInfo | null;
  loading: boolean;
  login: (token: string, user: UserInfo) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState>({
  token: null, user: null, loading: true,
  login: () => {}, logout: () => {}, refreshUser: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('insightor_token'));
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const login = useCallback((t: string, u: UserInfo) => {
    localStorage.setItem('insightor_token', t);
    setToken(t);
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('insightor_token');
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    try {
      const u = await getMe(token);
      setUser(u);
    } catch {
      logout();
    }
    setLoading(false);
  }, [token, logout]);

  useEffect(() => { refreshUser(); }, [refreshUser]);

  return (
    <AuthContext.Provider value={{ token, user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
