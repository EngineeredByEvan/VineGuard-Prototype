interface SeverityBadgeProps {
  severity: 'info' | 'warning' | 'critical';
}

const MAP = {
  critical: { label: 'Critical', classes: 'bg-red-500/20 text-red-400 border-red-500/30' },
  warning: { label: 'Warning', classes: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
  info: { label: 'Info', classes: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
};

export function SeverityBadge({ severity }: SeverityBadgeProps) {
  const { label, classes } = MAP[severity] ?? MAP.info;
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${classes}`}
    >
      {label}
    </span>
  );
}
