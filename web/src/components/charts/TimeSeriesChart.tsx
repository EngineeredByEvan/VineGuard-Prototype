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
  YAxis
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { NodeTelemetryPoint } from '@/types';
import { formatDateTime } from '@/utils';

interface SeriesDefinition {
  dataKey: keyof NodeTelemetryPoint;
  name: string;
  color: string;
  unit?: string;
  type?: 'monotone' | 'linear';
}

interface TimeSeriesChartProps {
  title: string;
  data: NodeTelemetryPoint[];
  series: SeriesDefinition[];
  height?: number;
  variant?: 'line' | 'area';
}

const TimeSeriesChart = ({ title, data, series, height = 280, variant = 'area' }: TimeSeriesChartProps) => {
  const ChartComponent = variant === 'line' ? LineChart : AreaChart;

  return (
    <Card className="border-border/40 bg-slate-900/50">
      <CardHeader>
        <CardTitle className="text-base font-semibold text-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent className="h-full w-full">
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height={height}>
            <ChartComponent data={data} margin={{ left: 0, right: 12, top: 16, bottom: 0 }}>
              <defs>
                {series.map((serie) => (
                  <linearGradient id={`${String(serie.dataKey)}Gradient`} key={serie.dataKey} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={serie.color} stopOpacity={0.4} />
                    <stop offset="100%" stopColor={serie.color} stopOpacity={0.05} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
              <XAxis
                dataKey="timestamp"
                stroke="rgba(148,163,184,0.6)"
                tickFormatter={(value) => formatDateTime(value)}
                minTickGap={24}
              />
              <YAxis stroke="rgba(148,163,184,0.6)" />
              <Tooltip
                contentStyle={{
                  background: 'rgba(15, 23, 42, 0.95)',
                  borderRadius: 12,
                  border: '1px solid rgba(148, 163, 184, 0.2)'
                }}
                labelFormatter={(value) => formatDateTime(value)}
              />
              <Legend wrapperStyle={{ color: 'rgba(226, 232, 240, 0.6)' }} />
              {series.map((serie) =>
                variant === 'line' ? (
                  <Line
                    type={serie.type ?? 'monotone'}
                    key={serie.dataKey}
                    dataKey={serie.dataKey}
                    name={serie.name}
                    stroke={serie.color}
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                ) : (
                  <Area
                    type={serie.type ?? 'monotone'}
                    key={serie.dataKey}
                    dataKey={serie.dataKey}
                    name={serie.name}
                    stroke={serie.color}
                    fill={`url(#${String(serie.dataKey)}Gradient)`}
                    strokeWidth={2}
                    isAnimationActive={false}
                  />
                )
              )}
            </ChartComponent>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

export default TimeSeriesChart;
