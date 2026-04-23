import { useCallback, useEffect, useState } from 'react';

import { RelativeTime } from '../components/RelativeTime';
import { SeverityBadge } from '../components/SeverityBadge';
import { Card } from '../components/ui/card';
import { fetchAlerts, resolveAlert } from '../lib/api';
import type { Alert } from '../lib/types';

type SeverityFilter = 'all' | 'critical' | 'warning' | 'info';
type StatusFilter = 'active' | 'all';

const SEVERITY_ORDER: Record<Alert['severity'], number> = {
  critical: 0,
  warning: 1,
  info: 2,
};

function AlertCard({
  alert,
  onResolved,
}: {
  alert: Alert;
  onResolved: (id: string) => void;
}) {
  const [resolving, setResolving] = useState(false);

  async function handleResolve() {
    setResolving(true);
    try {
      await resolveAlert(alert.id);
      onResolved(alert.id);
    } catch (e: unknown) {
      console.error('Failed to resolve alert', e);
    } finally {
      setResolving(false);
    }
  }

  const borderAccent =
    alert.severity === 'critical'
      ? 'border-red-500/30'
      : alert.severity === 'warning'
      ? 'border-amber-500/30'
      : 'border-blue-500/30';

  return (
    <Card className={`p-4 ${borderAccent}`}>
      <div className="flex flex-wrap items-start gap-3">
        <SeverityBadge severity={alert.severity} />

        <div className="flex-1 min-w-0">
          <p className="font-semibold text-white">{alert.title}</p>
          <p className="mt-1 text-sm text-slate-400">{alert.message}</p>

          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-500">
            <span>
              Triggered: <RelativeTime iso={alert.triggered_at} />
            </span>
            {!alert.is_active && alert.resolved_at && (
              <span className="text-emerald-500">
                Resolved: <RelativeTime iso={alert.resolved_at} />
              </span>
            )}
            {alert.block_id && (
              <span>Block: {alert.block_id.slice(0, 8)}…</span>
            )}
            <span className="font-mono">{alert.rule_key}</span>
          </div>
        </div>

        {alert.is_active && (
          <button
            onClick={handleResolve}
            disabled={resolving}
            className="shrink-0 rounded-lg bg-emerald-600/20 px-3 py-1.5 text-xs font-medium text-emerald-400 transition-colors hover:bg-emerald-600/30 disabled:opacity-50"
          >
            {resolving ? 'Resolving…' : 'Resolve'}
          </button>
        )}
      </div>
    </Card>
  );
}

export function AlertsCenter() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('active');

  const load = useCallback(async () => {
    try {
      const isActive = statusFilter === 'active' ? true : undefined;
      const data = await fetchAlerts({ isActive });
      setAlerts(data);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load alerts');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    setLoading(true);
    load();
    const timer = setInterval(load, 30_000);
    return () => clearInterval(timer);
  }, [load]);

  function handleResolved(id: string) {
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === id ? { ...a, is_active: false, resolved_at: new Date().toISOString() } : a,
      ),
    );
  }

  const filtered = alerts
    .filter((a) => severityFilter === 'all' || a.severity === severityFilter)
    .sort(
      (a, b) =>
        SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] ||
        b.triggered_at.localeCompare(a.triggered_at),
    );

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Alerts Center</h1>
          <p className="text-sm text-slate-400">
            {filtered.length} alert{filtered.length !== 1 ? 's' : ''}
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-2">
          {/* Status filter */}
          <div className="flex rounded-lg border border-slate-700 bg-slate-800 p-0.5">
            {(['active', 'all'] as StatusFilter[]).map((f) => (
              <button
                key={f}
                onClick={() => setStatusFilter(f)}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors capitalize ${
                  statusFilter === f
                    ? 'bg-slate-700 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {f === 'active' ? 'Active Only' : 'All'}
              </button>
            ))}
          </div>

          {/* Severity filter */}
          <div className="flex rounded-lg border border-slate-700 bg-slate-800 p-0.5">
            {(['all', 'critical', 'warning', 'info'] as SeverityFilter[]).map((f) => (
              <button
                key={f}
                onClick={() => setSeverityFilter(f)}
                className={`rounded-md px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
                  severityFilter === f
                    ? 'bg-slate-700 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <p className="text-slate-400">Loading alerts…</p>
        </div>
      )}

      {!loading && error && (
        <Card className="border-red-500/30 bg-red-900/10 p-5">
          <p className="text-red-400">{error}</p>
        </Card>
      )}

      {!loading && !error && filtered.length === 0 && (
        <Card className="p-10 text-center">
          <p className="text-lg font-medium text-emerald-400">No active alerts — system healthy</p>
          <p className="mt-1 text-sm text-slate-500">
            {severityFilter !== 'all' || statusFilter !== 'active'
              ? 'Try adjusting your filters.'
              : 'All sensors are operating normally.'}
          </p>
        </Card>
      )}

      {!loading && !error && filtered.length > 0 && (
        <div className="space-y-3">
          {filtered.map((alert) => (
            <AlertCard key={alert.id} alert={alert} onResolved={handleResolved} />
          ))}
        </div>
      )}
    </div>
  );
}
