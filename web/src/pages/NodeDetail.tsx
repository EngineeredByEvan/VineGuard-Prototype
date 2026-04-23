import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { NodeStatusDot } from '../components/NodeStatusDot';
import { RelativeTime } from '../components/RelativeTime';
import { Card } from '../components/ui/card';
import { fetchBlock, fetchNode, fetchNodeTelemetry } from '../lib/api';
import type { BlockWithNodes, Node, TelemetryReading } from '../lib/types';

function tierLabel(tier: Node['tier']) {
  return tier === 'precision_plus' ? 'Precision+' : 'Basic';
}

function tierBadge(tier: Node['tier']) {
  return tier === 'precision_plus'
    ? 'bg-cyan-500/20 text-cyan-400'
    : 'bg-slate-700 text-slate-300';
}

function ReadingItem({
  label,
  value,
  unit,
  accent,
}: {
  label: string;
  value: string | null;
  unit?: string;
  accent?: string;
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
      <span className="text-xs uppercase tracking-wide text-slate-500">{label}</span>
      <p className={`mt-1 text-xl font-bold ${accent ?? 'text-white'}`}>
        {value !== null ? (
          <>
            {value}
            {unit && <span className="ml-1 text-sm font-normal text-slate-400">{unit}</span>}
          </>
        ) : (
          <span className="text-slate-600">—</span>
        )}
      </p>
    </div>
  );
}

