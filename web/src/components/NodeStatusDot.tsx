interface NodeStatusDotProps {
  status: 'active' | 'stale' | 'inactive';
  className?: string;
}

const COLOR = {
  active: 'bg-emerald-400',
  stale: 'bg-amber-400',
  inactive: 'bg-slate-500',
};

export function NodeStatusDot({ status, className = '' }: NodeStatusDotProps) {
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${COLOR[status] ?? COLOR.inactive} ${className}`}
      title={status}
    />
  );
}
