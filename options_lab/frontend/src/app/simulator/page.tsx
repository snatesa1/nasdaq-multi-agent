'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function SimulatorRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/');
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <p className="text-xs text-slate-400 font-semibold">Redirecting to Live Portfolio Dashboard...</p>
    </div>
  );
}
