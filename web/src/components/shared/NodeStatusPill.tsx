import { cn, formatTimeAgo } from '@/utils';
import type { NodeSummary } from '@/types';

interface NodeStatusPillProps {
  node: Pick<NodeSummary, 'status' | 'lastSeen' | 'signalStrength' | 'battery'>;
}

const NodeStatusPill = ({ node }: NodeStatusPillProps) => {
  const isOnline = node.status === 'online';

  return (
    <div
      className={cn(
        'inline-flex items-center gap-3 rounded-full border border-border/40 bg-slate-900/70 px-4 py-2 text-xs font-medium shadow-inner',
        isOnline ? 'text-emerald-300' : 'text-rose-300'
      )}
    >
      <span
        className={cn('h-2.5 w-2.5 rounded-full', isOnline ? 'bg-emerald-400 shadow-emerald-400/60' : 'bg-rose-400 shadow-rose-400/60')}
      />
      <span>{isOnline ? 'Online' : 'Offline'}</span>
      <span className="text-muted-foreground">·</span>
      <span>Signal {node.signalStrength}%</span>
      <span className="text-muted-foreground">·</span>
      <span>Battery {node.battery}%</span>
      <span className="text-muted-foreground">·</span>
      <span>Last seen {formatTimeAgo(node.lastSeen)}</span>
    </div>
  );
};

export default NodeStatusPill;
