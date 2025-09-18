import { useEffect, useMemo, useState } from 'react';
import { Battery, Droplet, Thermometer, Waves } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Card, CardContent, CardTitle } from './components/ui/card';
import { TelemetryReading, fetchRecentReadings, openTelemetryStream } from './lib/api';

function formatTimestamp(value: string) {
  return new Date(value).toLocaleTimeString();
}

export default function App() {
  const [readings, setReadings] = useState<TelemetryReading[]>([]);

  useEffect(() => {
    fetchRecentReadings().then(setReadings).catch(console.error);
    const source = openTelemetryStream((reading) => {
      setReadings((current) => [reading, ...current].slice(0, 50));
    });
    return () => {
      source?.close();
    };
  }, []);

  const latest = readings[0];

  const moistureSeries = useMemo(() => readings.slice().reverse(), [readings]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      <header className="border-b border-slate-800 bg-slate-950/60 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-sm uppercase tracking-widest text-emerald-400">VineGuard™</p>
            <h1 className="text-2xl font-bold text-white">Smart Vineyard Telemetry</h1>
          </div>
          <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-semibold text-emerald-300">
            {latest ? 'Live' : 'Connecting'}
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-6 py-8">
        <section className="grid gap-4 md:grid-cols-4">
          <MetricCard
            title="Soil Moisture"
            value={latest ? `${latest.soil_moisture.toFixed(1)}%` : '—'}
            icon={<Droplet className="h-5 w-5" />}
          />
          <MetricCard
            title="Soil Temperature"
            value={latest ? `${latest.soil_temp_c.toFixed(1)}°C` : '—'}
            icon={<Thermometer className="h-5 w-5" />}
          />
          <MetricCard
            title="Ambient Humidity"
            value={latest ? `${latest.ambient_humidity.toFixed(1)}%` : '—'}
            icon={<Waves className="h-5 w-5" />}
          />
          <MetricCard
            title="Battery"
            value={latest ? `${latest.battery_voltage.toFixed(2)}V` : '—'}
            icon={<Battery className="h-5 w-5" />}
          />
        </section>

        <section className="grid gap-6 md:grid-cols-3">
          <Card className="md:col-span-2">
            <CardTitle>6h Soil Moisture Trend</CardTitle>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={moistureSeries}>
                  <defs>
                    <linearGradient id="moisture" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="recorded_at" tickFormatter={formatTimestamp} stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#020617', border: '1px solid #1e293b' }}
                    labelFormatter={(value) => new Date(value).toLocaleString()}
                  />
                  <Area type="monotone" dataKey="soil_moisture" stroke="#22d3ee" fill="url(#moisture)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card>
            <CardTitle>Latest Sample</CardTitle>
            <div className="mt-4 space-y-3 text-sm text-slate-300">
              <DetailRow label="Device" value={latest?.device_id ?? '—'} />
              <DetailRow label="Ambient Temp" value={latest ? `${latest.ambient_temp_c.toFixed(1)}°C` : '—'} />
              <DetailRow label="Light" value={latest ? `${latest.light_lux.toFixed(0)} lux` : '—'} />
              <DetailRow label="Recorded" value={latest ? new Date(latest.recorded_at).toLocaleString() : '—'} />
            </div>
          </Card>
        </section>
      </main>
    </div>
  );
}

interface MetricCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
}

function MetricCard({ title, value, icon }: MetricCardProps) {
  return (
    <Card>
      <div className="flex items-center justify-between">
        <CardTitle className="text-xs text-slate-400">{title}</CardTitle>
        <span className="text-emerald-300">{icon}</span>
      </div>
      <CardContent>{value}</CardContent>
    </Card>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-100">{value}</span>
    </div>
  );
}
