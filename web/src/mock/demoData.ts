import type {
  AuthResponse,
  Insight,
  NodeDetail,
  NodeTelemetryPoint,
  OrgOverview,
  Site
} from '@/types';

const baseTimestamp = Date.now();

const makeTelemetrySeries = (seed: number, nodeId?: string): NodeTelemetryPoint[] => {
  return Array.from({ length: 72 }, (_, index) => {
    const time = baseTimestamp - (72 - index) * 5 * 60 * 1000;
    const soilMoisture = 35 + Math.sin((index + seed) / 4) * 5 + Math.random() * 2;
    const soilTemp = 18 + Math.sin((index + seed) / 8) * 2 + Math.random();
    const airTemp = 22 + Math.sin((index + seed) / 6) * 3 + Math.random() * 2;
    const humidity = 55 + Math.cos((index + seed) / 7) * 10 + Math.random() * 4;
    const light = 600 + Math.sin((index + seed) / 3) * 300 + Math.random() * 50;
    const battery = 80 - index * 0.05 + Math.random();

    return {
      timestamp: new Date(time).toISOString(),
      soilMoisture: Math.max(10, Math.min(soilMoisture, 90)),
      soilTemp: Math.max(5, Math.min(soilTemp, 40)),
      airTemp: Math.max(5, Math.min(airTemp, 45)),
      humidity: Math.max(30, Math.min(humidity, 99)),
      light: Math.max(0, light),
      battery: Math.max(20, Math.min(battery, 100)),
      nodeId
    };
  });
};

const nodeSummaries = [
  {
    id: 'alpha',
    name: 'Block A - North',
    soilMoisture: 38,
    battery: 76,
    signalStrength: 88,
    lastSeen: new Date(baseTimestamp - 60 * 1000).toISOString(),
    status: 'online' as const
  },
  {
    id: 'bravo',
    name: 'Block A - South',
    soilMoisture: 34,
    battery: 69,
    signalStrength: 81,
    lastSeen: new Date(baseTimestamp - 6 * 60 * 1000).toISOString(),
    status: 'online' as const
  },
  {
    id: 'charlie',
    name: 'Block B - Creek',
    soilMoisture: 29,
    battery: 42,
    signalStrength: 62,
    lastSeen: new Date(baseTimestamp - 18 * 60 * 1000).toISOString(),
    status: 'offline' as const
  }
];

export const demoSites: Site[] = [
  {
    id: 'demo-vineyard',
    name: 'Napa Estate Vineyard',
    description: '12 hectare drip irrigated block with volcanic soil and rolling hills.',
    coordinates: { lat: 38.5025, lng: -122.2654 },
    nodes: nodeSummaries
  },
  {
    id: 'demo-valley',
    name: 'Rutherford Valley',
    description: 'Loamy soil near the river bank with premium cabernet blocks.',
    coordinates: { lat: 38.4621, lng: -122.4214 },
    nodes: [nodeSummaries[1]]
  }
];

const nodeDetails: Record<string, NodeDetail> = {
  alpha: {
    ...nodeSummaries[0],
    siteId: 'demo-vineyard',
    firmwareVersion: '2.4.1',
    publishIntervalSec: 900
  },
  bravo: {
    ...nodeSummaries[1],
    siteId: 'demo-vineyard',
    firmwareVersion: '2.4.1',
    publishIntervalSec: 900
  },
  charlie: {
    ...nodeSummaries[2],
    siteId: 'demo-vineyard',
    firmwareVersion: '2.3.5',
    publishIntervalSec: 1200
  }
};

const telemetryMap: Record<string, NodeTelemetryPoint[]> = {
  alpha: makeTelemetrySeries(3, 'alpha'),
  bravo: makeTelemetrySeries(9, 'bravo'),
  charlie: makeTelemetrySeries(14, 'charlie')
};

export const demoInsights: Insight[] = [
  {
    id: 'insight-1',
    siteId: 'demo-vineyard',
    nodeId: 'alpha',
    type: 'irrigation',
    severity: 'medium',
    message: 'Soil moisture trending low, consider irrigating in the next 8 hours.',
    timestamp: new Date(baseTimestamp - 45 * 60 * 1000).toISOString()
  },
  {
    id: 'insight-2',
    siteId: 'demo-vineyard',
    nodeId: 'charlie',
    type: 'battery',
    severity: 'high',
    message: 'Battery health at 42%, schedule maintenance soon.',
    timestamp: new Date(baseTimestamp - 2 * 60 * 60 * 1000).toISOString()
  },
  {
    id: 'insight-3',
    siteId: 'demo-valley',
    nodeId: 'bravo',
    type: 'disease',
    severity: 'low',
    message: 'Powdery mildew pressure increasing due to humidity swing.',
    timestamp: new Date(baseTimestamp - 90 * 60 * 1000).toISOString()
  }
];

export const demoOverview: OrgOverview = {
  totalNodes: nodeSummaries.length,
  onlineNodes: nodeSummaries.filter((node) => node.status === 'online').length,
  avgSoilMoisture:
    nodeSummaries.reduce((sum, node) => sum + node.soilMoisture, 0) / nodeSummaries.length,
  batteryWarnings: nodeSummaries.filter((node) => node.battery < 50).length
};

export const getDemoNodeDetail = (nodeId: string): NodeDetail => {
  return nodeDetails[nodeId] ?? {
    id: nodeId,
    name: `Node ${nodeId}`,
    soilMoisture: 0,
    battery: 0,
    signalStrength: 0,
    lastSeen: new Date().toISOString(),
    status: 'offline',
    siteId: 'demo-vineyard',
    firmwareVersion: 'unknown',
    publishIntervalSec: 900
  };
};

export const getDemoTelemetry = (nodeId: string): NodeTelemetryPoint[] => {
  return telemetryMap[nodeId] ?? makeTelemetrySeries(Math.floor(Math.random() * 10), nodeId);
};

export const getDemoInsights = () => demoInsights;

export const getDemoAuth = (email = 'demo@vineguard.io', name = 'Demo Grower'): AuthResponse => ({
  user: {
    id: 'demo-user',
    email,
    name,
    orgId: 'demo-org'
  },
  tokens: {
    accessToken: 'demo-access-token',
    refreshToken: 'demo-refresh-token'
  }
});

export const createMockLiveSample = (nodeId: string): NodeTelemetryPoint => {
  const base = telemetryMap[nodeId]?.[telemetryMap[nodeId].length - 1] ?? makeTelemetrySeries(2, nodeId).slice(-1)[0];
  const timestamp = new Date().toISOString();
  const jitter = (value: number, delta: number) => value + (Math.random() - 0.5) * delta;
  const sample = base ?? {
    timestamp,
    soilMoisture: 35,
    soilTemp: 18,
    airTemp: 22,
    humidity: 55,
    light: 600,
    battery: 80,
    nodeId
  };

  return {
    timestamp,
    soilMoisture: Math.max(5, Math.min(jitter(sample.soilMoisture, 2), 90)),
    soilTemp: Math.max(0, Math.min(jitter(sample.soilTemp, 1.5), 40)),
    airTemp: Math.max(0, Math.min(jitter(sample.airTemp, 2.5), 45)),
    humidity: Math.max(20, Math.min(jitter(sample.humidity, 5), 99)),
    light: Math.max(0, jitter(sample.light, 120)),
    battery: Math.max(10, Math.min(sample.battery - Math.random() * 0.1, 100)),
    nodeId
  };
};
