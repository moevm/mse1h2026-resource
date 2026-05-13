import React from 'react';

import type { ReactNode } from 'react';

import { NavLink, useNavigate } from 'react-router-dom';

import { NAV_ITEMS } from '../../lib/constants/navigation';
import { LogoMark } from '../../shared/components/LogoMark';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';
import { IconChevronLeft } from '../icons';

export const Sidebar: React.FC = () => {
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    await navigate('/login', { replace: true });
  };

  return (
    <aside
      className={[
        'hidden lg:flex',
        'relative shrink-0 flex-col border-r border-slate-800/60 bg-slate-950',
        'overflow-x-hidden transition-[width] duration-300 ease-in-out',
        collapsed ? 'lg:w-16 xl:w-20' : 'lg:w-52 xl:w-56',
      ].join(' ')}
    >
      <div
        className={[
          'flex h-14 shrink-0 items-center border-b border-slate-800/60 select-none',
          collapsed ? 'justify-center' : 'gap-3 px-4',
        ].join(' ')}
      >
        <LogoMark />
        {!collapsed && (
          <div className="min-w-0 overflow-hidden">
            <p className="truncate text-sm leading-tight font-bold tracking-tight text-slate-100">Resource Graph</p>
            <p className="truncate text-[10px] leading-tight font-medium tracking-wide text-slate-600 uppercase">
              Topology Explorer
            </p>
          </div>
        )}
      </div>

      <nav className="flex-1 space-y-0.5 px-2 py-3">
        {!collapsed && (
          <p className="px-2 pb-1.5 text-[9px] font-semibold tracking-widest text-slate-700 uppercase select-none">
            Navigation
          </p>
        )}
        {NAV_ITEMS.map(({ to, end, label, icon: Icon, badge }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              [
                'group relative flex items-center gap-3 rounded-lg py-2 text-sm font-medium transition-all duration-150 select-none',
                collapsed ? 'justify-center px-0' : 'px-3',
                isActive ? 'bg-blue-600/12 text-blue-400' : 'text-slate-500 hover:bg-slate-800/60 hover:text-slate-200',
              ].join(' ')
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute top-1/2 left-0 h-4 w-0.5 -translate-y-1/2 rounded-full bg-blue-400" />
                )}
                <Icon
                  className={[
                    'h-4.5 w-4.5 shrink-0 transition-colors',
                    isActive ? 'text-blue-400' : 'text-slate-500 group-hover:text-slate-300',
                  ].join(' ')}
                />
                {!collapsed && (
                  <>
                    <span className="flex-1 truncate whitespace-nowrap">{label}</span>
                    {badge && (
                      <span className="rounded bg-slate-800 px-1 py-0.5 font-mono text-[10px] leading-none text-slate-500">
                        {badge}
                      </span>
                    )}
                  </>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <button
        onClick={() => void handleLogout()}
        title="Sign out"
        className="flex h-9 w-full shrink-0 items-center justify-center border-t border-slate-800/60 text-xs text-slate-700 transition-colors hover:bg-slate-800/30 hover:text-red-400"
      >
        {collapsed ? 'Out' : 'Sign Out'}
      </button>

      <button
        onClick={toggleSidebar}
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        className="flex h-9 w-full shrink-0 items-center justify-center border-t border-slate-800/60 text-slate-700 transition-colors hover:bg-slate-800/30 hover:text-slate-400"
      >
        <IconChevronLeft
          className={['h-3.5 w-3.5 transition-transform duration-300', collapsed ? 'rotate-180' : ''].join(' ')}
        />
      </button>
    </aside>
  );
};

interface HeaderProps {
  children?: ReactNode;
}

export const Header: React.FC<HeaderProps> = ({ children }) => {
  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-slate-800/60 bg-slate-950/90 px-5 backdrop-blur-md">
      {children}
    </header>
  );
};
