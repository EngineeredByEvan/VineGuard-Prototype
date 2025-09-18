import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import type { InsightRow, NodeStatusRow, TelemetrySnapshot } from '../types';

const Dashboard = () => {
  const { user, logout, authFetch } = useAuth();
  const [statusRows, setStatusRows] = useState<NodeStatusRow[]>([]);
  const [telemetry, setTelemetry] = useState<TelemetrySnapshot[]>([]);
  const [insights, setInsights] = useState<InsightRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const [statusData, telemetryData, insightsData] = await Promise.all([
        authFetch<NodeStatusRow[]>({ url: '/api/nodes/status' }),
        authFetch<TelemetrySnapshot[]>({ url: '/api/telemetry/latest' }),
        authFetch<InsightRow[]>({ url: '/api/insights', params: { limit: 10 } })
      ]);
      setStatusRows(statusData);
      setTelemetry(telemetryData);
      setInsights(insightsData);
    } finally {
      setIsLoading(false);
    }
  }, [authFetch]);

  useEffect(() => {
    void loadData();
    const interval = window.setInterval(() => {
      void loadData();
    }, 60_000);
    return () => window.clearInterval(interval);
  }, [loadData]);

  const latestTelemetryByNode = useMemo(() => {
    const map = new Map<string, TelemetrySnapshot>();
    telemetry.forEach((item) => {
      map.set(item.nodeId, item);
    });
    return Array.from(map.values());
  }, [telemetry]);

  const formatDate = (value: string | null | undefined) =>
    value ? new Date(value).toLocaleString() : '—';

  const classifyHealth = (health: string | null) => {
    if (!health || health === 'ok') {
      return 'ok';
    }
    if (health === 'low_battery') {
      return 'low_battery';
    }
    return 'alert';
  };

  return (
    <div className="dashboard">
      <header>
        <div>
          <h1>VineGuard Overview</h1>
          <p>
            {user?.orgId} • Signed in as <strong>{user?.email}</strong>
          </p>
        </div>
        <button className="logout-button" onClick={logout}>
          Log out
        </button>
      </header>

      {isLoading ? (
        <p>Loading telemetry…</p>
      ) : (
        <div className="grid">
          <section className="panel">
            <h2>Node status</h2>
            <table>
              <thead>
                <tr>
                  <th>Node</th>
                  <th>Site</th>
                  <th>Last seen</th>
                  <th>Battery</th>
                  <th>Health</th>
                </tr>
              </thead>
              <tbody>
                {statusRows.map((row) => (
                  <tr key={row.nodeId}>
                    <td>{row.nodeId}</td>
                    <td>{row.siteId}</td>
                    <td>{formatDate(row.lastSeen)}</td>
                    <td>{row.batteryV != null ? `${row.batteryV.toFixed(2)} V` : '—'}</td>
                    <td>
                      <span className={`badge ${classifyHealth(row.health)}`}>{row.health ?? 'ok'}</span>
                    </td>
                  </tr>
                ))}
                {statusRows.length === 0 && (
                  <tr>
                    <td colSpan={5}>No node status yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>

          <section className="panel">
            <h2>Latest sensors</h2>
            <table>
              <thead>
                <tr>
                  <th>Node</th>
                  <th>Soil moisture</th>
                  <th>Soil temp</th>
                  <th>Air temp</th>
                  <th>Light</th>
                </tr>
              </thead>
              <tbody>
                {latestTelemetryByNode.map((row) => (
                  <tr key={row.nodeId}>
                    <td>{row.nodeId}</td>
                    <td>
                      {row.sensors.soilMoisture != null
                        ? `${Math.round(row.sensors.soilMoisture * 100)}%`
                        : '—'}
                    </td>
                    <td>{row.sensors.soilTempC != null ? `${row.sensors.soilTempC.toFixed(1)}°C` : '—'}</td>
                    <td>{row.sensors.airTempC != null ? `${row.sensors.airTempC.toFixed(1)}°C` : '—'}</td>
                    <td>{row.sensors.lightLux != null ? `${row.sensors.lightLux.toLocaleString()} lx` : '—'}</td>
                  </tr>
                ))}
                {latestTelemetryByNode.length === 0 && (
                  <tr>
                    <td colSpan={5}>Awaiting telemetry…</td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>

          <section className="panel">
            <h2>Insights</h2>
            <ul>
              {insights.map((insight) => (
                <li key={`${insight.nodeId}-${insight.ts}`}>
                  <div className="type">{insight.type.replace('_', ' ')}</div>
                  <div className="ts">{formatDate(insight.ts)}</div>
                  <pre style={{ marginTop: '8px', background: '#f1f5f9', padding: '12px', borderRadius: '8px' }}>
                    {JSON.stringify(insight.payload, null, 2)}
                  </pre>
                </li>
              ))}
              {insights.length === 0 && <li>No insights yet.</li>}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
