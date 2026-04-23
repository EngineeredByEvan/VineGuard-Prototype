interface MoistureBarProps {
  value: number | null;
}

function color(value: number) {
  if (value >= 25) return 'bg-emerald-400';
  if (value >= 15) return 'bg-amber-400';
  return 'bg-red-400';
}

export function MoistureBar({ value }: MoistureBarProps) {
  if (value === null) {
    return <div className="h-2 rounded-full bg-slate-700" />;
  }
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div className="h-2 w-full rounded-full bg-slate-700">
      <div
        className={`h-2 rounded-full transition-all ${color(value)}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
