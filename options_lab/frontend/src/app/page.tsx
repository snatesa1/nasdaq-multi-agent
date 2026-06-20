'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { 
  TrendingUp, 
  Cpu, 
  HelpCircle, 
  ArrowUpRight, 
  Shield, 
  DollarSign, 
  Activity 
} from 'lucide-react';
import { optionsApi } from '@/lib/api';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import ProtectedRoute from '@/components/ProtectedRoute';

interface Quote {
  symbol: string;
  current_price: number;
  historical_volatility: number;
  is_simulated: boolean;
}

export default function Dashboard() {
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [loadingQuotes, setLoadingQuotes] = useState(true);
  const [gbmPath, setGbmPath] = useState<any[]>([]);
  const [loadingGbm, setLoadingGbm] = useState(true);

  // Fetch initial quotes for major dashboard tickers
  useEffect(() => {
    async function fetchAll() {
      try {
        const symbols = ['AAPL', 'NVDA', 'PANW', 'TSLA'];
        const results: Record<string, Quote> = {};
        for (const sym of symbols) {
          const data = await optionsApi.getQuote(sym);
          results[sym] = data;
        }
        setQuotes(results);
      } catch (err) {
        console.error('Failed to load quotes:', err);
      } finally {
        setLoadingQuotes(false);
      }
    }
    fetchAll();
  }, []);

  // Fetch a sample single GBM path to animate on the dashboard
  useEffect(() => {
    async function fetchGbm() {
      try {
        const data = await optionsApi.simulateGbm({
          S0: 100,
          mu: 0.05,
          sigma: 0.20,
          T: 0.5,
          N: 50,
          num_paths: 1
        });
        
        // Format path for Recharts
        const chartData = data.paths[0].map((val: number, idx: number) => ({
          step: idx,
          price: parseFloat(val.toFixed(2))
        }));
        setGbmPath(chartData);
      } catch (err) {
        console.error('Failed to load GBM demo path:', err);
      } finally {
        setLoadingGbm(false);
      }
    }
    fetchGbm();
  }, []);

  return (
    <ProtectedRoute>
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-[#1e2538] to-[#141824] p-8 border border-slate-800">
        <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-[#5ba4b5]/5 blur-3xl" />
        <div className="absolute right-20 bottom-0 h-32 w-32 rounded-full bg-[#7ec8a0]/5 blur-3xl" />
        
        <div className="relative z-10 max-w-2xl space-y-4">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#5ba4b5]/10 px-3 py-1 text-xs font-semibold text-[#5ba4b5]">
            <Activity className="h-3 w-3 animate-pulse" /> Socratic Learning Environment
          </span>
          <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight sm:text-4xl">
            Welcome to Options<span className="text-[#5ba4b5]">Lab</span>
          </h1>
          <p className="text-slate-400 text-sm sm:text-base leading-relaxed">
            Welcome to your options trading and risk management playground. Run vectorized Brownian motion simulations,
            model multi-leg option strategies, and engage with the Socratic Tutor to learn hedging and arbitrage without capital loss.
          </p>
          <div className="pt-2 flex flex-wrap gap-4">
            <Link href="/learn" className="inline-flex items-center gap-2 rounded-lg bg-[#5ba4b5] px-4 py-2.5 text-sm font-semibold text-slate-900 transition hover:bg-[#4a91a2]">
              Start Socratic Lesson <ArrowUpRight className="h-4 w-4" />
            </Link>
            <Link href="/simulator" className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/50 px-4 py-2.5 text-sm font-semibold text-slate-300 transition hover:bg-slate-800">
              Go to Simulator
            </Link>
          </div>
        </div>
      </div>

      {/* Quote Grid */}
      <div className="grid gap-6 md:grid-cols-4">
        {loadingQuotes ? (
          Array.from({ length: 4 }).map((_, idx) => (
            <div key={idx} className="glass-card p-6 h-32 animate-pulse bg-slate-900/30 border border-slate-800 rounded-lg" />
          ))
        ) : (
          Object.values(quotes).map((quote) => (
            <div key={quote.symbol} className="glass-card p-6 hover:-translate-y-1 transition-all duration-300">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">{quote.symbol}</span>
                  <h3 className="text-2xl font-bold font-mono mt-1 text-slate-200">${quote.current_price.toFixed(2)}</h3>
                </div>
                <span className="rounded bg-[#5ba4b5]/10 px-2 py-0.5 text-[10px] font-semibold text-[#5ba4b5]">
                  {quote.is_simulated ? 'Simulated' : 'yFinance'}
                </span>
              </div>
              <div className="mt-4 flex items-center justify-between text-xs">
                <span className="text-slate-400">Ann. Volatility</span>
                <span className="font-mono text-[#7ec8a0] font-semibold">{(quote.historical_volatility * 100).toFixed(1)}%</span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* GBM Preview Chart */}
        <div className="glass-card p-6 lg:col-span-2 space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold text-slate-200">Geometric Brownian Motion</h2>
              <p className="text-xs text-slate-400">Random walk simulations at S0=100, &sigma;=20%</p>
            </div>
            <Link href="/simulator" className="text-xs text-[#5ba4b5] hover:underline flex items-center gap-1">
              Playground <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="h-64 w-full">
            {loadingGbm ? (
              <div className="h-full w-full flex items-center justify-center text-xs text-slate-400">Loading paths...</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={gbmPath}>
                  <XAxis dataKey="step" tick={{ fill: '#64748b', fontSize: 10 }} stroke="rgba(255,255,255,0.05)" />
                  <YAxis domain={['auto', 'auto']} tick={{ fill: '#64748b', fontSize: 10 }} stroke="rgba(255,255,255,0.05)" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1a1d24', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px' }}
                    labelStyle={{ color: '#64748b', fontSize: 10 }}
                    itemStyle={{ color: '#5ba4b5', fontSize: 12 }}
                  />
                  <Line type="monotone" dataKey="price" stroke="#5ba4b5" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Lesson Roadmap */}
        <div className="glass-card p-6 space-y-4">
          <h2 className="text-lg font-bold text-slate-200">Socratic Syllabus</h2>
          <div className="space-y-4">
            <div className="flex gap-3">
              <div className="h-8 w-8 rounded-lg bg-[#5ba4b5]/10 text-[#5ba4b5] flex items-center justify-center flex-shrink-0">
                <Cpu className="h-4 w-4" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-200">GBM & Monte Carlo Pricing</h4>
                <p className="text-xs text-slate-400 mt-0.5">Explore conditional expectation pricing models.</p>
                <Link href="/simulator" className="text-xs text-[#5ba4b5] hover:underline mt-1.5 inline-block">Start Lab &rarr;</Link>
              </div>
            </div>

            <div className="flex gap-3">
              <div className="h-8 w-8 rounded-lg bg-[#7ec8a0]/10 text-[#7ec8a0] flex items-center justify-center flex-shrink-0">
                <DollarSign className="h-4 w-4" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-200">Income Generation (Selling Calls)</h4>
                <p className="text-xs text-slate-400 mt-0.5">Covered Calls vs Cash-Secured Puts.</p>
                <Link href="/strategies" className="text-xs text-[#7ec8a0] hover:underline mt-1.5 inline-block">Design Strategy &rarr;</Link>
              </div>
            </div>

            <div className="flex gap-3">
              <div className="h-8 w-8 rounded-lg bg-red-500/10 text-[#dc3545] flex items-center justify-center flex-shrink-0">
                <Shield className="h-4 w-4" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-200">Hedging & Capital Preservation</h4>
                <p className="text-xs text-slate-400 mt-0.5">How to collar shares of PANW, AAPL, etc.</p>
                <Link href="/learn" className="text-xs text-[#dc3545] hover:underline mt-1.5 inline-block">Discuss with Tutor &rarr;</Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    </ProtectedRoute>
  );
}
