import axios, { AxiosRequestConfig } from 'axios';
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { TokenResponse, UserProfile } from '../types';

interface AuthState {
  user: UserProfile | null;
  accessToken: string | null;
  refreshToken: string | null;
  expiresAt: string | null;
}

interface AuthContextValue {
  user: UserProfile | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  authFetch: <T = unknown>(config: AxiosRequestConfig) => Promise<T>;
}

const storageKey = 'vineguard_auth_tokens';
const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [state, setState] = useState<AuthState>({
    user: null,
    accessToken: null,
    refreshToken: null,
    expiresAt: null
  });
  const [isLoading, setIsLoading] = useState(true);
  const refreshTimeoutRef = useRef<number>();

  const persistTokens = useCallback((tokens: TokenResponse) => {
    const payload = {
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      expiresAt: tokens.expires_at
    };
    localStorage.setItem(storageKey, JSON.stringify(payload));
    setState((prev) => ({
      ...prev,
      accessToken: payload.accessToken,
      refreshToken: payload.refreshToken,
      expiresAt: payload.expiresAt
    }));
    return payload;
  }, []);

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimeoutRef.current) {
      window.clearTimeout(refreshTimeoutRef.current);
      refreshTimeoutRef.current = undefined;
    }
  }, []);

  const logout = useCallback(() => {
    clearRefreshTimer();
    localStorage.removeItem(storageKey);
    setState({ user: null, accessToken: null, refreshToken: null, expiresAt: null });
  }, [clearRefreshTimer]);

  const fetchProfile = useCallback(async (token: string) => {
    const { data } = await axios.get<UserProfile>(`${baseURL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return data;
  }, []);

  const refreshAccessToken = useCallback(
    async (overrideToken?: string): Promise<string> => {
      const refreshToken = overrideToken ?? state.refreshToken;
      if (!refreshToken) {
        throw new Error('Missing refresh token');
      }
      try {
        const { data } = await axios.post<TokenResponse>(`${baseURL}/auth/refresh`, {
          refresh_token: refreshToken
        });
        const stored = persistTokens(data);
        const profile = await fetchProfile(stored.accessToken);
        setState((prev) => ({ ...prev, user: profile }));
        return stored.accessToken;
      } catch (error) {
        logout();
        throw error;
      }
    },
    [state.refreshToken, persistTokens, fetchProfile, logout]
  );

  useEffect(() => {
    if (!state.expiresAt || !state.refreshToken) {
      return;
    }
    clearRefreshTimer();
    const expiryMs = new Date(state.expiresAt).getTime();
    const delay = Math.max(expiryMs - Date.now() - 60_000, 5_000);
    refreshTimeoutRef.current = window.setTimeout(() => {
      void refreshAccessToken().catch(() => {
        // handled in refresh
      });
    }, delay);
    return () => clearRefreshTimer();
  }, [state.expiresAt, state.refreshToken, refreshAccessToken, clearRefreshTimer]);

  useEffect(() => {
    const restore = async () => {
      const raw = localStorage.getItem(storageKey);
      if (!raw) {
        setIsLoading(false);
        return;
      }
      const parsed = JSON.parse(raw) as {
        accessToken: string;
        refreshToken: string;
        expiresAt: string;
      };
      setState((prev) => ({ ...prev, ...parsed }));
      try {
        const profile = await fetchProfile(parsed.accessToken);
        setState((prev) => ({ ...prev, user: profile }));
      } catch (error) {
        try {
          await refreshAccessToken(parsed.refreshToken);
        } catch (refreshError) {
          logout();
        }
      } finally {
        setIsLoading(false);
      }
    };
    void restore();
  }, [fetchProfile, refreshAccessToken, logout]);

  const login = useCallback(
    async (email: string, password: string) => {
      setIsLoading(true);
      try {
        const { data } = await axios.post<TokenResponse>(`${baseURL}/auth/login`, {
          email,
          password
        });
        const stored = persistTokens(data);
        const profile = await fetchProfile(stored.accessToken);
        setState((prev) => ({ ...prev, user: profile }));
      } finally {
        setIsLoading(false);
      }
    },
    [persistTokens, fetchProfile]
  );

  const authFetch = useCallback(
    async <T,>(config: AxiosRequestConfig): Promise<T> => {
      if (!state.accessToken) {
        throw new Error('Not authenticated');
      }
      try {
        const response = await axios.request<T>({
          baseURL,
          ...config,
          headers: {
            ...(config.headers ?? {}),
            Authorization: `Bearer ${state.accessToken}`
          }
        });
        return response.data;
      } catch (error) {
        if (axios.isAxiosError(error) && error.response?.status === 401 && state.refreshToken) {
          const newToken = await refreshAccessToken();
          const retryResponse = await axios.request<T>({
            baseURL,
            ...config,
            headers: {
              ...(config.headers ?? {}),
              Authorization: `Bearer ${newToken}`
            }
          });
          return retryResponse.data;
        }
        throw error;
      }
    },
    [state.accessToken, state.refreshToken, refreshAccessToken]
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user: state.user,
      isLoading,
      login,
      logout,
      authFetch
    }),
    [state.user, isLoading, login, logout, authFetch]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
