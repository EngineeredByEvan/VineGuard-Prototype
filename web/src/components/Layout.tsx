import { AlertTriangle, BarChart2, Home, Leaf, List } from 'lucide-react';
import { NavLink, Outlet } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/', label: 'Overview', icon: Home, end: true },
  { to: '/blocks', label: 'Blocks', icon: BarChart2, end: false },
  { to: '/alerts', label: 'Alerts', icon: AlertTriangle, end: false },
  { to: '/recommendations', label: 'Recommendations', icon: List, end: false },
];

export function Layout() {
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      {/* Sidebar */}
      <aside className="hidden w-60 flex-shrink-0 flex-col border-r border-slate-800 bg-slate-900 md:flex">
        {/* Brand */}
        <div className="border-b border-slate-800 px-6 py-5">
          <div className="flex items-center gap-2">
            <Leaf className="h-6 w-6 text-emerald-400" />
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-emerald-400">
                VineGuard
              </p>
              <p className="text-xs text-slate-500">Vineyard Intelligence</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-emerald-500/15 text-emerald-400'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
                }`
              }
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-800 px-6 py-4">
          <p className="text-xs text-slate-600">VineGuard V1</p>
        </div>
      </aside>

      {/* Mobile top nav */}
      <div className="fixed inset-x-0 top-0 z-50 flex items-center justify-between border-b border-slate-800 bg-slate-900/95 px-4 py-3 backdrop-blur md:hidden">
        <div className="flex items-center gap-2">
          <Leaf className="h-5 w-5 text-emerald-400" />
          <span className="text-sm font-semibold uppercase tracking-widest text-emerald-400">
            VineGuard
          </span>
        </div>
        <nav className="flex gap-1">
          {NAV_ITEMS.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `rounded-md p-2 transition-colors ${
                  isActive
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
                }`
              }
              title={label}
            >
              <Icon className="h-4 w-4" />
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Main content */}
      <main className="flex flex-1 flex-col overflow-auto pt-14 md:pt-0">
        <Outlet />
      </main>
    </div>
  );
}
