import {
  AlertTriangle,
  BarChart2,
  FileText,
  Home,
  Layers,
  Leaf,
  List,
  Map,
  Settings,
} from 'lucide-react';
import { NavLink, Outlet } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/', label: 'Overview', icon: Home, end: true },
  { to: '/analytics', label: 'Analytics', icon: BarChart2, end: false },
  { to: '/blocks', label: 'Blocks', icon: Layers, end: false },
  { to: '/alerts', label: 'Alerts', icon: AlertTriangle, end: false },
  { to: '/recommendations', label: 'Recommendations', icon: List, end: false },
  { to: '/settings', label: 'Settings', icon: Settings, end: false },
];

const NAV_SOON = [
  { label: 'Field Map', icon: Map },
  { label: 'Reports', icon: FileText },
];

export function Layout() {
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      {/* ── Desktop sidebar ──────────────────────────────────────────── */}
      <aside className="hidden w-56 flex-shrink-0 flex-col border-r border-slate-800/70 bg-slate-900 md:flex">
        {/* Brand */}
        <div className="border-b border-slate-800/70 px-5 py-5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/15">
              <Leaf className="h-4 w-4 text-emerald-400" />
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-emerald-400">
                VineGuard
              </p>
              <p className="text-[10px] text-slate-500">Vineyard Intelligence</p>
            </div>
          </div>
        </div>

        {/* Primary nav */}
        <nav className="flex flex-col gap-0.5 p-3">
          <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
            Main
          </p>
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-emerald-500/15 text-emerald-400'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className={`h-4 w-4 flex-shrink-0 ${
                      isActive ? 'text-emerald-400' : 'text-slate-500'
                    }`}
                  />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Coming soon */}
        {NAV_SOON.length > 0 && (
          <nav className="flex flex-col gap-0.5 px-3 pb-3">
            <p className="mb-1 mt-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-700">
              Coming Soon
            </p>
            {NAV_SOON.map(({ label, icon: Icon }) => (
              <div
                key={label}
                className="flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-700"
              >
                <Icon className="h-4 w-4 flex-shrink-0 text-slate-700" />
                {label}
              </div>
            ))}
          </nav>
        )}

        {/* Footer */}
        <div className="mt-auto border-t border-slate-800/70 px-5 py-4">
          <div className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            <p className="text-[10px] text-slate-600">VineGuard V1 · Prototype</p>
          </div>
        </div>
      </aside>

      {/* ── Mobile top bar ───────────────────────────────────────────── */}
      <div className="fixed inset-x-0 top-0 z-50 flex items-center justify-between border-b border-slate-800 bg-slate-900/95 px-4 py-3 backdrop-blur md:hidden">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-emerald-500/15">
            <Leaf className="h-3.5 w-3.5 text-emerald-400" />
          </div>
          <span className="text-sm font-bold uppercase tracking-widest text-emerald-400">
            VineGuard
          </span>
        </div>
        <nav className="flex gap-0.5">
          {NAV_ITEMS.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `rounded-lg p-2 transition-colors ${
                  isActive
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`
              }
              title={label}
            >
              <Icon className="h-4 w-4" />
            </NavLink>
          ))}
        </nav>
      </div>

      {/* ── Main content ─────────────────────────────────────────────── */}
      <main className="flex flex-1 flex-col overflow-auto pt-14 md:pt-0">
        <Outlet />
      </main>
    </div>
  );
}
