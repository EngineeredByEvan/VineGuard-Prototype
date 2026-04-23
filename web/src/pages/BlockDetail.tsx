import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
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
import { RelativeTime, relativeTime } from '../components/RelativeTime';
import { SeverityBadge } from '../components/SeverityBadge';
import { Card } from '../components/ui/card';
import {
  fetchAlerts,
  fetchBlock,
  fetchBlockTelemetry,
  fetchRecommendations,
  fetchVineyard,
} from '../lib/api';
import type { Alert, BlockWithNodes, Node, Recommendation, TelemetryReading } from '../lib/types';

const NODE_COLORS = [
  '#22d3ee', // cyan-400
  '#a78bfa', // violet-400
  '#fb923c', // orange-400
  '#34d399', // emerald-400
  '#f472b6', // pink-400
  '#facc15', // yellow-400
];

function tierLabel(tier: Node['tier']) {
  return tier === 'precision_plus' ? 'Precision+' : 'Basic';
}

function tierBadge(tier: Node['tier']) {
  return tier === 'precision_plus'
    ? 'bg-cyan-500/20 text-cyan-400'
    : 'bg-slate-700 text-slate-300';
}

function NodeCard({ node }: { node: Node }) {
  const navigate = useNavigate();
  return (
    <Card
      className="cursor-pointer p-4 transition-colors hover:border-slate-600 hover:bg-slate-900"
      onClick={() => navigate(`/nodes/${node.id}`)}
    >
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <NodeStatusDot status={node.status} />
          <span className="font-semibold text-white">{node.name}</span>
        </div>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${tierBadge(node.tier)}`}>
          {tierLabel(node.tier)}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-slate-500">Last Seen</span>
          <p className="text-slate-300">
            <RelativeTime iso={node.last_seen_at} fallback="Never" />
          </p>
        </div>
        <div>
          <span className="text-slate-500">Status</span>
          <p className="capitalize text-slate-300">{node.status}</p>
        </div>
        {node.battery_voltage !== null && (
          <div>
            <span className="text-slate-500">Battery</span>
            <p className="text-slate-300">
              {node.battery_voltage.toFixed(2)}V
              {node.battery_pct !== null && (
                <span className="ml-1 text-slate-500">({Math.round(node.battery_pct)}%)</span>
              )}
            </p>
          </div>
        )}
        {node.rssi_last !== null && (
          <div>
            <span className="text-slate-500">RSSI</span>
            <p className="text-slate-300">{node.rssi_last} dBm</p>
          </div>
        )}
      </div>

      <div className="mt-2 text-xs text-emerald-400">View node →</div>
    </Card>
  );
}

function AlertCard({ alert }: { alert: Alert }) {
  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-start gap-3">
        <SeverityBadge severity={alert.severity} />
        <div className="flex-1">
          <p className="font-medium text-white">{alert.title}</p>
          <p className="mt-1 text-sm text-slate-400">{alert.message}</p>
          <p className="mt-1 text-xs text-slate-500">
            {relativeTime(alert.triggered_at)}
          </p>
        </div>
      </div>
    </Card>
  );
}

function RecommendationCard({ rec }: { rec: Recommendation }) {
  const priorityLabel: Record<number, string> = { 1: 'High', 2: 'Medium', 3: 'Low' };
  const priorityClass: Record<number, string> = {
    1: 'bg-red-500/20 text-red-400 border-red-500/30',
    2: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    3: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  };

  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-start gap-3">
        <span
          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${priorityClass[rec.priority]}`}
        >
          {priorityLabel[rec.priority]}
        </span>
        <div className="flex-1">
          <p className="text-sm text-slate-200">{rec.action_text}</p>
          {rec.due_by && (
            <p className="mt-1 text-xs text-slate-500">
              Due: {new Date(rec.due_by).toLocaleDateString()}
            </p>
          )}
        </div>
      </div>
    </Card>
  );
}

