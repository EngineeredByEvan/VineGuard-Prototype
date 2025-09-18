import { useEffect, useMemo, useState } from 'react';
import MetricCard from '@/components/shared/MetricCard';
import TimeSeriesChart from '@/components/charts/TimeSeriesChart';
import NodeStatusPill from '@/components/shared/NodeStatusPill';
import { apiClient } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import type { NodeTelemetryPoint, OrgOverview, Site } from '@/types';
import { formatPercentage } from '@/utils';
import { Droplets, Leaf, RadioTower, ShieldAlert } from 'lucide-react';

const OverviewPage = () => {
  const { user } = useAuth();
  const [overview, setOverview] = useState<OrgOverview | null>(null);
  const [sites, setSites] = useState<Site[]>([]);
  const [chartData, setChartData] = useState<NodeTelemetryPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    if (!user?.orgId) return;

    const load = async () => {
      setLoading(true);
      try {
        const [overviewData, sitesData] = await Promise.all([
          apiClient.fetchOrgOverview(user.orgId),
          apiClient.fetchSites(user.orgId)
        ]);
        if (cancelled) return;
        setOverview(overviewData);
        setSites(sitesData);

        const primarySite = sitesData[0];
        if (primarySite && primarySite.nodes.length > 0) {
          const telemetrySeries = await Promise.all(
            primarySite.nodes.map((node) => apiClient.fetchNodeTelemetry(node.id, '6h'))
          );
          if (cancelled) return;
          if (!telemetrySeries.length || telemetrySeries[0].length === 0) {
            setChartData([]);
            return;
          }
          const aggregated = telemetrySeries[0].map((point, index) => {
            const timestamp = point.timestamp;
            const soilMoisture = telemetrySeries.reduce(
              (sum, series) => sum + (series[index]?.soilMoisture ?? series[series.length - 1]?.soilMoisture ?? 0),
              0
            );
            const airTemp = telemetrySeries.reduce(
              (sum, series) => sum + (series[index]?.airTemp ?? series[series.length - 1]?.airTemp ?? 0),
              0
            );
            const humidity = telemetrySeries.reduce(
              (sum, series) => sum + (series[index]?.humidity ?? series[series.length - 1]?.humidity ?? 0),
              0
            );
            const battery = telemetrySeries.reduce(
              (sum, series) => sum + (series[index]?.battery ?? series[series.length - 1]?.battery ?? 0),
              0
            );
            const count = telemetrySeries.length || 1;

            return {
              ...point,
              timestamp,
              soilMoisture: soilMoisture / count,
              airTemp: airTemp / count,
              humidity: humidity / count,
              battery: battery / count
            };
          });
          setChartData(aggregated);
        }
      } catch (error) {
        console.error('Failed to load overview data', error);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [user?.orgId]);

  const metrics = useMemo(() => {
    if (!overview) return [];
    return [
      {
        title: 'Total nodes',
        value: overview.totalNodes,
        subtitle: 'Across all vineyard blocks',
        icon: <RadioTower className="h-5 w-5" />,
        trend: { label: 'Active deployment', value: overview.onlineNodes / Math.max(overview.totalNodes, 1), isPositive: true }
      },
      {
        title: 'Online nodes',
        value: overview.onlineNodes,
        subtitle: 'Reporting in the last hour',
        icon: <Leaf className="h-5 w-5" />,
        trend: {
          label: 'Availability',
          value: overview.onlineNodes / Math.max(overview.totalNodes, 1),
          isPositive: overview.onlineNodes / Math.max(overview.totalNodes, 1) > 0.7
        }
      },
      {
        title: 'Avg soil moisture',
        value: overview.avgSoilMoisture,
        subtitle: 'Weighted average across blocks',
        icon: <Droplets className="h-5 w-5" />,
        format: (value: number | string) => formatPercentage(Number(value), 1)
      },
      {
        title: 'Battery warnings',
        value: overview.batteryWarnings,
        subtitle: 'Nodes below 50% capacity',
        icon: <ShieldAlert className="h-5 w-5" />,
        trend: {
          label: 'Maintenance load',
          value: overview.batteryWarnings / Math.max(overview.totalNodes, 1),
          isPositive: overview.batteryWarnings === 0
        }
      }
    ];
  }, [overview]);

  return (
    <div className="space-y-8">
      <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <MetricCard key={metric.title} {...metric} />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <TimeSeriesChart
            title="Vineyard moisture and climate"
            data={chartData}
            series={[
              { dataKey: 'soilMoisture', name: 'Soil moisture (%)', color: '#34d399' },
              { dataKey: 'airTemp', name: 'Air temp (°C)', color: '#60a5fa' },
              { dataKey: 'humidity', name: 'Humidity (%)', color: '#a855f7' }
            ]}
          />
        </div>
        <div className="space-y-4 rounded-2xl border border-border/40 bg-slate-900/50 p-6">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Live node health</h2>
            <p className="text-sm text-muted-foreground">
              Latest check-ins across your deployment with connectivity and battery.
            </p>
          </div>
          <div className="space-y-4">
            {(sites[0]?.nodes ?? []).map((node) => (
              <div key={node.id} className="space-y-2">
                <p className="text-sm font-semibold text-foreground">{node.name}</p>
                <NodeStatusPill node={node} />
              </div>
            ))}
            {!loading && sites.length === 0 && (
              <p className="text-sm text-muted-foreground">No nodes assigned to this organization yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default OverviewPage;
