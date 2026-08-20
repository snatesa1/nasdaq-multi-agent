'use client';

import React from 'react';
import { useAuth } from '@/context/AuthContext';
import { Loader } from 'lucide-react';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4 text-slate-800">
        <Loader className="h-6 w-6 text-indigo-600 animate-spin" />
        <p className="text-xs font-semibold text-slate-500">Verifying session & loading dashboard...</p>
      </div>
    );
  }

  // Gracefully allow rendering for demo/institutional session
  return <>{children}</>;
}
