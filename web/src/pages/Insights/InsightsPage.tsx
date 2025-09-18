import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import InsightBadge from '@/components/shared/InsightBadge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/hooks/useAuth';
import { apiClient } from '@/services/api';
import type { Insight, InsightType } from '@/types';
import { formatDateTime } from '@/utils';
import { Button } from '@/components/ui/button';

const timeRanges = [
  { label: '24 hours', value: '24h', delta: 24 * 60 * 60 * 1000 },
  { label: '7 days', value: '7d', delta: 7 * 24 * 60 * 60 * 1000 },
  { label: '30 days', value: '30d', delta: 30 * 24 * 60 * 60 * 1000 }
];

const types: Array<{ label: string; value: InsightType | 'all' }> = [
  { label: 'All types', value: 'all' },
  { label: 'Irrigation', value: 'irrigation' },
  { label: 'Disease', value: 'disease' },
  { label: 'Battery', value: 'battery' }
];

const InsightsPage = () => {
  const { user } = useAuth();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState<InsightType | 'all'>('all');
  const [range, setRange] = useState(timeRanges[1]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    if (!user?.orgId) return;

    const load = async () => {
      setLoading(true);
      try {
        const to = new Date();
        const from = new Date(to.getTime() - range.delta);
        const data = await apiClient.fetchInsights(user.orgId, {
          type: selectedType === 'all' ? undefined : selectedType,
          from: from.toISOString(),
          to: to.toISOString()
        });
        if (!cancelled) setInsights(data);
      } catch (error) {
        console.error('Failed to load insights', error);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [user?.orgId, selectedType, range]);

  const filtered = useMemo(() => {
    if (!search) return insights;
    const term = search.toLowerCase();
    return insights.filter((insight) => insight.message.toLowerCase().includes(term));
  }, [insights, search]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Irrigation & disease insights</h1>
          <p className="text-sm text-muted-foreground">
            Review actionable telemetry-driven recommendations and plan maintenance.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {types.map((type) => (
            <Button
              key={type.value}
              variant={selectedType === type.value ? 'default' : 'ghost'}
              onClick={() => setSelectedType(type.value)}
            >
              {type.label}
            </Button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-[1fr_auto]">
        <Input
          placeholder="Search insight text…"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="border-border/60 bg-slate-900/50"
        />
        <select
          className="h-10 rounded-md border border-border/60 bg-slate-900/60 px-3 text-sm text-foreground"
          value={range.value}
          onChange={(event) => {
            const next = timeRanges.find((option) => option.value === event.target.value);
            if (next) setRange(next);
          }}
        >
          {timeRanges.map((option) => (
            <option key={option.value} value={option.value}>
              Last {option.label}
            </option>
          ))}
        </select>
      </div>

      <Card className="border-border/40 bg-slate-900/60">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-foreground">{filtered.length} insights</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading && <p className="text-sm text-muted-foreground">Loading insights…</p>}
          {!loading && filtered.length === 0 && (
            <p className="text-sm text-muted-foreground">No insights match the selected filters.</p>
          )}
          {filtered.map((insight) => (
            <div key={insight.id} className="rounded-xl border border-border/40 bg-slate-950/60 p-5 shadow-inner shadow-black/20">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-foreground">{insight.message}</p>
                  <p className="text-xs text-muted-foreground">{formatDateTime(insight.timestamp)}</p>
                </div>
                <InsightBadge type={insight.type} severity={insight.severity} />
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                <span>Node {insight.nodeId}</span>
                <span>Site {insight.siteId}</span>
                <Link to={`/nodes/${insight.nodeId}`} className="text-primary hover:text-primary/80">
                  View node
                </Link>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
};

export default InsightsPage;
