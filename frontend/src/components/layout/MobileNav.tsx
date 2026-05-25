import React, { useState } from 'react';

import { NavLink } from 'react-router-dom';

import { useGraphUiStore } from '../../features/graph/store';
import { NAV_ITEMS } from '../../lib/constants/navigation';
import { STATUS_CONFIG } from '../../lib/constants/status';
import { LogoMark } from '../../shared/components/LogoMark';
import { IconMenu, IconX } from '../icons';

export const MobileNav: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const backendStatus = useGraphUiStore((s) => s.backendStatus);

  return (
    <>
      {/* Hamburger button - visible on mobile only */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed top-3 left-3 z-50 rounded-xl border border-slate-700/60 bg-slate-800/90 p-2.5 shadow-lg backdrop-blur-sm lg:hidden"
        aria-label="Open menu"
      >
        <IconMenu className="h-5 w-5 text-slate-300" />
      </button>

      {/* Overlay */}
      {isOpen && (
        <button
          type="button"
          className="animate-fade-in fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setIsOpen(false)}
          aria-label="Close menu overlay"
        />
      )}

      {/* Drawer */}
      <aside
        className={[
          'fixed top-0 left-0 z-50 h-full w-64 border-r border-slate-800/60 bg-slate-950 lg:hidden',
          'flex flex-col',
          'transform transition-transform duration-300 ease-out',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        ].join(' ')}
      >
        {/* Header */}
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-slate-800/60 px-4">
          <div className="flex items-center gap-3">
            <LogoMark />
            <div>
              <p className="text-sm leading-tight font-bold text-slate-100">Resource Graph</p>
              <p className="text-[10px] leading-tight font-medium tracking-wide text-slate-600 uppercase">
                Topology Explorer
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="rounded-lg p-1.5 transition-colors hover:bg-slate-800"
            aria-label="Close menu"
          >
            <IconX className="h-5 w-5 text-slate-400" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
          <p className="px-2 pb-1.5 text-[9px] font-semibold tracking-widest text-slate-700 uppercase select-none">
            Navigation
          </p>
          {NAV_ITEMS.map(({ to, end, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setIsOpen(false)}
              className={({ isActive }) =>
                [
                  'group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150',
                  isActive
                    ? 'bg-blue-600/12 text-blue-400'
                    : 'text-slate-500 hover:bg-slate-800/60 hover:text-slate-200',
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
                  <span className="truncate">{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Status indicator */}
        <div className="shrink-0 border-t border-slate-800/60 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className={['h-2 w-2 shrink-0 rounded-full', STATUS_CONFIG[backendStatus].color].join(' ')} />
            <span className="text-[11px] font-medium text-slate-600">{STATUS_CONFIG[backendStatus].label}</span>
          </div>
        </div>
      </aside>
    </>
  );
};
