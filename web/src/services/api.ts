import type {
  AuthResponse,
  CommandPayload,
  Insight,
  NodeDetail,
  NodeTelemetryPoint,
  OrgOverview,
  Site
} from '@/types';
import {
  createMockLiveSample,
  demoInsights,
  demoOverview,
  demoSites,
  getDemoAuth,
  getDemoNodeDetail,
  getDemoTelemetry
} from '@/mock/demoData';

interface RequestOptions<T> {
  fallback?: () => T | Promise<T>;
  skipAuth?: boolean;
}

const withTrailingSlash = (value: string) => (value.endsWith('/') ? value.slice(0, -1) : value);

export class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private readonly baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = withTrailingSlash(baseUrl || '');
  }

  setTokens(access?: string, refresh?: string) {
    if (access) this.accessToken = access;
    if (refresh) this.refreshToken = refresh;
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    return this.request<AuthResponse>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ email, password })
      },
      {
        skipAuth: true,
        fallback: () => getDemoAuth(email)
      }
    );
  }

  async register(email: string, password: string, name?: string): Promise<AuthResponse> {
    return this.request<AuthResponse>(
      '/auth/register',
      {
        method: 'POST',
        body: JSON.stringify({ email, password, name })
      },
      {
        skipAuth: true,
        fallback: () => getDemoAuth(email, name ?? 'Demo Grower')
      }
    );
  }

  async refreshSession(): Promise<AuthResponse> {
    if (!this.refreshToken) {
      return getDemoAuth();
    }

    return this.request<AuthResponse>(
      '/auth/refresh',
      {
        method: 'POST',
        body: JSON.stringify({ refreshToken: this.refreshToken })
      },
      {
        skipAuth: true,
        fallback: () => getDemoAuth()
      }
    );
  }

  async fetchOrgOverview(orgId: string): Promise<OrgOverview> {
    return this.request<OrgOverview>(`/orgs/${orgId}/overview`, undefined, {
      fallback: () => ({ ...demoOverview })
    });
  }

  async fetchSites(orgId: string): Promise<Site[]> {
    return this.request<Site[]>(`/orgs/${orgId}/sites`, undefined, {
      fallback: () => demoSites.map((site) => ({ ...site, nodes: site.nodes.map((node) => ({ ...node })) }))
    });
  }

  async fetchSite(siteId: string): Promise<Site> {
    return this.request<Site>(`/sites/${siteId}`, undefined, {
      fallback: () =>
        demoSites
          .map((site) => ({ ...site, nodes: site.nodes.map((node) => ({ ...node })) }))
          .find((site) => site.id === siteId) ?? demoSites[0]
    });
  }

  async fetchNode(nodeId: string): Promise<NodeDetail> {
    return this.request<NodeDetail>(`/nodes/${nodeId}`, undefined, {
      fallback: () => ({ ...getDemoNodeDetail(nodeId) })
    });
  }

  async fetchNodeTelemetry(nodeId: string, range: string): Promise<NodeTelemetryPoint[]> {
    return this.request<NodeTelemetryPoint[]>(`/nodes/${nodeId}/telemetry?range=${range}`, undefined, {
      fallback: () => getDemoTelemetry(nodeId).map((point) => ({ ...point }))
    });
  }

  async fetchInsights(orgId: string, params: Record<string, string | undefined>): Promise<Insight[]> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value) query.set(key, value);
    });
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return this.request<Insight[]>(`/orgs/${orgId}/insights${suffix}`, undefined, {
      fallback: () => demoInsights.map((insight) => ({ ...insight }))
    });
  }

  async sendCommand(payload: CommandPayload): Promise<void> {
    await this.request(
      '/commands',
      {
        method: 'POST',
        body: JSON.stringify(payload)
      },
      {
        fallback: () => undefined
      }
    );
  }

  subscribeToLive(orgId: string, onMessage: (payload: NodeTelemetryPoint) => void) {
    const liveUrl = `${this.baseUrl}/live/${orgId}`;
    let eventSource: EventSource | null = null;
    let isClosed = false;

    if (typeof window !== 'undefined' && 'EventSource' in window) {
      eventSource = new EventSource(liveUrl, { withCredentials: true });
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as NodeTelemetryPoint;
          onMessage(data);
        } catch (error) {
          console.warn('Failed to parse live event', error);
        }
      };
      eventSource.onerror = (error) => {
        console.error('Live stream error, closing EventSource', error);
        eventSource?.close();
        if (!isClosed) {
          startPollingFallback();
        }
      };
    } else {
      startPollingFallback();
    }

    const intervalHandles: Array<ReturnType<typeof setInterval>> = [];

    function startPollingFallback() {
      const nodeIds = demoSites.flatMap((site) => site.nodes.map((node) => node.id));
      const handle = setInterval(() => {
        const target = nodeIds[Math.floor(Math.random() * nodeIds.length)] ?? 'alpha';
        onMessage(createMockLiveSample(target));
      }, 5000);
      intervalHandles.push(handle);
    }

    return () => {
      isClosed = true;
      eventSource?.close();
      intervalHandles.forEach((handle) => clearInterval(handle));
    };
  }

  private async request<T>(path: string, init?: RequestInit, options: RequestOptions<T> = {}): Promise<T> {
    const { fallback, skipAuth } = options;
    const headers = new Headers(init?.headers);
    if (init?.body && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }
    if (!skipAuth && this.accessToken) {
      headers.set('Authorization', `Bearer ${this.accessToken}`);
    }

    const requestInit: RequestInit = {
      credentials: 'include',
      ...init,
      headers
    };

    if (!this.baseUrl) {
      if (fallback) {
        return await fallback();
      }
      throw new Error('API base URL is not configured.');
    }

    try {
      const response = await fetch(`${this.baseUrl}${path}`, requestInit);
      if (response.status === 401 && !skipAuth && this.refreshToken) {
        const refreshed = await this.refreshSession();
        this.setTokens(refreshed.tokens.accessToken, refreshed.tokens.refreshToken);
        return this.request<T>(path, init, options);
      }
      if (!response.ok) {
        throw new Error(`API request failed with status ${response.status}`);
      }
      if (response.status === 204) {
        return undefined as T;
      }
      return (await response.json()) as T;
    } catch (error) {
      if (fallback) {
        return await fallback();
      }
      throw error;
    }
  }
}

export const apiClient = new ApiClient(import.meta.env.VITE_API_URL || '');
