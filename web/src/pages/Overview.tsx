import { useCallback, useEffect, useState } from 'react';
import { Activity, AlertTriangle, Droplets, Thermometer, Wind, X, Zap } from 'lucide-react';
import { Area, AreaChart, ResponsiveContainer } from 'recharts';

import { fetchBlockTelemetry, fetchDashboardOverview, fetchVineyards } from '../lib/api';
import type { BlockSummary, DashboardOverview, TelemetryReading } from '../lib/types';

// ── GDD phenological milestones ─────────────────────────────────────────
const GDD_MILESTONES = [
  { gdd: 147, label: 'Bud Break' },
  { gdd: 350, label: 'Flowering' },
  { gdd: 550, label: 'Fruit Set' },
  { gdd: 810, label: 'Veraison' },
  { gdd: 1100, label: 'Ripening' },
  { gdd: 1620, label: 'Harvest' },
];
const MAX_GDD = 1620;

// ── Moisture colour helpers ─────────────────────────────────────────────

function moistureCardClass(vwc: number | null): string {
  if (vwc === null) return 'bg-slate-900 border-slate-800';
  if (vwc < 14) return 'bg-red-950/80 border-red-800/40';
  if (vwc < 19) return 'bg-orange-950/60 border-orange-800/30';
  if (vwc < 27) return 'bg-slate-900 border-slate-700/40';
  return 'bg-sky-950/30 border-sky-900/30';
}

function moistureValueClass(vwc: number | null): string {
  if (vwc === null) return 'text-slate-500';
  if (vwc < 14) return 'text-red-400';
  if (vwc < 19) return 'text-amber-400';
  return 'text-emerald-400';
}

function statusDotClass(vwc: number | null, alerts: number): string {
  if (alerts > 0) return vwc !== null && vwc < 15 ? 'bg-red-500' : 'bg-amber-500';
  if (vwc === null) return 'bg-slate-600';
  if (vwc < 19) return 'bg-amber-400';
  return 'bg-emerald-400';
}

// ── Mini sparkline ──────────────────────────────────────────────────────

