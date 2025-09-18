import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiClient } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import type { Site } from '@/types';
import NodeStatusPill from '@/components/shared/NodeStatusPill';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { MapPin } from 'lucide-react';

const SiteDetailPage = () => {
  const { siteId } = useParams();
  const { user } = useAuth();
  const [site, setSite] = useState<Site | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!siteId) return;

    const load = async () => {
      try {
        const data = await apiClient.fetchSite(siteId);
        if (!cancelled) setSite(data);
      } catch (error) {
        console.error('Failed to load site detail', error);
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [siteId, user?.orgId]);

  if (!site) {
    return (
      <div className="rounded-2xl border border-border/40 bg-slate-900/40 p-8 text-sm text-muted-foreground">
        Loading site details…
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
      <Card className="overflow-hidden border-border/40 bg-slate-900/60">
        <CardHeader className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-2xl font-semibold text-foreground">{site.name}</CardTitle>
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/40 bg-primary/5 px-3 py-1 text-xs text-primary">
              <MapPin className="h-3.5 w-3.5" /> {site.coordinates.lat.toFixed(3)}, {site.coordinates.lng.toFixed(3)}
            </div>
          </div>
          <p className="max-w-3xl text-sm text-muted-foreground">{site.description}</p>
        </CardHeader>
        <CardContent>
          <div className="relative h-80 w-full overflow-hidden rounded-2xl border border-border/40 bg-gradient-to-br from-slate-800 via-slate-900 to-slate-950">
            <div className="absolute inset-0 opacity-40" style={{
              backgroundImage:
                'radial-gradient(circle at 20% 20%, rgba(79, 70, 229, 0.3), transparent 55%), radial-gradient(circle at 80% 30%, rgba(16, 185, 129, 0.35), transparent 50%), radial-gradient(circle at 60% 75%, rgba(59, 130, 246, 0.3), transparent 45%)'
            }} />
            <div className="absolute inset-0 flex flex-col justify-between p-6 text-xs text-slate-300">
              <div className="flex items-center justify-between">
                <span>Vineyard heatmap</span>
                <span>Signal overlay</span>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                {site.nodes.map((node) => (
                  <div key={node.id} className="rounded-xl border border-border/40 bg-slate-900/60 p-4">
                    <p className="text-sm font-semibold text-foreground">{node.name}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Signal {node.signalStrength}% · Soil moisture {node.soilMoisture}%
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">Battery {node.battery}%</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-6">
        <Card className="border-border/40 bg-slate-900/60">
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-foreground">Node roster</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {site.nodes.map((node) => (
              <div key={node.id} className="rounded-xl border border-border/40 bg-slate-900/50 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-foreground">{node.name}</p>
                    <p className="text-xs text-muted-foreground">Last seen {new Date(node.lastSeen).toLocaleTimeString()}</p>
                  </div>
                  <Button asChild variant="ghost" className="text-xs text-primary">
                    <Link to={`/nodes/${node.id}`}>View node</Link>
                  </Button>
                </div>
                <div className="mt-3">
                  <NodeStatusPill node={node} />
                </div>
              </div>
            ))}
            {site.nodes.length === 0 && (
              <p className="text-sm text-muted-foreground">No telemetry nodes assigned to this site.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default SiteDetailPage;
