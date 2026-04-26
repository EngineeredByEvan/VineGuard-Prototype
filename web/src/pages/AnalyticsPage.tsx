import { useEffect, useState } from 'react';
import {
  Activity,
  BarChart2,
  Droplets,
  Thermometer,
  Wind,
  Zap,
} from 'lucide-react';
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

import { fetchBlock, fetchBlocks, fetchNodeTelemetry, fetchVineyards } from '../lib/api';
import type { Block, BlockWithNodes, TelemetryReading } from '../lib/types';

const HOURS_OPTIONS = [
  { label: '6h', value: 6 },
  { label: '24h', value: 24 },
  { label: '48h', value: 48 },
  { label: '7d', value: 168 },
];

function fmtTick(ts: string, hours: number): string {
  const d = new Date(ts);
  if (hours <= 48) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function ChartCard({
  title,
  icon: Icon,
  color,
  children,
}: {
  title: string;
  icon: React.ElementType;
  color: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <div className="mb-4 flex items-center gap-2">
        <Icon className="h-4 w-4 flex-shrink-0" style={{ color }} />
        <h3 className="text-sm font-semibold text-slate-300">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function CustomTooltip({
  active,
  payload,
  label,
  unit = '',
}: {
  active?: boolean;
  payload?: { color: string; name: string; value: number }[];
  label?: string;
  unit?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 shadow-xl">
      <p className="mb-1 text-[10px] text-slate-400">
        {label ? new Date(label).toLocaleString() : ''}
      </p>
      {payload.map((p) => (
        <p key={p.name} className="text-sm font-semibold" style={{ color: p.color }}>
          {p.name}: {p.value.toFixed(1)}
          {unit}
        </p>
      ))}
    </div>
  );
}

const axisStyle = { fill: '#475569', fontSize: 10 };
const gridStyle = { strokeDasharray: '3 3', stroke: '#1e293b' };

export function AnalyticsPage() {
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [selectedBlockId, setSelectedBlockId] = useState<string>('');
  const [blockDetail, setBlockDetail] = useState<BlockWithNodes | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string>('');
  const [telemetry, setTelemetry] = useState<TelemetryReading[]>([]);
  const [hours, setHours] = useState(24);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchVineyards()
      .then((vs) => {
        if (vs.length === 0) return;
        return fetchBlocks(vs[0].id);
      })
      .then((bs) => {
        if (!bs || bs.length === 0) return;
        setBlocks(bs);
        setSelectedBlockId(bs[0].id);
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'));
  }, []);

  useEffect(() => {
    if (!selectedBlockId) return;
    fetchBlock(selectedBlockId).then((bd) => {
      setBlockDetail(bd);
      setSelectedNodeId(bd.nodes[0]?.id ?? '');
    });
  }, [selectedBlockId]);

  useEffect(() => {
    if (!selectedNodeId) return;
    setLoading(true);
    setTelemetry([]);
    fetchNodeTelemetry(selectedNodeId, hours)
      .then(setTelemetry)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load telemetry'))
      .finally(() => setLoading(false));
  }, [selectedNodeId, hours]);

  const chartData = [...telemetry].reverse();
  const hasLeafWet = chartData.some((r) => r.leaf_wetness_pct !== null);

  return (
    <div className="space-y-5 p-6">
      {/* Header + controls */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold text-white">Analytics</h1>
          <p className="text-xs text-slate-500">Historical sensor trends per node</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedBlockId}
            onChange={(e) => setSelectedBlockId(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 focus:border-emerald-500 focus:outline-none"
          >
            <option value="" disabled>Select block…</option>
            {blocks.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>

          {blockDetail && blockDetail.nodes.length > 0 && (
            <select
              value={selectedNodeId}
              onChange={(e) => setSelectedNodeId(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 focus:border-emerald-500 focus:outline-none"
            >
              {blockDetail.nodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.name} · {n.device_id}
                </option>
              ))}
            </select>
          )}

          <div className="flex overflow-hidden rounded-lg border border-slate-700">
            {HOURS_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setHours(opt.value)}
                className={`px-3 py-2 text-xs font-medium transition-colors ${
                  hours === opt.value
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-800/30 bg-red-950/20 p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="flex items-center gap-3">
            <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
            <span className="text-sm text-slate-400">Loading telemetry…</span>
          </div>
        </div>
      ) : chartData.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40">
          <BarChart2 className="h-10 w-10 text-slate-700" />
          <div className="text-center">
            <p className="text-sm font-medium text-slate-400">No data for this period</p>
            <p className="mt-1 text-xs text-slate-600">
              Start the simulator:{' '}
              <code className="text-slate-500">docker compose --profile demo up -d</code>
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
          {/* Soil Moisture */}
          <ChartCard title="Soil Moisture (VWC %)" icon={Droplets} color="#10b981">
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="gm" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid {...gridStyle} />
                <XAxis
                  dataKey="recorded_at"
                  tickFormatter={(v) => fmtTick(v, hours)}
                  tick={axisStyle}
                  minTickGap={50}
                />
                <YAxis tick={axisStyle} domain={[0, 100]} unit="%" width={40} />
                <Tooltip content={<CustomTooltip unit="%" />} />
                <Area
                  type="monotone"
                  dataKey="soil_moisture"
                  name="VWC"
                  stroke="#10b981"
                  strokeWidth={2}
                  fill="url(#gm)"
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Temperature */}
          <ChartCard title="Temperature (°C)" icon={Thermometer} color="#f59e0b">
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData}>
                <CartesianGrid {...gridStyle} />
                <XAxis
                  dataKey="recorded_at"
                  tickFormatter={(v) => fmtTick(v, hours)}
                  tick={axisStyle}
                  minTickGap={50}
                />
                <YAxis tick={axisStyle} unit="°" width={35} />
                <Tooltip content={<CustomTooltip unit="°C" />} />
                <Legend wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }} />
                <Line
                  type="monotone"
                  dataKey="ambient_temp_c"
                  name="Air"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="soil_temp_c"
                  name="Soil"
                  stroke="#fb923c"
                  strokeWidth={1.5}
                  strokeDasharray="4 2"
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Humidity */}
          <ChartCard title="Relative Humidity (%)" icon={Wind} color="#38bdf8">
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="gh" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid {...gridStyle} />
                <XAxis
                  dataKey="recorded_at"
                  tickFormatter={(v) => fmtTick(v, hours)}
                  tick={axisStyle}
                  minTickGap={50}
                />
                <YAxis tick={axisStyle} domain={[0, 100]} unit="%" width={40} />
                <Tooltip content={<CustomTooltip unit="%" />} />
                <Area
                  type="monotone"
                  dataKey="ambient_humidity"
                  name="RH"
                  stroke="#38bdf8"
                  strokeWidth={2}
                  fill="url(#gh)"
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Light Lux */}
          <ChartCard title="Light Intensity (lux)" icon={Zap} color="#a78bfa">
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="gl" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#a78bfa" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#a78bfa" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid {...gridStyle} />
                <XAxis
                  dataKey="recorded_at"
                  tickFormatter={(v) => fmtTick(v, hours)}
                  tick={axisStyle}
                  minTickGap={50}
                />
                <YAxis
                  tick={axisStyle}
                  width={45}
                  tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v))}
                />
                <Tooltip content={<CustomTooltip unit=" lux" />} />
                <Area
                  type="monotone"
                  dataKey="light_lux"
                  name="Lux"
                  stroke="#a78bfa"
                  strokeWidth={2}
                  fill="url(#gl)"
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Leaf Wetness — precision_plus nodes only */}
          {hasLeafWet && (
            <ChartCard title="Leaf Wetness (%)" icon={Activity} color="#34d399">
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="glw" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#34d399" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid {...gridStyle} />
                  <XAxis
                    dataKey="recorded_at"
                    tickFormatter={(v) => fmtTick(v, hours)}
                    tick={axisStyle}
                    minTickGap={50}
                  />
                  <YAxis tick={axisStyle} domain={[0, 100]} unit="%" width={40} />
                  <Tooltip content={<CustomTooltip unit="%" />} />
                  <Area
                    type="monotone"
                    dataKey="leaf_wetness_pct"
                    name="Leaf Wet"
                    stroke="#34d399"
                    strokeWidth={2}
                    fill="url(#glw)"
                    dot={false}
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </ChartCard>
          )}
        </div>
      )}
    </div>
  );
}
