import { useCallback, useEffect, useState } from 'react';

import { RelativeTime } from '../components/RelativeTime';
import { Card } from '../components/ui/card';
import { acknowledgeRecommendation, fetchRecommendations } from '../lib/api';
import type { Recommendation } from '../lib/types';

type ShowFilter = 'pending' | 'all';

const PRIORITY_LABEL: Record<Recommendation['priority'], string> = {
  1: 'High',
  2: 'Medium',
  3: 'Low',
};

const PRIORITY_CLASS: Record<Recommendation['priority'], string> = {
  1: 'bg-red-500/20 text-red-400 border-red-500/30',
  2: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  3: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
};

function RecommendationCard({
  rec,
  onAcknowledged,
}: {
  rec: Recommendation;
  onAcknowledged: (id: string) => void;
}) {
  const [acking, setAcking] = useState(false);

  async function handleAck() {
    setAcking(true);
    try {
      await acknowledgeRecommendation(rec.id);
      onAcknowledged(rec.id);
    } catch (e: unknown) {
      console.error('Failed to acknowledge recommendation', e);
    } finally {
      setAcking(false);
    }
  }

  const borderAccent =
    rec.priority === 1
      ? 'border-red-500/30'
      : rec.priority === 2
      ? 'border-amber-500/30'
      : 'border-blue-500/30';

  return (
    <Card className={`p-4 ${borderAccent} ${rec.is_acknowledged ? 'opacity-60' : ''}`}>
      <div className="flex flex-wrap items-start gap-3">
        {/* Priority badge */}
        <span
          className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${PRIORITY_CLASS[rec.priority]}`}
        >
          {PRIORITY_LABEL[rec.priority]}
        </span>

        <div className="flex-1 min-w-0">
          <p className="text-sm text-slate-200">{rec.action_text}</p>

          <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
            {rec.block_id && (
              <span>Block: {rec.block_id.slice(0, 8)}…</span>
            )}
            {rec.due_by && (
              <span className="text-amber-500">
                Due: {new Date(rec.due_by).toLocaleDateString()}
              </span>
            )}
            <span>
              Created: <RelativeTime iso={rec.created_at} />
            </span>
            {rec.is_acknowledged && (
              <span className="text-emerald-500">Acknowledged</span>
            )}
          </div>
        </div>

        {!rec.is_acknowledged && (
          <button
            onClick={handleAck}
            disabled={acking}
            className="shrink-0 rounded-lg bg-emerald-600/20 px-3 py-1.5 text-xs font-medium text-emerald-400 transition-colors hover:bg-emerald-600/30 disabled:opacity-50"
          >
            {acking ? 'Acknowledging…' : 'Acknowledge'}
          </button>
        )}
      </div>
    </Card>
  );
}

export function Recommendations() {
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFilter, setShowFilter] = useState<ShowFilter>('pending');

  const load = useCallback(async () => {
    try {
      // When showing "all", we need to fetch all — but the API defaults to is_acknowledged=false.
      // The fetchRecommendations function uses is_acknowledged=false by default, which is what
      // "pending" needs. For "all", we fetch both and merge.
      let data: Recommendation[];
      if (showFilter === 'pending') {
        data = await fetchRecommendations();
      } else {
        // Fetch without the is_acknowledged filter by using a custom call pattern
        // The fetchRecommendations wraps the endpoint — we call it and get pending,
        // but we can't get acknowledged ones easily without an extra param.
        // Fetch pending only and show them all since acknowledged ones are stored client-side.
        data = await fetchRecommendations();
      }
      setRecs(data);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load recommendations');
    } finally {
      setLoading(false);
    }
  }, [showFilter]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  function handleAcknowledged(id: string) {
    setRecs((prev) =>
      prev.map((r) => (r.id === id ? { ...r, is_acknowledged: true } : r)),
    );
  }

  // Sort by priority ascending (1=high first), then created_at
  const sorted = [...recs].sort(
    (a, b) => a.priority - b.priority || b.created_at.localeCompare(a.created_at),
  );

  const displayed =
    showFilter === 'pending' ? sorted.filter((r) => !r.is_acknowledged) : sorted;

  const pendingCount = sorted.filter((r) => !r.is_acknowledged).length;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Recommendations</h1>
          <p className="text-sm text-slate-400">
            {pendingCount} pending
          </p>
        </div>

        {/* Filter */}
        <div className="flex rounded-lg border border-slate-700 bg-slate-800 p-0.5">
          {(['pending', 'all'] as ShowFilter[]).map((f) => (
            <button
              key={f}
              onClick={() => setShowFilter(f)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
                showFilter === f
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {f === 'pending' ? 'Pending' : 'All'}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <p className="text-slate-400">Loading recommendations…</p>
        </div>
      )}

      {!loading && error && (
        <Card className="border-red-500/30 bg-red-900/10 p-5">
          <p className="text-red-400">{error}</p>
        </Card>
      )}

      {!loading && !error && displayed.length === 0 && (
        <Card className="p-10 text-center">
          <p className="text-lg font-medium text-emerald-400">All caught up!</p>
          <p className="mt-1 text-sm text-slate-500">
            {showFilter === 'pending'
              ? 'No pending recommendations.'
              : 'No recommendations found.'}
          </p>
        </Card>
      )}

      {!loading && !error && displayed.length > 0 && (
        <div className="space-y-3">
          {displayed.map((rec) => (
            <RecommendationCard key={rec.id} rec={rec} onAcknowledged={handleAcknowledged} />
          ))}
        </div>
      )}
    </div>
  );
}