export function BlockDetail() {
  const { blockId } = useParams<{ blockId: string }>();
  const navigate = useNavigate();

  const [block, setBlock] = useState<BlockWithNodes | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryReading[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [vineyardName, setVineyardName] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!blockId) return;
    try {
      const [b, tele, als, recommendations] = await Promise.all([
        fetchBlock(blockId),
        fetchBlockTelemetry(blockId, 24),
        fetchAlerts({ blockId, isActive: true }),
        fetchRecommendations({ blockId }),
      ]);
      setBlock(b);
      setTelemetry(tele.slice().sort((a, z) => a.recorded_at.localeCompare(z.recorded_at)));
      setAlerts(als);
      setRecs(recommendations);

      // Fetch vineyard name
      try {
        const v = await fetchVineyard(b.vineyard_id);
        setVineyardName(v.name);
      } catch {
        setVineyardName(b.vineyard_id);
      }

      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load block');
    } finally {
      setLoading(false);
    }
  }, [blockId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-slate-400">Loading block…</p>
      </div>
    );
  }

  if (error || !block) {
    return (
      <div className="p-6">
        <Card className="border-red-500/30 bg-red-900/10 p-5">
          <p className="text-red-400">{error ?? 'Block not found'}</p>
        </Card>
      </div>
    );
  }

  // Build chart data: one entry per timestamp, keyed by node_id
  const nodeIds = block.nodes.map((n) => n.id);
  const nodeMap = Object.fromEntries(block.nodes.map((n) => [n.id, n.name]));

  // Group telemetry readings by time bucket (minute precision) per node
  const chartMap: Record<string, Record<string, number>> = {};
  for (const r of telemetry) {
    if (!r.node_id) continue;
    const minute = r.recorded_at.slice(0, 16); // "YYYY-MM-DDTHH:MM"
    if (!chartMap[minute]) chartMap[minute] = { time: new Date(r.recorded_at).getTime() };
    chartMap[minute][r.node_id] = r.soil_moisture;
  }
  const chartData = Object.entries(chartMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, vals]) => vals);

  function formatTime(ts: number) {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate('/blocks')}
          className="mb-2 text-xs text-slate-500 hover:text-slate-300"
        >
          ← Back to Blocks
        </button>
        <div className="flex flex-wrap items-baseline gap-3">
          <h1 className="text-2xl font-bold text-white">{block.name}</h1>
          <span className="text-slate-400">{block.variety}</span>
          {vineyardName && (
            <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
              {vineyardName}
            </span>
          )}
        </div>
        {block.notes && <p className="mt-1 text-sm text-slate-500">{block.notes}</p>}
      </div>

      {/* Node cards */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Nodes ({block.nodes.length})
        </h2>
        {block.nodes.length === 0 ? (
          <Card className="p-5 text-center text-slate-500">No nodes in this block.</Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {block.nodes.map((node) => (
              <NodeCard key={node.id} node={node} />
            ))}
          </div>
        )}
      </div>

      {/* 24h Soil Moisture Chart */}
      {chartData.length > 0 && (
        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
            24h Soil Moisture Trend (% vol)
          </h2>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
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
                itemStyle={{ color: '#e2e8f0' }}
                labelFormatter={(v) => formatTime(v as number)}
                formatter={(v: number) => [`${v.toFixed(1)}%`]}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
              {nodeIds.map((nid, i) => (
                <Line
                  key={nid}
                  type="monotone"
                  dataKey={nid}
                  name={nodeMap[nid] ?? nid}
                  stroke={NODE_COLORS[i % NODE_COLORS.length]}
                  dot={false}
                  strokeWidth={2}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Active Alerts */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Active Alerts ({alerts.length})
        </h2>
        {alerts.length === 0 ? (
          <Card className="p-5 text-center text-emerald-400">No active alerts for this block.</Card>
        ) : (
          <div className="space-y-3">
            {alerts.map((a) => (
              <AlertCard key={a.id} alert={a} />
            ))}
          </div>
        )}
      </div>

      {/* Recommendations */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Recommendations ({recs.length})
        </h2>
        {recs.length === 0 ? (
          <Card className="p-5 text-center text-slate-500">No pending recommendations.</Card>
        ) : (
          <div className="space-y-3">
            {recs.map((r) => (
              <RecommendationCard key={r.id} rec={r} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
