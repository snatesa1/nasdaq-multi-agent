'use client';

import React from 'react';
import Sidebar, { SidebarProvider, useSidebar } from '@/components/Sidebar';

function LayoutShell({ children }: { children: React.ReactNode }) {
  const { isCollapsed } = useSidebar();

  return (
    <div className="flex">
      <Sidebar />
      {/* Main content area — shifts based on sidebar state */}
      <main
        className={`flex-1 min-h-screen transition-all duration-300 ease-in-out ${
          /* Mobile: no margin (sidebar is a drawer overlay), add top padding for mobile header */
          'pt-14 lg:pt-0'
        } ${
          /* Desktop: margin matches sidebar width */
          isCollapsed ? 'lg:ml-[72px]' : 'lg:ml-64'
        } p-4 sm:p-6 lg:p-8`}
      >
        <div className="mx-auto max-w-7xl">
          {children}
        </div>
      </main>
    </div>
  );
}

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <LayoutShell>{children}</LayoutShell>
    </SidebarProvider>
  );
}