function Sparkline({ values, color }: { values: number[]; color: string }) {
  const safeId = `sg${color.replace(/[^a-zA-Z0-9]/g, '')}`;
  if (values.length < 2) {
    return <div className="h-12 rounded opacity-10" style={{ background: color }} />;
  }
  const pts = values.map((v, i) => ({ i, v }));
  return (
    <ResponsiveContainer width="100%" height={48}>
      <AreaChart data={pts} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
        <defs>
          <linearGradient id={safeId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.35} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#${safeId})`}
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ── Sensor metric row ───────────────────────────────────────────────────

function SensorMetric({
  icon: Icon,
  label,
  value,
  badge,
  color,
  values,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  badge?: string;
  color: string;
  values: number[];
}) {
  return (
    <div className="border-b border-slate-800/70 px-4 py-4 last:border-0">
      <div className="mb-1 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Icon className="h-3.5 w-3.5 text-slate-500" />
          <span className="text-xs text-slate-400">{label}</span>
        </div>
        {badge && (
          <span
            className="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
            style={{ color, background: `${color}22` }}
          >
            {badge}
          </span>
        )}
      </div>
      <p className="mb-2 text-xl font-bold" style={{ color }}>
        {value}
      </p>
      <Sparkline values={values} color={color} />
    </div>
  );
}

// ── Block card in the moisture grid ────────────────────────────────────

function BlockCard({
  block,
  selected,
  onClick,
}: {
  block: BlockSummary;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`relative w-full rounded-xl border p-4 text-left transition-all duration-200 hover:brightness-110 ${moistureCardClass(
        block.avg_soil_moisture,
      )} ${selected ? 'ring-2 ring-emerald-500/60' : ''}`}
    >
      {/* Status dot */}
      <span
        className={`absolute right-3 top-3 h-2.5 w-2.5 rounded-full ${statusDotClass(
          block.avg_soil_moisture,
          block.active_alert_count,
        )}`}
      />

      <p className="mb-0.5 pr-5 text-sm font-semibold text-white">{block.name}</p>
      <p className="mb-3 text-xs text-slate-400">{block.variety}</p>

      <div className="flex items-end gap-1">
        <p className={`text-2xl font-bold ${moistureValueClass(block.avg_soil_moisture)}`}>
          {block.avg_soil_moisture !== null
            ? `${block.avg_soil_moisture.toFixed(0)}%`
            : '—'}
        </p>
        {block.avg_soil_moisture !== null && (
          <p className="mb-0.5 text-xs text-slate-500">VWC</p>
        )}
      </div>

      {block.active_alert_count > 0 && (
        <div className="mt-2 flex items-center gap-1">
          <AlertTriangle className="h-3 w-3 text-red-400" />
          <span className="text-xs text-red-400">
            {block.active_alert_count} alert{block.active_alert_count !== 1 ? 's' : ''}
          </span>
        </div>
      )}

      <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
        <span>
          {block.avg_temp !== null ? `${block.avg_temp.toFixed(1)}°C` : '—'}
        </span>
        <span>
          {block.node_count} node{block.node_count !== 1 ? 's' : ''}
        </span>
      </div>
    </button>
  );
}

// ── Sensor detail panel ─────────────────────────────────────────────────

function SensorPanel({
  block,
  telemetry,
  loading,
  onClose,
}: {
  block: BlockSummary;
  telemetry: TelemetryReading[];
  loading: boolean;
  onClose: () => void;
}) {
  const sorted = [...telemetry].reverse().slice(-40);
  const latest = telemetry[0] ?? null;

  const moistureValues = sorted.map((r) => r.soil_moisture);
  const tempValues = sorted.map((r) => r.ambient_temp_c);
  const humidityValues = sorted.map((r) => r.ambient_humidity);
  const leafValues = sorted
    .filter((r) => r.leaf_wetness_pct !== null)
    .map((r) => r.leaf_wetness_pct as number);

  const moistureColor =
    latest === null
      ? '#64748b'
      : latest.soil_moisture < 14
      ? '#ef4444'
      : latest.soil_moisture < 20
      ? '#f59e0b'
      : '#10b981';

  return (
    <div className="fixed inset-y-0 right-0 z-20 flex w-72 flex-col overflow-hidden border-l border-slate-800 bg-slate-900 shadow-2xl top-14 md:top-0">
      {/* Header */}
      <div className="flex flex-shrink-0 items-center justify-between border-b border-slate-800 px-4 py-3">
        <div>
          <p className="text-[10px] uppercase tracking-widest text-slate-500">Sensors</p>
          <p className="text-sm font-semibold text-white">{block.name}</p>
          <p className="text-xs text-slate-500">{block.variety}</p>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-slate-800 hover:text-slate-300"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Body */}
      {loading ? (
        <div className="flex flex-1 items-center justify-center">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            Loading sensor data…
          </div>
        </div>
      ) : telemetry.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
          <Droplets className="h-8 w-8 text-slate-700" />
          <p className="text-xs text-slate-500">
            No readings in the last 24 hours.
            <br />
            Make sure the simulator is running.
          </p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          <SensorMetric
            icon={Droplets}
            label="Soil Moisture"
            value={latest ? `${latest.soil_moisture.toFixed(1)}%` : '—'}
            badge="VWC"
            color={moistureColor}
            values={moistureValues}
          />
          <SensorMetric
            icon={Thermometer}
            label="Temperature"
            value={latest ? `${latest.ambient_temp_c.toFixed(1)}°C` : '—'}
            badge="Air"
            color="#f59e0b"
            values={tempValues}
          />
          <SensorMetric
            icon={Wind}
            label="Humidity"
            value={latest ? `${latest.ambient_humidity.toFixed(0)}%` : '—'}
            badge="RH"
            color="#38bdf8"
            values={humidityValues}
          />
          {leafValues.length > 0 && (
            <SensorMetric
              icon={Activity}
              label="Leaf Wetness"
              value={
                latest?.leaf_wetness_pct != null
                  ? `${latest.leaf_wetness_pct.toFixed(1)}%`
                  : '—'
              }
              badge={
                (latest?.leaf_wetness_pct ?? 0) > 60
                  ? 'High Risk'
                  : (latest?.leaf_wetness_pct ?? 0) > 30
                  ? 'Moderate'
                  : 'Low'
              }
              color="#a78bfa"
              values={leafValues}
            />
          )}

          {latest && (
            <div className="space-y-2 px-4 py-4">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500">Battery</span>
                <span
                  className={
                    latest.battery_voltage < 3.4
                      ? 'text-red-400'
                      : latest.battery_voltage < 3.6
                      ? 'text-amber-400'
                      : 'text-emerald-400'
                  }
                >
                  {latest.battery_voltage.toFixed(2)} V
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500">Last reading</span>
                <span className="text-slate-300">
                  {new Date(latest.recorded_at).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500">Light</span>
                <span className="text-slate-300">
                  {latest.light_lux >= 1000
                    ? `${(latest.light_lux / 1000).toFixed(1)}k`
                    : latest.light_lux.toFixed(0)}{' '}
                  lux
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Stat card ───────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  accent = 'text-white',
  icon: Icon,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
  icon: React.ElementType;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-5 py-4">
      <div className="mb-2 flex items-center gap-2">
        <Icon className="h-3.5 w-3.5 text-slate-500" />
        <span className="text-xs uppercase tracking-wide text-slate-500">{label}</span>
      </div>
      <p className={`text-3xl font-bold ${accent}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

// ── GDD progress strip ──────────────────────────────────────────────────

function GDDBar({ gdd }: { gdd: number | null }) {
  const pct = gdd !== null ? Math.min(100, (gdd / MAX_GDD) * 100) : 0;
  const reached = GDD_MILESTONES.filter((m) => (gdd ?? 0) >= m.gdd);
  const next = GDD_MILESTONES.find((m) => (gdd ?? 0) < m.gdd);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-5 py-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-slate-500">
          Season GDD Progress
        </span>
        <div className="flex items-center gap-2">
          {reached.length > 0 && (
            <span className="text-xs text-emerald-400">
              ✓ {reached[reached.length - 1].label}
            </span>
          )}
          {next && (
            <span className="text-xs text-slate-500">
              → {next.label} ({next.gdd})
            </span>
          )}
        </div>
      </div>
      <div className="relative mb-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-emerald-700 to-emerald-400 transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
        {GDD_MILESTONES.map((m) => (
          <div
            key={m.gdd}
            className={`absolute top-0 h-full w-px ${
              (gdd ?? 0) >= m.gdd ? 'bg-emerald-200/20' : 'bg-slate-700'
            }`}
            style={{ left: `${(m.gdd / MAX_GDD) * 100}%` }}
          />
        ))}
      </div>
      <div className="flex justify-between">
        {GDD_MILESTONES.map((m) => (
          <span
            key={m.gdd}
            className={`text-[9px] ${
              (gdd ?? 0) >= m.gdd ? 'text-emerald-500' : 'text-slate-600'
            }`}
          >
            {m.label}
          </span>
        ))}
      </div>
    </div>
  );
}

// ── Main component ──────────────────────────────────────────────────────

export function Overview() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [selectedBlock, setSelectedBlock] = useState<BlockSummary | null>(null);
  const [sensorTelemetry, setSensorTelemetry] = useState<TelemetryReading[]>([]);
  const [sensorLoading, setSensorLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const load = useCallback(async () => {
    try {
      const vineyards = await fetchVineyards();
      if (vineyards.length === 0) {
        setError('No vineyards found. Run the seed script first.');
        setLoading(false);
        return;
      }
      const ov = await fetchDashboardOverview(vineyards[0].id);
      setOverview(ov);
      setLastUpdated(new Date());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load overview');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 30_000);
    return () => clearInterval(t);
  }, [load]);

  const handleBlockClick = useCallback(
    async (block: BlockSummary) => {
      if (selectedBlock?.id === block.id) {
        setSelectedBlock(null);
        setSensorTelemetry([]);
        return;
      }
      setSelectedBlock(block);
      setSensorLoading(true);
      setSensorTelemetry([]);
      try {
        const data = await fetchBlockTelemetry(block.id, 24);
        setSensorTelemetry(data);
      } finally {
        setSensorLoading(false);
      }
    },
    [selectedBlock],
  );

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex items-center gap-3">
          <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
          <p className="text-sm text-slate-400">Connecting to VineGuard…</p>
        </div>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="p-6">
        <div className="rounded-xl border border-red-800/30 bg-red-950/20 p-5">
          <p className="text-sm text-red-400">{error ?? 'Unknown error'}</p>
        </div>
      </div>
    );
  }

  // Aggregate stats from blocks that have recent telemetry
  const blocksWithData = overview.block_summaries.filter(
    (b) => b.avg_soil_moisture !== null,
  );
  const avgVWC =
    blocksWithData.length > 0
      ? blocksWithData.reduce((s, b) => s + (b.avg_soil_moisture ?? 0), 0) /
        blocksWithData.length
      : null;
  const avgTemp =
    blocksWithData.length > 0
      ? blocksWithData.reduce((s, b) => s + (b.avg_temp ?? 0), 0) /
        blocksWithData.length
      : null;
  const totalNodes = overview.online_node_count + overview.stale_node_count;

  return (
    <div className={`min-h-full transition-all duration-300 ${selectedBlock ? 'pr-72' : ''}`}>
      {/* ── Sticky header ─────────────────────────────────────────────── */}
      <div className="sticky top-0 z-10 border-b border-slate-800 bg-slate-950/90 px-6 py-4 backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold text-white">{overview.vineyard_name}</h1>
            <p className="text-xs text-slate-500">
              {new Date().toLocaleDateString([], {
                weekday: 'long',
                month: 'long',
                day: 'numeric',
              })}
              {lastUpdated && (
                <>
                  {' · '}Updated{' '}
                  {lastUpdated.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </>
              )}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {overview.total_active_alerts > 0 && (
              <div className="flex items-center gap-1.5 rounded-full border border-red-800/40 bg-red-950/40 px-3 py-1.5">
                <AlertTriangle className="h-3.5 w-3.5 text-red-400" />
                <span className="text-xs font-semibold text-red-400">
                  {overview.total_active_alerts} Alert
                  {overview.total_active_alerts !== 1 ? 's' : ''}
                </span>
              </div>
            )}
            {overview.gdd_season_total !== null && (
              <div className="flex items-center gap-1.5 rounded-full border border-emerald-800/40 bg-emerald-950/40 px-3 py-1.5">
                <Zap className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-xs font-semibold text-emerald-400">
                  GDD {Math.round(overview.gdd_season_total)}
                </span>
              </div>
            )}
            <div className="flex items-center gap-1.5 rounded-full border border-slate-700 px-3 py-1.5">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              <span className="text-xs text-emerald-400">Live</span>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-5 p-6">
        {/* ── Stat row ──────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard
            label="Avg Soil VWC"
            value={avgVWC !== null ? `${avgVWC.toFixed(1)}%` : '—'}
            accent={
              avgVWC === null
                ? 'text-slate-500'
                : avgVWC < 15
                ? 'text-red-400'
                : avgVWC < 22
                ? 'text-amber-400'
                : 'text-emerald-400'
            }
            icon={Droplets}
            sub={
              blocksWithData.length > 0
                ? `across ${blocksWithData.length} block${blocksWithData.length !== 1 ? 's' : ''}`
                : 'No readings yet — start the simulator'
            }
          />
          <StatCard
            label="Avg Temp"
            value={avgTemp !== null ? `${avgTemp.toFixed(1)}°C` : '—'}
            accent="text-amber-400"
            icon={Thermometer}
            sub="Ambient air"
          />
          <StatCard
            label="Active Alerts"
            value={String(overview.total_active_alerts)}
            accent={overview.total_active_alerts > 0 ? 'text-red-400' : 'text-emerald-400'}
            icon={AlertTriangle}
            sub={`${overview.online_node_count} / ${totalNodes} nodes online`}
          />
          <StatCard
            label="Season GDD"
            value={
              overview.gdd_season_total !== null
                ? Math.round(overview.gdd_season_total).toString()
                : '—'
            }
            accent="text-emerald-400"
            icon={Zap}
            sub={
              overview.gdd_date
                ? `as of ${new Date(overview.gdd_date).toLocaleDateString()}`
                : 'Accumulated total'
            }
          />
        </div>

        {/* ── GDD bar ───────────────────────────────────────────────────── */}
        <GDDBar gdd={overview.gdd_season_total} />

        {/* ── Block moisture map ────────────────────────────────────────── */}
        <div>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
              Block Moisture Map
            </h2>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span>Soil VWC%</span>
              <div className="flex items-center gap-1.5">
                <span className="text-red-400">Low</span>
                <div className="h-1.5 w-20 rounded-full bg-gradient-to-r from-red-800 via-amber-700 to-emerald-600" />
                <span className="text-emerald-400">High</span>
              </div>
            </div>
          </div>

          {overview.block_summaries.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center text-sm text-slate-500">
              No blocks found. Run <code className="text-slate-400">python3 tools/seed_demo.py</code> to add demo data.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {overview.block_summaries.map((block) => (
                <BlockCard
                  key={block.id}
                  block={block}
                  selected={selectedBlock?.id === block.id}
                  onClick={() => handleBlockClick(block)}
                />
              ))}
            </div>
          )}
        </div>

        {/* ── Network footer ────────────────────────────────────────────── */}
        <div className="rounded-xl border border-slate-800/60 bg-slate-900/30 px-5 py-3">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-1.5 text-xs">
            <span className="font-medium uppercase tracking-widest text-slate-500">
              Network
            </span>
            <div className="flex items-center gap-1.5">
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  overview.online_node_count > 0 ? 'bg-emerald-400' : 'bg-slate-600'
                }`}
              />
              <span className="text-slate-400">
                Nodes online:{' '}
                <span className="text-slate-200">
                  {overview.online_node_count} / {totalNodes}
                </span>
              </span>
            </div>
            {overview.stale_node_count > 0 && (
              <span className="text-amber-500">
                {overview.stale_node_count} stale
              </span>
            )}
            {lastUpdated && (
              <span className="text-slate-500">
                Last sync:{' '}
                <span className="text-slate-400">
                  {lastUpdated.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </span>
            )}
            {overview.block_summaries.length > 0 && (
              <span className="text-slate-600">
                Click a block to view sensor details
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ── Sensor panel ─────────────────────────────────────────────────── */}
      {selectedBlock && (
        <SensorPanel
          block={selectedBlock}
          telemetry={sensorTelemetry}
          loading={sensorLoading}
          onClose={() => {
            setSelectedBlock(null);
            setSensorTelemetry([]);
          }}
        />
      )}
    </div>
  );
}
