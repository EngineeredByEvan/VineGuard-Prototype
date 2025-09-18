import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiClient } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import { useLiveTelemetry } from '@/hooks/useLiveTelemetry';
import type { Insight, NodeDetail, NodeTelemetryPoint } from '@/types';
import TimeSeriesChart from '@/components/charts/TimeSeriesChart';
import NodeStatusPill from '@/components/shared/NodeStatusPill';
import InsightBadge from '@/components/shared/InsightBadge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { formatDateTime } from '@/utils';

const ranges = [
  { label: '6h', value: '6h' },
  { label: '24h', value: '24h' },
  { label: '7d', value: '7d' }
];

const NodeDetailPage = () => {
  const { nodeId } = useParams();
  const { user } = useAuth();
  const [node, setNode] = useState<NodeDetail | null>(null);
  const [telemetry, setTelemetry] = useState<NodeTelemetryPoint[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [range, setRange] = useState('24h');
  const [publishInterval, setPublishInterval] = useState(900);
  const [otaUrl, setOtaUrl] = useState('');
  const [commandStatus, setCommandStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('idle');

  useEffect(() => {
    let cancelled = false;
    if (!nodeId) return;

    const load = async () => {
      try {
        const [nodeData, telemetryData, insightData] = await Promise.all([
          apiClient.fetchNode(nodeId),
          apiClient.fetchNodeTelemetry(nodeId, range),
          user?.orgId ? apiClient.fetchInsights(user.orgId, { nodeId }) : Promise.resolve([])
        ]);
        if (cancelled) return;
        setNode(nodeData);
        setPublishInterval(nodeData.publishIntervalSec);
        setTelemetry(telemetryData);
        setInsights(insightData);
      } catch (error) {
        console.error('Failed to load node data', error);
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [nodeId, range, user?.orgId]);

  const handleLive = useCallback(
    (payload: NodeTelemetryPoint) => {
      if (!nodeId) return;
      if (payload.nodeId && payload.nodeId !== nodeId) return;
      setTelemetry((prev) => {
        const next = [...prev.slice(-200), { ...payload, nodeId }];
        return next;
      });
      setNode((prev) =>
        prev
          ? {
              ...prev,
              soilMoisture: payload.soilMoisture,
              battery: payload.battery,
              lastSeen: payload.timestamp,
              status: 'online'
            }
          : prev
      );
    },
    [nodeId]
  );

  useLiveTelemetry(user?.orgId, handleLive);

  const handleCommand = async (event: FormEvent) => {
    event.preventDefault();
    if (!nodeId) return;
    setCommandStatus('sending');
    try {
      await apiClient.sendCommand({ nodeId, publishIntervalSec: publishInterval, otaUrl: otaUrl || undefined });
      setCommandStatus('success');
      setTimeout(() => setCommandStatus('idle'), 2500);
    } catch (error) {
      console.error('Failed to send command', error);
      setCommandStatus('error');
    }
  };

  const latestTelemetry = useMemo(() => telemetry[telemetry.length - 1], [telemetry]);

  if (!node) {
    return (
      <div className="rounded-2xl border border-border/40 bg-slate-900/40 p-8 text-sm text-muted-foreground">
        Loading node diagnostics…
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">{node.name}</h1>
          <p className="text-sm text-muted-foreground">
            Firmware {node.firmwareVersion} · Reporting every {node.publishIntervalSec / 60} minutes
          </p>
        </div>
        <NodeStatusPill node={node} />
      </div>

      <div className="flex flex-wrap gap-3">
        {ranges.map((option) => (
          <Button
            key={option.value}
            variant={option.value === range ? 'default' : 'ghost'}
            onClick={() => setRange(option.value)}
          >
            Last {option.label}
          </Button>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <TimeSeriesChart
          title="Soil moisture & soil temperature"
          data={telemetry}
          series={[
            { dataKey: 'soilMoisture', name: 'Soil moisture (%)', color: '#34d399' },
            { dataKey: 'soilTemp', name: 'Soil temp (°C)', color: '#f97316' }
          ]}
        />
        <TimeSeriesChart
          title="Air temperature & humidity"
          data={telemetry}
          series={[
            { dataKey: 'airTemp', name: 'Air temp (°C)', color: '#60a5fa' },
            { dataKey: 'humidity', name: 'Humidity (%)', color: '#a855f7' }
          ]}
        />
        <TimeSeriesChart
          title="Light intensity"
          data={telemetry}
          variant="line"
          series={[{ dataKey: 'light', name: 'Light (lux)', color: '#facc15' }]}
        />
        <TimeSeriesChart
          title="Battery voltage"
          data={telemetry}
          variant="line"
          series={[{ dataKey: 'battery', name: 'Battery (%)', color: '#f472b6' }]}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <Card className="border-border/40 bg-slate-900/60">
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-foreground">Recent insights</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {insights.length === 0 && (
              <p className="text-sm text-muted-foreground">No alerts for this node in the selected timeframe.</p>
            )}
            {insights.map((insight) => (
              <div key={insight.id} className="rounded-xl border border-border/40 bg-slate-950/60 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-foreground">{insight.message}</p>
                    <p className="text-xs text-muted-foreground">{formatDateTime(insight.timestamp)}</p>
                  </div>
                  <InsightBadge type={insight.type} severity={insight.severity} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-border/40 bg-slate-900/60">
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-foreground">Command & control</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleCommand}>
              <div className="space-y-2">
                <Label htmlFor="publishInterval">Publish interval (seconds)</Label>
                <Input
                  id="publishInterval"
                  type="number"
                  min={60}
                  value={publishInterval}
                  onChange={(event) => setPublishInterval(Number(event.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="otaUrl">OTA firmware URL</Label>
                <Input
                  id="otaUrl"
                  type="url"
                  placeholder="https://updates.vineguard.io/firmware.bin"
                  value={otaUrl}
                  onChange={(event) => setOtaUrl(event.target.value)}
                />
              </div>
              <Button type="submit" className="w-full" disabled={commandStatus === 'sending'}>
                {commandStatus === 'sending' ? 'Dispatching…' : 'Send command'}
              </Button>
              {commandStatus === 'success' && (
                <p className="text-sm text-emerald-400">Command queued successfully.</p>
              )}
              {commandStatus === 'error' && (
                <p className="text-sm text-rose-400">Failed to queue command. Try again.</p>
              )}
            </form>
            {latestTelemetry && (
              <div className="mt-6 rounded-xl border border-border/40 bg-slate-950/60 p-4 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground">Latest reading</p>
                <ul className="mt-2 space-y-1">
                  <li>Soil moisture {latestTelemetry.soilMoisture.toFixed(1)}%</li>
                  <li>Air temperature {latestTelemetry.airTemp.toFixed(1)}°C</li>
                  <li>Humidity {latestTelemetry.humidity.toFixed(1)}%</li>
                  <li>Battery {latestTelemetry.battery.toFixed(1)}%</li>
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default NodeDetailPage;
