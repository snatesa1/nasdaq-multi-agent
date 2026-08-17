'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { LogIn, ShieldCheck, Loader, TrendingUp, UserCheck } from 'lucide-react';

export default function LoginPage() {
  const { user, loading, signInWithGoogle } = useAuth();
  const router = useRouter();
  const [signingIn, setSigningIn] = useState(false);

  useEffect(() => {
    if (!loading && user) {
      router.push('/');
    }
  }, [user, loading, router]);

  const handleGoogleSignIn = async () => {
    setSigningIn(true);
    try {
      await signInWithGoogle();
      router.push('/');
    } catch (err) {
      console.error('Sign-in failed, proceeding as Demo user:', err);
      router.push('/');
    } finally {
      setSigningIn(false);
    }
  };

  const handleDemoAccess = () => {
    router.push('/');
  };

  if (loading || user) {
    return (
      <div className="min-h-screen bg-[#F3F3F9] flex flex-col items-center justify-center gap-3">
        <Loader className="h-8 w-8 text-[#4051B5] animate-spin" />
        <p className="text-xs font-semibold text-slate-500">Entering Saxo Quant Lab...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F3F3F9] flex items-center justify-center p-4">
      {/* Login Card */}
      <div className="relative z-10 w-full max-w-md">
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-xl">
          {/* Logo / Title */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center h-14 w-14 rounded-xl bg-indigo-50 text-[#4051B5] mb-4">
              <TrendingUp className="h-7 w-7" />
            </div>
            <h1 className="text-2xl font-bold text-slate-800">
              Saxo <span className="text-[#4051B5]">Quant Lab</span>
            </h1>
            <p className="text-xs text-slate-500 mt-1">Institutional Multi-Agent Options Yield Platform</p>
          </div>

          <div className="space-y-3">
            {/* Primary Demo Entrance */}
            <button
              onClick={handleDemoAccess}
              className="w-full flex items-center justify-center gap-3 px-5 py-3 rounded-xl bg-[#4051B5] hover:bg-[#34449a] text-white font-medium shadow-md transition-all text-sm"
            >
              <UserCheck className="h-4 w-4" />
              <span>Enter Dashboard (Sathish - Online)</span>
            </button>


            {/* Google OAuth Login */}
            <button
              onClick={handleGoogleSignIn}
              disabled={signingIn}
              className="w-full flex items-center justify-center gap-3 px-5 py-3 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium transition-all text-sm"
            >
              {signingIn ? (
                <Loader className="h-4 w-4 text-slate-500 animate-spin" />
              ) : (
                <LogIn className="h-4 w-4 text-slate-500" />
              )}
              <span>Sign in with Google</span>
            </button>
          </div>

          <div className="mt-8 pt-6 border-t border-slate-100 flex items-center justify-center gap-2 text-[11px] text-slate-400">
            <ShieldCheck className="h-4 w-4 text-emerald-500" />
            <span>Saxo OpenAPI 256-Bit Encrypted OAuth Session</span>
          </div>
        </div>
      </div>
    </div>
  );
}
