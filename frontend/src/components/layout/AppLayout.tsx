import React from 'react';

import type { ReactNode } from 'react';

import { MobileNav } from './MobileNav';
import { Header, Sidebar } from './Sidebar';

interface AppLayoutProps {
  children: ReactNode;
  headerContent?: ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children, headerContent }) => {
  return (
    <div className="flex h-screen min-h-0 w-screen overflow-hidden bg-slate-950">
      <MobileNav />

      <Sidebar />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <Header>
          <div className="w-10 shrink-0 lg:hidden" />
          {headerContent}
        </Header>
        <main className="min-h-0 flex-1 overflow-hidden">{children}</main>
      </div>
    </div>
  );
};
