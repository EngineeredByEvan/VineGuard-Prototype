export function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 60_000) return 'just now';
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return `${Math.floor(diff / 86_400_000)}d ago`;
}

interface RelativeTimeProps {
  iso: string | null;
  fallback?: string;
  className?: string;
}

export function RelativeTime({ iso, fallback = '—', className = '' }: RelativeTimeProps) {
  if (!iso) return <span className={className}>{fallback}</span>;
  return (
    <span className={className} title={new Date(iso).toLocaleString()}>
      {relativeTime(iso)}
    </span>
  );
}
