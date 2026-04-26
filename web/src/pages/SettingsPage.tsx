import { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, Clock, PlusCircle, Radio, Server, Wifi, WifiOff } from 'lucide-react';

import { createNode, fetchBlocks, fetchNodes, fetchUnregisteredDevices, fetchVineyards } from '../lib/api';
import type { Block, Node, UnregisteredDevice, Vineyard } from '../lib/types';

const STATUS_STYLES: Record<string, string> = {
  active: 'bg-emerald-500/15 text-emerald-400 border-emerald-800/30',
  stale: 'bg-amber-500/15 text-amber-400 border-amber-800/30',
  inactive: 'bg-slate-700/40 text-slate-500 border-slate-700/30',
};

const TIER_LABELS: Record<string, string> = {
  basic: 'Basic',
  precision_plus: 'Precision+',
};

function SectionCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60">
      <div className="border-b border-slate-800 px-5 py-4">
        <h2 className="text-sm font-semibold text-white">{title}</h2>
        {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function NodeRow({ node }: { node: Node }) {
  const lastSeen = node.last_seen_at
    ? new Date(node.last_seen_at).toLocaleString()
    : 'Never';
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/60 py-3 last:border-0">
      <div className="flex items-center gap-3 min-w-0">
        {node.status === 'active' ? (
          <Wifi className="h-4 w-4 flex-shrink-0 text-emerald-400" />
        ) : (
          <WifiOff className="h-4 w-4 flex-shrink-0 text-slate-600" />
        )}
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-200">{node.name}</p>
          <p className="text-xs text-slate-500">
            <code className="font-mono">{node.device_id}</code>
            {' · '}
            {TIER_LABELS[node.tier] ?? node.tier}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs text-slate-500">{lastSeen}</span>
        <span
          className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
            STATUS_STYLES[node.status] ?? STATUS_STYLES.inactive
          }`}
        >
          {node.status}
        </span>
        {node.battery_voltage != null && (
          <span
            className={`text-xs ${
              node.battery_voltage < 3.4
                ? 'text-red-400'
                : node.battery_voltage < 3.6
                ? 'text-amber-400'
                : 'text-emerald-400'
            }`}
          >
            {node.battery_voltage.toFixed(2)}V
          </span>
        )}
      </div>
    </div>
  );
}

function RegisterNodeForm({
  blocks,
  onRegistered,
}: {
  blocks: Block[];
  onRegistered: () => void;
}) {
  const [deviceId, setDeviceId] = useState('');
  const [name, setName] = useState('');
  const [tier, setTier] = useState<'basic' | 'precision_plus'>('basic');
  const [blockId, setBlockId] = useState(blocks[0]?.id ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!deviceId.trim() || !name.trim() || !blockId) return;
    setSubmitting(true);
    setError(null);
    try {
      await createNode({ device_id: deviceId.trim(), name: name.trim(), tier, block_id: blockId });
      setDeviceId('');
      setName('');
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
      onRegistered();
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Registration failed';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass =
    'w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-emerald-500 focus:outline-none';

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1.5 block text-xs text-slate-400">Device ID</label>
          <input
            className={inputClass}
            placeholder="e.g. vg-node-004"
            value={deviceId}
            onChange={(e) => setDeviceId(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="mb-1.5 block text-xs text-slate-400">Display Name</label>
          <input
            className={inputClass}
            placeholder="e.g. Block C — East Row"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="mb-1.5 block text-xs text-slate-400">Block</label>
          <select
            className={inputClass}
            value={blockId}
            onChange={(e) => setBlockId(e.target.value)}
            required
          >
            {blocks.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name} ({b.variety})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-xs text-slate-400">Tier</label>
          <select
            className={inputClass}
            value={tier}
            onChange={(e) => setTier(e.target.value as 'basic' | 'precision_plus')}
          >
            <option value="basic">Basic</option>
            <option value="precision_plus">Precision+</option>
          </select>
        </div>
      </div>

      {error && (
        <p className="rounded-lg border border-red-800/30 bg-red-950/20 px-3 py-2 text-xs text-red-400">
          {error}
        </p>
      )}
      {success && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-800/30 bg-emerald-950/20 px-3 py-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          <p className="text-xs text-emerald-400">Node registered successfully.</p>
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <PlusCircle className="h-4 w-4" />
        {submitting ? 'Registering…' : 'Register Node'}
      </button>
    </form>
  );
}

export function SettingsPage() {
  const [vineyard, setVineyard] = useState<Vineyard | null>(null);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [unregistered, setUnregistered] = useState<UnregisteredDevice[]>([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    try {
      const vs = await fetchVineyards();
      if (vs.length === 0) return;
      setVineyard(vs[0]);
      const [ns, bs, ur] = await Promise.all([
        fetchNodes(),
        fetchBlocks(vs[0].id),
        fetchUnregisteredDevices(),
      ]);
      setNodes(ns);
      setBlocks(bs);
      setUnregistered(ur);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
      </div>
    );
  }

  const activeNodes = nodes.filter((n) => n.status === 'active');
  const staleNodes = nodes.filter((n) => n.status !== 'active');

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-lg font-semibold text-white">Settings</h1>
        <p className="text-xs text-slate-500">Vineyard configuration and device management</p>
      </div>

      {/* Vineyard summary */}
      {vineyard && (
        <SectionCard title="Vineyard" subtitle="Current estate">
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            {[
              { label: 'Name', value: vineyard.name },
              { label: 'Region', value: vineyard.region },
              { label: 'Owner', value: vineyard.owner_name },
              { label: 'Blocks', value: String(blocks.length) },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="text-xs text-slate-500">{label}</p>
                <p className="mt-0.5 font-medium text-slate-200">{value || '—'}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Node fleet */}
      <SectionCard
        title="Registered Nodes"
        subtitle={`${activeNodes.length} online · ${staleNodes.length} stale/inactive`}
      >
        {nodes.length === 0 ? (
          <p className="text-sm text-slate-500">No nodes registered yet.</p>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {nodes.map((n) => (
              <NodeRow key={n.id} node={n} />
            ))}
          </div>
        )}
      </SectionCard>

      {/* Unregistered devices */}
      {unregistered.length > 0 && (
        <SectionCard
          title="Unregistered Devices"
          subtitle="These device IDs are sending telemetry but have no node record. Register them below."
        >
          <div className="space-y-2">
            {unregistered.map((d) => (
              <div
                key={d.device_id}
                className="flex items-center justify-between rounded-lg border border-amber-800/20 bg-amber-950/10 px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <Radio className="h-4 w-4 text-amber-400" />
                  <div>
                    <code className="text-sm text-amber-300">{d.device_id}</code>
                    <p className="text-xs text-slate-500">
                      {d.reading_count} readings · last{' '}
                      {new Date(d.last_seen_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <span className="rounded-full border border-amber-800/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-400">
                  Unregistered
                </span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Register new node */}
      <SectionCard
        title="Register New Node"
        subtitle="Provision a device ID to a block before deployment. Telemetry will be attributed once registered."
      >
        {blocks.length === 0 ? (
          <p className="text-sm text-slate-500">No blocks found — seed the demo data first.</p>
        ) : (
          <RegisterNodeForm blocks={blocks} onRegistered={reload} />
        )}
      </SectionCard>

      {/* MQTT info */}
      <SectionCard
        title="Gateway Connection"
        subtitle="Configuration for hardware gateways to connect to this broker"
      >
        <div className="space-y-3 font-mono text-xs">
          {[
            { label: 'MQTT Broker (plain)', value: 'mqtt://localhost:1883' },
            { label: 'MQTT Broker (TLS — prod)', value: 'mqtts://your-server:8883' },
            { label: 'Topic', value: 'vineguard/telemetry' },
            { label: 'Payload format', value: 'JSON · schema_version: "1.0"' },
          ].map(({ label, value }) => (
            <div key={label} className="flex flex-wrap items-center gap-2">
              <span className="w-44 flex-shrink-0 text-slate-500">{label}</span>
              <code className="rounded bg-slate-800 px-2 py-0.5 text-emerald-300">{value}</code>
            </div>
          ))}
        </div>
        <div className="mt-4 rounded-lg border border-slate-700/50 bg-slate-800/40 p-4">
          <p className="text-xs font-semibold text-slate-400">Minimum payload (v1 schema)</p>
          <pre className="mt-2 text-[11px] leading-relaxed text-slate-300">{`{
  "schema_version": "1.0",
  "device_id": "vg-node-001",
  "sensors": {
    "soil_moisture_pct": 24.5,
    "soil_temp_c": 18.2,
    "ambient_temp_c": 21.0,
    "ambient_humidity_pct": 62.0,
    "light_lux": 32000
  },
  "meta": {
    "battery_voltage": 3.87
  }
}`}</pre>
        </div>
      </SectionCard>
    </div>
  );
}
