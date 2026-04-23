import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { RelativeTime } from '../components/RelativeTime';
import { Card } from '../components/ui/card';
import { fetchBlocks, fetchVineyards } from '../lib/api';
import type { Block, Vineyard } from '../lib/types';

function BlockCard({ block, vineyardName }: { block: Block; vineyardName?: string }) {
  const navigate = useNavigate();

  return (
    <Card
      className="cursor-pointer p-5 transition-colors hover:border-slate-600 hover:bg-slate-900"
      onClick={() => navigate(`/blocks/${block.id}`)}
    >
      <div className="mb-2 flex items-start justify-between">
        <div>
          <p className="text-base font-semibold text-white">{block.name}</p>
          <p className="text-sm text-slate-400">{block.variety}</p>
        </div>
        {vineyardName && (
          <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
            {vineyardName}
          </span>
        )}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        {block.area_ha !== null && (
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">Area</span>
            <p className="font-medium text-slate-200">{block.area_ha.toFixed(2)} ha</p>
          </div>
        )}
        <div>
          <span className="text-xs uppercase tracking-wide text-slate-500">Created</span>
          <p className="font-medium text-slate-200">
            <RelativeTime iso={block.created_at} />
          </p>
        </div>
      </div>

      {block.notes && (
        <p className="mt-3 text-xs text-slate-500 line-clamp-2">{block.notes}</p>
      )}

      <div className="mt-3 text-xs text-emerald-400">View block details →</div>
    </Card>
  );
}

export function BlocksPage() {
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [vineyards, setVineyards] = useState<Vineyard[]>([]);
  const [selectedVineyard, setSelectedVineyard] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadVineyards = useCallback(async () => {
    try {
      const v = await fetchVineyards();
      setVineyards(v);
    } catch {
      // vineyards are optional context, don't fail hard
    }
  }, []);

  const loadBlocks = useCallback(async (vineyardId?: string) => {
    setLoading(true);
    try {
      const data = await fetchBlocks(vineyardId || undefined);
      setBlocks(data);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load blocks');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadVineyards();
  }, [loadVineyards]);

  useEffect(() => {
    loadBlocks(selectedVineyard || undefined);
  }, [loadBlocks, selectedVineyard]);

  const vineyardMap = Object.fromEntries(vineyards.map((v) => [v.id, v.name]));

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Blocks</h1>
          <p className="text-sm text-slate-400">
            {blocks.length} block{blocks.length !== 1 ? 's' : ''}
          </p>
        </div>

        {vineyards.length > 1 && (
          <select
            value={selectedVineyard}
            onChange={(e) => setSelectedVineyard(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="">All Vineyards</option>
            {vineyards.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <p className="text-slate-400">Loading blocks…</p>
        </div>
      )}

      {!loading && error && (
        <Card className="border-red-500/30 bg-red-900/10 p-5">
          <p className="text-red-400">{error}</p>
        </Card>
      )}

      {!loading && !error && blocks.length === 0 && (
        <Card className="p-10 text-center">
          <p className="text-slate-400">No blocks found.</p>
        </Card>
      )}

      {!loading && !error && blocks.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {blocks.map((block) => (
            <BlockCard
              key={block.id}
              block={block}
              vineyardName={vineyards.length > 1 ? vineyardMap[block.vineyard_id] : undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
}
