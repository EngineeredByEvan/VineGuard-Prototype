import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { useMemo, useState } from 'react';
import { Menu, Power, Sprout } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { cn } from '@/utils';

const navigation = [
  { to: '/', label: 'Overview' },
  { to: '/insights', label: 'Insights' }
];

const DashboardLayout = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const activeNav = useMemo(() => {
    if (location.pathname.startsWith('/sites')) return '/sites';
    if (location.pathname.startsWith('/nodes')) return '/nodes';
    return navigation.find((nav) => nav.to === location.pathname)?.to ?? '/';
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-border/50 bg-slate-900/70 p-6 shadow-2xl backdrop-blur-lg transition-transform lg:static lg:translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/20 text-primary">
            <Sprout className="h-6 w-6" />
          </div>
          <div>
            <p className="text-lg font-semibold">VineGuard</p>
            <p className="text-xs text-muted-foreground">Smart viticulture control</p>
          </div>
        </div>

        <nav className="mt-10 space-y-2">
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'flex items-center rounded-lg px-3 py-2 text-sm font-medium transition',
                  isActive || activeNav === item.to
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-slate-800/60 hover:text-foreground'
                )
              }
              onClick={() => setMobileOpen(false)}
            >
              {item.label}
            </NavLink>
          ))}
          <NavLink
            to="/sites/demo-vineyard"
            className={({ isActive }) =>
              cn(
                'flex items-center rounded-lg px-3 py-2 text-sm font-medium transition',
                isActive || activeNav === '/sites'
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-slate-800/60 hover:text-foreground'
              )
            }
            onClick={() => setMobileOpen(false)}
          >
            Sites
          </NavLink>
          <NavLink
            to="/nodes/alpha"
            className={({ isActive }) =>
              cn(
                'flex items-center rounded-lg px-3 py-2 text-sm font-medium transition',
                isActive || activeNav === '/nodes'
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-slate-800/60 hover:text-foreground'
              )
            }
            onClick={() => setMobileOpen(false)}
          >
            Nodes
          </NavLink>
        </nav>

        <div className="mt-auto flex flex-col gap-3 rounded-lg border border-border/40 bg-slate-950/50 p-4 text-xs text-muted-foreground">
          <p className="text-sm font-semibold text-foreground">{user?.name ?? user?.email}</p>
          <p>{user?.orgId ? `Org: ${user.orgId}` : 'Demo organization'}</p>
          <Button variant="ghost" className="mt-2 justify-start gap-2 text-sm" onClick={logout}>
            <Power className="h-4 w-4" /> Sign out
          </Button>
        </div>
      </aside>

      <div className="flex flex-1 flex-col lg:ml-64">
        <header className="flex items-center justify-between border-b border-border/50 bg-slate-900/60 px-6 py-4 backdrop-blur">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              className="lg:hidden"
              size="icon"
              onClick={() => setMobileOpen((prev) => !prev)}
            >
              <Menu className="h-5 w-5" />
            </Button>
            <div>
              <p className="text-xl font-semibold">Operational Dashboard</p>
              <p className="text-sm text-muted-foreground">
                Monitor vineyard health, telemetry and commands in real time.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="hidden sm:flex flex-col text-right">
              <span className="text-sm font-medium text-foreground">{user?.name ?? 'Demo Grower'}</span>
              <span>{user?.email}</span>
            </div>
            <Link
              to="https://docs.vineguard.local"
              target="_blank"
              className="rounded-full border border-primary/40 px-4 py-1 text-xs font-medium text-primary hover:bg-primary/10"
            >
              View docs
            </Link>
          </div>
        </header>

        <main className="flex-1 space-y-6 px-4 py-6 sm:px-6 lg:px-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;
