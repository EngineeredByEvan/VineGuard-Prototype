export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_at: string;
}

export interface UserProfile {
  email: string;
  orgId: string;
  role: string;
  createdAt: string;
}

export interface NodeStatusRow {
  orgId: string;
  siteId: string;
  nodeId: string;
  lastSeen: string;
  batteryV: number | null;
  fwVersion: string | null;
  health: string | null;
}

export interface TelemetrySnapshot {
  ts: string;
  orgId: string;
  siteId: string;
  nodeId: string;
  sensors: {
    soilMoisture: number | null;
    soilTempC: number | null;
    airTempC: number | null;
    humidity: number | null;
    lightLux: number | null;
    vbat: number | null;
  };
  rssi: number | null;
  fwVersion: string | null;
}

export interface InsightRow {
  ts: string;
  type: string;
  payload: Record<string, unknown>;
  nodeId: string;
  siteId: string;
}
