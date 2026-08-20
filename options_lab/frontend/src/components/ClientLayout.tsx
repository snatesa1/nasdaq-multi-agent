'use client';

import React, { useEffect } from 'react';
import Header from '@/components/Header';
import Sidebar, { SidebarProvider, useSidebar } from '@/components/Sidebar';
import ErrorBoundary from '@/components/ErrorBoundary';
import { initClientLogger } from '@/lib/logger';

function LayoutShell({ children }: { children: React.ReactNode }) {
  const { isCollapsed } = useSidebar();

  useEffect(() => {
    initClientLogger();
  }, []);

  return (
    <div className="min-h-screen bg-[#F3F3F9] text-slate-800 flex flex-col">
      {/* Fixed Velzon Top Header Bar */}
      <Header />

      <div className="flex flex-1 pt-16">
        {/* Velzon Grouped Sidebar */}
        <Sidebar />

        {/* Main Dashboard Canvas — Fluid & Responsive */}
        <main
          className={`flex-1 transition-all duration-300 ease-in-out ${
            /* Desktop margin matches sidebar width */
            isCollapsed ? 'lg:ml-[72px]' : 'lg:ml-64'
          } p-4 sm:p-6 lg:p-8 min-w-0 overflow-x-hidden`}
        >
          <div className="mx-auto max-w-[1600px] space-y-6">
            <ErrorBoundary>
              {children}
            </ErrorBoundary>
          </div>
        </main>
      </div>
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

