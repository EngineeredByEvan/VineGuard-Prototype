export type InsightType = 'irrigation' | 'disease' | 'battery';
export type InsightSeverity = 'low' | 'medium' | 'high';

export interface OrgOverview {
  totalNodes: number;
  onlineNodes: number;
  avgSoilMoisture: number;
  batteryWarnings: number;
}

export interface NodeSummary {
  id: string;
  name: string;
  soilMoisture: number;
  battery: number;
  signalStrength: number;
  lastSeen: string;
  status: 'online' | 'offline';
}

export interface Site {
  id: string;
  name: string;
  description?: string;
  coordinates: {
    lat: number;
    lng: number;
  };
  nodes: NodeSummary[];
}

export interface NodeTelemetryPoint {
  timestamp: string;
  soilMoisture: number;
  soilTemp: number;
  airTemp: number;
  humidity: number;
  light: number;
  battery: number;
  nodeId?: string;
}

export interface NodeDetail extends NodeSummary {
  siteId: string;
  firmwareVersion: string;
  publishIntervalSec: number;
}

export interface Insight {
  id: string;
  siteId: string;
  nodeId: string;
  type: InsightType;
  severity: InsightSeverity;
  message: string;
  timestamp: string;
  acknowledged?: boolean;
}

export interface CommandPayload {
  nodeId: string;
  publishIntervalSec: number;
  otaUrl?: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

export interface User {
  id: string;
  email: string;
  name: string;
  orgId: string;
}
