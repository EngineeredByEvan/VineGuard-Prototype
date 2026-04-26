import axios from 'axios';

import type {
  Alert,
  Block,
  BlockWithNodes,
  DashboardOverview,
  GDDEntry,
  Node,
  Recommendation,
  TelemetryReading,
  UnregisteredDevice,
  Vineyard,
} from './types';

// Re-export TelemetryReading for backwards compat with App.tsx
export type { TelemetryReading };

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY ?? '';
const headers = { 'X-API-Key': API_KEY };

// ── Vineyards ──────────────────────────────────────────────────────────────

export async function fetchVineyards(): Promise<Vineyard[]> {
  const { data } = await axios.get<Vineyard[]>(`${API_BASE}/api/v1/vineyards`, { headers });
  return data;
}

export async function fetchVineyard(id: string): Promise<Vineyard> {
  const { data } = await axios.get<Vineyard>(`${API_BASE}/api/v1/vineyards/${id}`, { headers });
  return data;
}

// ── Blocks ─────────────────────────────────────────────────────────────────

export async function fetchBlocks(vineyardId?: string): Promise<Block[]> {
  const params: Record<string, string> = {};
  if (vineyardId) params['vineyard_id'] = vineyardId;
  const { data } = await axios.get<Block[]>(`${API_BASE}/api/v1/blocks`, { headers, params });
  return data;
}

export async function fetchBlock(id: string): Promise<BlockWithNodes> {
  const { data } = await axios.get<BlockWithNodes>(`${API_BASE}/api/v1/blocks/${id}`, { headers });
  return data;
}

export async function fetchBlockTelemetry(
  blockId: string,
  hours = 24,
): Promise<TelemetryReading[]> {
  const { data } = await axios.get<TelemetryReading[]>(
    `${API_BASE}/api/v1/blocks/${blockId}/telemetry`,
    { headers, params: { limit: 200, hours } },
  );
  return data;
}

// ── Nodes ──────────────────────────────────────────────────────────────────

export async function fetchNodes(params?: {
  blockId?: string;
  status?: string;
}): Promise<Node[]> {
  const query: Record<string, string> = {};
  if (params?.blockId) query['block_id'] = params.blockId;
  if (params?.status) query['status'] = params.status;
  const { data } = await axios.get<Node[]>(`${API_BASE}/api/v1/nodes`, {
    headers,
    params: query,
  });
  return data;
}

export async function fetchNode(id: string): Promise<Node> {
  const { data } = await axios.get<Node>(`${API_BASE}/api/v1/nodes/${id}`, { headers });
  return data;
}

export async function fetchNodeTelemetry(
  nodeId: string,
  hours = 48,
): Promise<TelemetryReading[]> {
  const { data } = await axios.get<TelemetryReading[]>(
    `${API_BASE}/api/v1/nodes/${nodeId}/telemetry`,
    { headers, params: { limit: 200, hours } },
  );
  return data;
}

export async function createNode(payload: {
  device_id: string;
  name: string;
  tier: 'basic' | 'precision_plus';
  block_id: string;
  lat?: number;
  lon?: number;
  firmware_version?: string;
}): Promise<Node> {
  const { data } = await axios.post<Node>(`${API_BASE}/api/v1/nodes`, payload, { headers });
  return data;
}

export async function fetchUnregisteredDevices(): Promise<UnregisteredDevice[]> {
  const { data } = await axios.get<UnregisteredDevice[]>(
    `${API_BASE}/api/v1/nodes/unregistered-devices`,
    { headers },
  );
  return data;
}

// ── Alerts ─────────────────────────────────────────────────────────────────

export async function fetchAlerts(params?: {
  vineyardId?: string;
  blockId?: string;
  isActive?: boolean;
}): Promise<Alert[]> {
  const query: Record<string, string> = { limit: '50' };
  if (params?.vineyardId) query['vineyard_id'] = params.vineyardId;
  if (params?.blockId) query['block_id'] = params.blockId;
  if (params?.isActive !== undefined) query['is_active'] = String(params.isActive);
  const { data } = await axios.get<Alert[]>(`${API_BASE}/api/v1/alerts`, {
    headers,
    params: query,
  });
  return data;
}

export async function resolveAlert(id: string): Promise<Alert> {
  const { data } = await axios.post<Alert>(
    `${API_BASE}/api/v1/alerts/${id}/resolve`,
    {},
    { headers },
  );
  return data;
}

// ── Recommendations ────────────────────────────────────────────────────────

export async function fetchRecommendations(params?: {
  vineyardId?: string;
  blockId?: string;
}): Promise<Recommendation[]> {
  const query: Record<string, string> = { limit: '50', is_acknowledged: 'false' };
  if (params?.vineyardId) query['vineyard_id'] = params.vineyardId;
  if (params?.blockId) query['block_id'] = params.blockId;
  const { data } = await axios.get<Recommendation[]>(`${API_BASE}/api/v1/recommendations`, {
    headers,
    params: query,
  });
  return data;
}

export async function acknowledgeRecommendation(id: string): Promise<Recommendation> {
  const { data } = await axios.post<Recommendation>(
    `${API_BASE}/api/v1/recommendations/${id}/acknowledge`,
    {},
    { headers },
  );
  return data;
}

// ── Dashboard ──────────────────────────────────────────────────────────────

export async function fetchDashboardOverview(vineyardId: string): Promise<DashboardOverview> {
  const { data } = await axios.get<DashboardOverview>(
    `${API_BASE}/api/v1/dashboard/overview`,
    { headers, params: { vineyard_id: vineyardId } },
  );
  return data;
}

export async function fetchGDD(vineyardId: string, days = 30): Promise<GDDEntry[]> {
  const { data } = await axios.get<GDDEntry[]>(`${API_BASE}/api/v1/dashboard/gdd`, {
    headers,
    params: { vineyard_id: vineyardId, days },
  });
  return data;
}

// ── Legacy / SSE ───────────────────────────────────────────────────────────

export async function fetchRecentReadings(limit = 50): Promise<TelemetryReading[]> {
  const { data } = await axios.get<TelemetryReading[]>(`${API_BASE}/readings`, {
    headers,
    params: { limit },
  });
  return data;
}

export function openTelemetryStream(
  onMessage: (reading: TelemetryReading) => void,
): EventSource | null {
  if (!API_KEY) return null;
  const url = new URL(`${API_BASE}/streams/telemetry`);
  url.searchParams.set('api_key', API_KEY);
  const source = new EventSource(url.toString(), { withCredentials: false });
  source.onmessage = (event) => {
    try {
      const reading = JSON.parse(event.data) as TelemetryReading;
      onMessage(reading);
    } catch (error) {
      console.error('Failed to parse telemetry event', error);
    }
  };
  return source;
}
