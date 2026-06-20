'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { TrendingUp, Loader } from 'lucide-react';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-8 w-8 text-[#5ba4b5]" />
          <span className="text-xl font-bold text-slate-100">
            Options<span className="text-[#5ba4b5]">Lab</span>
          </span>
        </div>
        <Loader className="h-6 w-6 text-[#5ba4b5] animate-spin" />
        <p className="text-xs text-slate-500">Verifying authentication...</p>
      </div>
    );
  }

  if (!user) {
    router.push('/login');
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4">
        <Loader className="h-6 w-6 text-[#5ba4b5] animate-spin" />
        <p className="text-xs text-slate-500">Redirecting to login...</p>
      </div>
    );
  }

  return <>{children}</>;
}
