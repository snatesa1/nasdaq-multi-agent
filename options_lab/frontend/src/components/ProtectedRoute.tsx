'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Loader } from 'lucide-react';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4 text-slate-800">
        <Loader className="h-6 w-6 text-indigo-600 animate-spin" />
        <p className="text-xs font-semibold text-slate-500">Verifying session & loading dashboard...</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4 text-slate-800">
        <Loader className="h-6 w-6 text-indigo-600 animate-spin" />
        <p className="text-xs font-semibold text-slate-500">Redirecting to login...</p>
      </div>
    );
  }

  // Gracefully allow rendering for authenticated session
  return <>{children}</>;
}
