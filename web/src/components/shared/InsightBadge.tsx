import { Badge } from '@/components/ui/badge';
import type { Insight, InsightType } from '@/types';

const typeToVariant: Record<InsightType, 'default' | 'secondary' | 'destructive'> = {
  irrigation: 'default',
  disease: 'destructive',
  battery: 'secondary'
};

const severityTone: Record<Insight['severity'], string> = {
  low: 'bg-emerald-500/20 text-emerald-300',
  medium: 'bg-amber-500/20 text-amber-300',
  high: 'bg-rose-500/20 text-rose-300'
};

interface InsightBadgeProps {
  type: InsightType;
  severity: Insight['severity'];
  className?: string;
}

const InsightBadge = ({ type, severity, className }: InsightBadgeProps) => {
  return (
    <Badge
      variant={typeToVariant[type]}
      className={`${severityTone[severity]} border-transparent capitalize ${className ?? ''}`.trim()}
    >
      {type} · {severity}
    </Badge>
  );
};

export default InsightBadge;