function moistureAccent(v: number | null) {
  if (v === null) return 'text-slate-500';
  if (v >= 25) return 'text-emerald-400';
  if (v >= 15) return 'text-amber-400';
  return 'text-red-400';
}

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function NodeDetail() {
  const { nodeId } = useParams<{ nodeId: string }>();
  const navigate = useNavigate();

  const [node, setNode] = useState<Node | null>(null);
  const [block, setBlock] = useState<BlockWithNodes | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryReading[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!nodeId) return;
    try {
      const [n, tele] = await Promise.all([
        fetchNode(nodeId),
        fetchNodeTelemetry(nodeId, 24),
      ]);
      setNode(n);
      const sorted = tele.slice().sort((a, z) => a.recorded_at.localeCompare(z.recorded_at));
      setTelemetry(sorted);

      // Fetch block info for context
      try {
        const b = await fetchBlock(n.block_id);
        setBlock(b);
      } catch {
        // block info is optional context
      }

      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load node');
    } finally {
      setLoading(false);
    }
  }, [nodeId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-slate-400">Loading node…</p>
      </div>
    );
  }

  if (error || !node) {
    return (
      <div className="p-6">
        <Card className="border-red-500/30 bg-red-900/10 p-5">
          <p className="text-red-400">{error ?? 'Node not found'}</p>
        </Card>
      </div>
    );
  }

  const latest = telemetry.length > 0 ? telemetry[telemetry.length - 1] : null;
  const isPrecision = node.tier === 'precision_plus';

  // Build chart data with epoch timestamps
  const chartData = telemetry.map((r) => ({
    time: new Date(r.recorded_at).getTime(),
    soil_moisture: r.soil_moisture,
    soil_temp: r.soil_temp_c,
    ambient_temp: r.ambient_temp_c,
    humidity: r.ambient_humidity,
    leaf_wetness: r.leaf_wetness_pct,
  }));

  return (
    <div className="space-y-6 p-6">
      {/* Back nav */}
      <button
        onClick={() => block ? navigate(`/blocks/${block.id}`) : navigate('/blocks')}
        className="text-xs text-slate-500 hover:text-slate-300"
      >
        ← Back to {block ? block.name : 'Blocks'}
      </button>

      {/* Node header */}
      <div className="flex flex-wrap items-start gap-4">
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-3">
            <NodeStatusDot status={node.status} />
            <h1 className="text-2xl font-bold text-white">{node.name}</h1>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${tierBadge(node.tier)}`}
            >
              {tierLabel(node.tier)}
            </span>
          </div>
          <p className="mt-1 font-mono text-sm text-slate-500">{node.device_id}</p>
          {block && <p className="mt-0.5 text-sm text-slate-400">Block: {block.name}</p>}
        </div>
      </div>

      {/* Health row */}
      <Card className="p-4">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">Status</span>
            <p className="mt-1 flex items-center gap-2 text-sm font-medium capitalize text-slate-200">
              <NodeStatusDot status={node.status} />
              {node.status}
            </p>
          </div>
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">Last Seen</span>
            <p className="mt-1 text-sm font-medium text-slate-200">
              <RelativeTime iso={node.last_seen_at} fallback="Never" />
            </p>
          </div>
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">Battery</span>
            <p className="mt-1 text-sm font-medium text-slate-200">
              {node.battery_voltage !== null ? (
                <>
                  {node.battery_voltage.toFixed(2)}V
                  {node.battery_pct !== null && (
                    <span className="ml-1 text-slate-500">({Math.round(node.battery_pct)}%)</span>
                  )}
                </>
              ) : (
                '—'
              )}
            </p>
          </div>
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">RSSI</span>
            <p className="mt-1 text-sm font-medium text-slate-200">
              {node.rssi_last !== null ? `${node.rssi_last} dBm` : '—'}
            </p>
          </div>
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">Firmware</span>
            <p className="mt-1 font-mono text-sm text-slate-200">{node.firmware_version}</p>
          </div>
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">Installed</span>
            <p className="mt-1 text-sm text-slate-200">
              {new Date(node.installed_at).toLocaleDateString()}
            </p>
          </div>
        </div>
      </Card>

      {/* Current readings */}
      {latest && (
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Latest Readings
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            <ReadingItem
              label="Soil Moisture"
              value={latest.soil_moisture.toFixed(1)}
              unit="%"
              accent={moistureAccent(latest.soil_moisture)}
            />
            <ReadingItem
              label="Soil Temp"
              value={latest.soil_temp_c.toFixed(1)}
              unit="°C"
            />
            <ReadingItem
              label="Ambient Temp"
              value={latest.ambient_temp_c.toFixed(1)}
              unit="°C"
            />
            <ReadingItem
              label="Humidity"
              value={latest.ambient_humidity.toFixed(1)}
              unit="%"
            />
            <ReadingItem
              label="Light"
              value={latest.light_lux.toFixed(0)}
              unit="lux"
            />
            <ReadingItem
              label="Battery"
              value={latest.battery_voltage.toFixed(2)}
              unit="V"
            />
            {latest.pressure_hpa !== null && (
              <ReadingItem
                label="Pressure"
                value={latest.pressure_hpa.toFixed(1)}
                unit="hPa"
              />
            )}
            {isPrecision && latest.leaf_wetness_pct !== null && (
              <ReadingItem
                label="Leaf Wetness"
                value={latest.leaf_wetness_pct.toFixed(1)}
                unit="%"
                accent="text-cyan-400"
              />
            )}
          </div>
        </div>
      )}

      {/* 24h Soil Moisture Chart */}
      {chartData.length > 0 && (
        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
            24h Soil Moisture (% vol)
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <defs>
                <linearGradient id="moistureGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="time"
                type="number"
                scale="time"
                domain={['dataMin', 'dataMax']}
                tickFormatter={formatTime}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
              />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} unit="%" />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#94a3b8' }}
                itemStyle={{ color: '#22d3ee' }}
                labelFormatter={(v) => formatTime(v as number)}
                formatter={(v: number) => [`${v.toFixed(1)}%`, 'Soil Moisture']}
              />
              <Area
                type="monotone"
                dataKey="soil_moisture"
                stroke="#22d3ee"
                strokeWidth={2}
                fill="url(#moistureGrad)"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* 24h Ambient Temp + Humidity Chart */}
      {chartData.length > 0 && (
        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
            24h Ambient Temperature & Humidity
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 5, right: 40, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="time"
                type="number"
                scale="time"
                domain={['dataMin', 'dataMax']}
                tickFormatter={formatTime}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
              />
              <YAxis
                yAxisId="temp"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                unit="°C"
              />
              <YAxis
                yAxisId="humid"
                orientation="right"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                unit="%"
              />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#94a3b8' }}
                itemStyle={{ color: '#e2e8f0' }}
                labelFormatter={(v) => formatTime(v as number)}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
              <Line
                yAxisId="temp"
                type="monotone"
                dataKey="ambient_temp"
                name="Temp (°C)"
                stroke="#fb923c"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="humid"
                type="monotone"
                dataKey="humidity"
                name="Humidity (%)"
                stroke="#818cf8"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Precision+ Leaf Wetness Chart */}
      {isPrecision && chartData.some((d) => d.leaf_wetness !== null) && (
        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
            24h Leaf Wetness (%)
          </h2>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <defs>
                <linearGradient id="leafGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#34d399" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#34d399" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="time"
                type="number"
                scale="time"
                domain={['dataMin', 'dataMax']}
                tickFormatter={formatTime}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
              />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} unit="%" />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#94a3b8' }}
                itemStyle={{ color: '#34d399' }}
                labelFormatter={(v) => formatTime(v as number)}
                formatter={(v: number) => [`${v.toFixed(1)}%`, 'Leaf Wetness']}
              />
              <Area
                type="monotone"
                dataKey="leaf_wetness"
                stroke="#34d399"
                strokeWidth={2}
                fill="url(#leafGrad)"
                dot={false}
                connectNulls
              />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  );
}
