import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { MoistureBar } from '../components/MoistureBar';
import { Card } from '../components/ui/card';
import { fetchDashboardOverview, fetchGDD, fetchVineyards } from '../lib/api';
import type { BlockSummary, DashboardOverview, GDDEntry } from '../lib/types';

const GDD_MILESTONES = [147, 350, 550, 810, 1100, 1620];

function getMilestoneInfo(gdd: number | null) {
  if (gdd === null) return { lastPassed: null, next: GDD_MILESTONES[0], pct: 0, prevMilestone: 0 };
  let lastPassed: number | null = null;
  let prevMilestone = 0;
  for (const m of GDD_MILESTONES) {
    if (gdd >= m) {
      lastPassed = m;
      prevMilestone = m;
    }
  }
  const next = GDD_MILESTONES.find((m) => m > gdd) ?? null;
  const from = lastPassed ?? 0;
  const to = next ?? (lastPassed ?? GDD_MILESTONES[GDD_MILESTONES.length - 1]);
  const pct = to === from ? 100 : Math.min(100, ((gdd - from) / (to - from)) * 100);
  return { lastPassed, next, pct, prevMilestone };
}

function GDDProgressCard({ gdd, gddDate }: { gdd: number | null; gddDate: string | null }) {
  const { lastPassed, next, pct } = getMilestoneInfo(gdd);

  return (
    <Card className="p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
          Growing Degree Days (Season Total)
        </h2>
        {gddDate && (
          <span className="text-xs text-slate-500">as of {new Date(gddDate).toLocaleDateString()}</span>
        )}
      </div>

      <div className="mb-4 flex items-end gap-3">
        <span className="text-4xl font-bold text-white">
          {gdd !== null ? Math.round(gdd) : '—'}
        </span>
        <span className="mb-1 text-sm text-slate-400">GDD</span>
      </div>

      {gdd !== null && (
        <>
          <div className="mb-2 flex justify-between text-xs text-slate-500">
            <span>Last milestone: {lastPassed !== null ? lastPassed : 'None yet'}</span>
            <span>Next: {next !== null ? next : 'All milestones reached!'}</span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-3 rounded-full bg-emerald-400 transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {GDD_MILESTONES.map((m) => (
              <span
                key={m}
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  gdd >= m
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-slate-800 text-slate-500'
                }`}
              >
                {m}
              </span>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: number | string;
  accent?: string;
}) {
  return (
    <Card className="flex flex-col gap-1 p-4">
      <span className="text-xs uppercase tracking-wide text-slate-500">{label}</span>
      <span className={`text-3xl font-bold ${accent ?? 'text-white'}`}>{value}</span>
    </Card>
  );
}

function BlockHealthCard({ block }: { block: BlockSummary }) {
  const navigate = useNavigate();
  const hasAlerts = block.active_alert_count > 0;

  return (
    <Card
      className="cursor-pointer p-4 transition-colors hover:border-slate-600 hover:bg-slate-900"
      onClick={() => navigate(`/blocks/${block.id}`)}
    >
      <div className="mb-3 flex items-start justify-between">
        <div>
          <p className="font-semibold text-white">{block.name}</p>
          <p className="text-xs text-slate-500">{block.variety}</p>
        </div>
        {hasAlerts && (
          <span className="rounded-full bg-red-500/20 px-2 py-0.5 text-xs font-semibold text-red-400">
            {block.active_alert_count} alert{block.active_alert_count !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      <div className="mb-3 space-y-1">
        <div className="flex justify-between text-xs">
          <span className="text-slate-400">Soil Moisture</span>
          <span
            className={
              block.avg_soil_moisture === null
                ? 'text-slate-500'
                : block.avg_soil_moisture >= 25
                ? 'text-emerald-400'
                : block.avg_soil_moisture >= 15
                ? 'text-amber-400'
                : 'text-red-400'
            }
          >
            {block.avg_soil_moisture !== null ? `${block.avg_soil_moisture.toFixed(1)}%` : '—'}
          </span>
        </div>
        <MoistureBar value={block.avg_soil_moisture} />
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-slate-500">Avg Temp</span>
          <p className="font-medium text-slate-200">
            {block.avg_temp !== null ? `${block.avg_temp.toFixed(1)}°C` : '—'}
          </p>
        </div>
        <div>
          <span className="text-slate-500">Nodes</span>
          <p className="font-medium text-slate-200">{block.node_count}</p>
        </div>
      </div>

      {block.last_reading_at && (
        <p className="mt-2 text-xs text-slate-600">
          Last reading:{' '}
          {new Date(block.last_reading_at).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
      )}
    </Card>
  );
}

export function Overview() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [gddHistory, setGddHistory] = useState<GDDEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const vineyards = await fetchVineyards();
      if (vineyards.length === 0) {
        setError('No vineyards found.');
        setLoading(false);
        return;
      }
      const firstId = vineyards[0].id;
      const [ov, gdd] = await Promise.all([
        fetchDashboardOverview(firstId),
        fetchGDD(firstId, 30),
      ]);
      setOverview(ov);
      setGddHistory(gdd);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load overview');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, 60_000);
    return () => clearInterval(timer);
  }, [load]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-slate-400">Loading overview…</p>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="p-6">
        <Card className="border-red-500/30 bg-red-900/10 p-5">
          <p className="text-red-400">{error ?? 'Unknown error'}</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">{overview.vineyard_name}</h1>
        <p className="text-sm text-slate-400">Dashboard Overview</p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <StatCard
          label="Active Alerts"
          value={overview.total_active_alerts}
          accent={overview.total_active_alerts > 0 ? 'text-red-400' : 'text-emerald-400'}
        />
        <StatCard label="Online Nodes" value={overview.online_node_count} accent="text-emerald-400" />
        <StatCard
          label="Stale Nodes"
          value={overview.stale_node_count}
          accent={overview.stale_node_count > 0 ? 'text-amber-400' : 'text-slate-300'}
        />
      </div>

      {/* GDD Progress */}
      <GDDProgressCard gdd={overview.gdd_season_total} gddDate={overview.gdd_date} />

      {/* Block health grid */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Block Health
        </h2>
        {overview.block_summaries.length === 0 ? (
          <Card className="p-5 text-center text-slate-500">No blocks found.</Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {overview.block_summaries.map((block) => (
              <BlockHealthCard key={block.id} block={block} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
