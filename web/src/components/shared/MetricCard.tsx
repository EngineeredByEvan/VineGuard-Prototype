import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn, formatPercentage } from '@/utils';
import type { ReactNode } from 'react';

interface MetricCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon?: ReactNode;
  trend?: {
    label: string;
    value: number;
    isPositive?: boolean;
  };
  format?: (value: number | string) => string;
}

const MetricCard = ({ title, value, subtitle, icon, trend, format }: MetricCardProps) => {
  const renderValue = () => {
    if (typeof value === 'number') {
      return format ? format(value) : value.toLocaleString();
    }
    return value;
  };

  return (
    <Card className="relative overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>{title}</CardTitle>
          {subtitle && <CardDescription>{subtitle}</CardDescription>}
        </div>
        {icon && <div className="text-primary/80">{icon}</div>}
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-3xl font-semibold tracking-tight text-foreground">{renderValue()}</p>
        {trend && (
          <div
            className={cn(
              'inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium',
              trend.isPositive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
            )}
          >
            <span>{trend.label}</span>
            <span className="font-semibold">{formatPercentage(Math.abs(trend.value), 1)}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default MetricCard;
