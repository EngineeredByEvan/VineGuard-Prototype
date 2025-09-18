import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren
} from 'react';
import { apiClient } from '@/services/api';
import { getDemoAuth } from '@/mock/demoData';
import type { AuthResponse, User } from '@/types';

interface AuthContextValue {
  user: User | null;
  accessToken: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => void;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const ACCESS_KEY = 'vineguard.access';
const REFRESH_KEY = 'vineguard.refresh';
const USER_KEY = 'vineguard.user';

const persist = (user: User, tokens: AuthResponse['tokens']) => {
  sessionStorage.setItem(ACCESS_KEY, tokens.accessToken);
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  localStorage.setItem(REFRESH_KEY, tokens.refreshToken);
};

const clearPersisted = () => {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(USER_KEY);
  localStorage.removeItem(REFRESH_KEY);
};

export const AuthProvider = ({ children }: PropsWithChildren) => {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const handleAuthSuccess = useCallback(
    (response: AuthResponse) => {
      setUser(response.user);
      setAccessToken(response.tokens.accessToken);
      setRefreshToken(response.tokens.refreshToken);
      apiClient.setTokens(response.tokens.accessToken, response.tokens.refreshToken);
      persist(response.user, response.tokens);
    },
    []
  );

  const logout = useCallback(() => {
    clearPersisted();
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
    apiClient.clearTokens();
  }, []);

  const bootstrap = useCallback(async () => {
    const storedRefresh = localStorage.getItem(REFRESH_KEY);
    const storedAccess = sessionStorage.getItem(ACCESS_KEY);
    const storedUser = sessionStorage.getItem(USER_KEY);

    if (storedRefresh) {
      setRefreshToken(storedRefresh);
      apiClient.setTokens(storedAccess ?? undefined, storedRefresh);
    }

    if (storedUser && storedAccess) {
      const parsedUser = JSON.parse(storedUser) as User;
      setUser(parsedUser);
      setAccessToken(storedAccess);
    }

    if (storedRefresh) {
      try {
        const refreshed = await apiClient.refreshSession();
        handleAuthSuccess(refreshed);
      } catch (error) {
        console.warn('Refresh failed, falling back to demo mode', error);
        if (!storedUser) {
          const demo = getDemoAuth();
          handleAuthSuccess(demo);
        } else {
          logout();
        }
      }
    }

    setLoading(false);
  }, [handleAuthSuccess, logout]);

  useEffect(() => {
    bootstrap().catch((error) => {
      console.error('Bootstrap auth failed', error);
      setLoading(false);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


  const login = useCallback(
    async (email: string, password: string) => {
      setLoading(true);
      try {
        const response = await apiClient.login(email, password);
        handleAuthSuccess(response);
      } catch (error) {
        console.warn('Login failed, using demo auth', error);
        const demo = getDemoAuth(email);
        handleAuthSuccess(demo);
      } finally {
        setLoading(false);
      }
    },
    [handleAuthSuccess]
  );

  const register = useCallback(
    async (email: string, password: string, name?: string) => {
      setLoading(true);
      try {
        const response = await apiClient.register(email, password, name);
        handleAuthSuccess(response);
      } catch (error) {
        console.warn('Register failed, using demo auth', error);
        const demo = getDemoAuth(email, name ?? 'Demo Grower');
        handleAuthSuccess(demo);
      } finally {
        setLoading(false);
      }
    },
    [handleAuthSuccess]
  );


  const refreshSession = useCallback(async () => {
    if (!refreshToken) return;
    try {
      const refreshed = await apiClient.refreshSession();
      handleAuthSuccess(refreshed);
    } catch (error) {
      console.error('Refresh session failed', error);
      const demo = getDemoAuth();
      handleAuthSuccess(demo);
    }
  }, [handleAuthSuccess, refreshToken]);

  const value = useMemo(
    () => ({ user, accessToken, loading, login, register, logout, refreshSession }),
    [user, accessToken, loading, login, register, logout, refreshSession]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuthContext = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuthContext must be used within AuthProvider');
  return context;
};
