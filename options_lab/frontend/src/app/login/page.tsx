'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { LogIn, ShieldCheck, Loader, TrendingUp } from 'lucide-react';

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
    } catch (err) {
      console.error('Sign-in failed:', err);
    } finally {
      setSigningIn(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0f1117] flex items-center justify-center">
        <Loader className="h-8 w-8 text-[#5ba4b5] animate-spin" />
      </div>
    );
  }

  if (user) {
    return (
      <div className="min-h-screen bg-[#0f1117] flex items-center justify-center">
        <Loader className="h-8 w-8 text-[#5ba4b5] animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0f1117] flex items-center justify-center p-4">
      {/* Background decorations */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 h-96 w-96 rounded-full bg-[#5ba4b5]/5 blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 h-80 w-80 rounded-full bg-[#7ec8a0]/5 blur-3xl" />
      </div>

      {/* Login Card */}
      <div className="relative z-10 w-full max-w-md">
        <div className="rounded-2xl border border-slate-800 bg-[#161924]/80 backdrop-blur-xl p-10 shadow-2xl shadow-black/40">
          {/* Logo / Title */}
          <div className="text-center mb-10">
            <div className="inline-flex items-center justify-center h-16 w-16 rounded-2xl bg-[#5ba4b5]/10 border border-[#5ba4b5]/20 mb-5">
              <TrendingUp className="h-8 w-8 text-[#5ba4b5]" />
            </div>
            <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">
              Options<span className="text-[#5ba4b5]">Lab</span>
            </h1>
            <p className="text-slate-400 text-sm mt-2">
              Socratic Simulator & Portfolio Intelligence
            </p>
          </div>

          {/* Security badge */}
          <div className="flex items-center gap-2 rounded-lg bg-[#7ec8a0]/5 border border-[#7ec8a0]/10 px-4 py-3 mb-8">
            <ShieldCheck className="h-5 w-5 text-[#7ec8a0] flex-shrink-0" />
            <p className="text-xs text-slate-400">
              Authenticated access with Google. Your data stays secure.
            </p>
          </div>

          {/* Google Sign In Button */}
          <button
            onClick={handleGoogleSignIn}
            disabled={signingIn}
            className="w-full flex items-center justify-center gap-3 rounded-xl bg-slate-100 hover:bg-white px-6 py-3.5 text-sm font-semibold text-slate-900 transition-all duration-200 hover:shadow-lg hover:shadow-[#5ba4b5]/10 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {signingIn ? (
              <Loader className="h-5 w-5 animate-spin" />
            ) : (
              <LogIn className="h-5 w-5" />
            )}
            {signingIn ? 'Signing in...' : 'Sign in with Google'}
          </button>

          {/* Footer */}
          <p className="text-center text-[10px] text-slate-600 mt-8">
            By signing in, you agree to use this platform for educational and personal analysis purposes only.
          </p>
        </div>
      </div>
    </div>
  );
}
