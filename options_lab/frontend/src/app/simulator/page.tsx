'use client';

import React, { useState, useEffect } from 'react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts';
import { optionsApi } from '@/lib/api';
import { Activity, HelpCircle, RefreshCw, Cpu, Award } from 'lucide-react';
import Link from 'next/link';
import ProtectedRoute from '@/components/ProtectedRoute';

export default function SimulatorPage() {
  // Parameters state
  const [S0, setS0] = useState<number>(80);
  const [mu, setMu] = useState<number>(0.001);
  const [sigma, setSigma] = useState<number>(0.03);
  const [T, setT] = useState<number>(100 / 365.0);
  const [N, setN] = useState<number>(1000);
  const [numPaths, setNumPaths] = useState<number>(50);
  const [K, setK] = useState<number>(100);

  // Results state
  const [paths, setPaths] = useState<any[]>([]);
  const [terminalPrices, setTerminalPrices] = useState<number[]>([]);
  const [histogramData, setHistogramData] = useState<any[]>([]);
  const [timeGrid, setTimeGrid] = useState<number[]>([]);
  
  // Pricing comparisons
  const [prices, setPrices] = useState({
    bsPut: 0,
    mcPut: 0,
    legacyPut: 0,
    mcError: 0
  });

  const [simulating, setSimulating] = useState(false);

  const runSimulation = async () => {
    setSimulating(true);
    try {
      // 1. Run GBM Paths simulation
      const gbmRes = await optionsApi.simulateGbm({
        S0,
        mu,
        sigma,
        T,
        N,
        num_paths: numPaths
      });

      // Format paths for Recharts
      const chartPaths = gbmRes.paths.map((path: number[], pathIdx: number) => {
        return path.map((price: number, stepIdx: number) => ({
          step: stepIdx,
          [`path_${pathIdx}`]: parseFloat(price.toFixed(2))
        }));
      });

      // Pivot the paths to shape (N+1, {step, path_0, path_1, ...})
      const pivotedPaths = gbmRes.time_grid.map((time: number, stepIdx: number) => {
        const row: any = { step: stepIdx, time: parseFloat(time.toFixed(4)) };
        chartPaths.forEach((path: any, pathIdx: number) => {
          row[`path_${pathIdx}`] = path[stepIdx][`path_${pathIdx}`];
        });
        return row;
      });

      setPaths(pivotedPaths);
      setTimeGrid(gbmRes.time_grid);
      setTerminalPrices(gbmRes.terminal_prices);

      // Generate histogram bins for terminal prices
      const minP = Math.min(...gbmRes.terminal_prices);
      const maxP = Math.max(...gbmRes.terminal_prices);
      const numBins = 15;
      const binWidth = (maxP - minP) / numBins;
      const bins = Array.from({ length: numBins }, (_, i) => ({
        binStart: minP + i * binWidth,
        binEnd: minP + (i + 1) * binWidth,
        count: 0
      }));

      gbmRes.terminal_prices.forEach((price: number) => {
        for (let i = 0; i < bins.length; i++) {
          if (price >= bins[i].binStart && price <= bins[i].binEnd) {
            bins[i].count += 1;
            break;
          }
        }
      });

      const formattedBins = bins.map((b) => ({
        name: `$${((b.binStart + b.binEnd)/2).toFixed(1)}`,
        frequency: b.count
      }));
      setHistogramData(formattedBins);

      // 2. Fetch Option Pricing comparisons
      const bsRes = await optionsApi.priceAnalytical({
        S: S0,
        K,
        T,
        r: mu,
        sigma,
        option_type: 'put'
      });

      const mcRes = await optionsApi.priceMonteCarlo({
        S0,
        K,
        T,
        r: mu,
        sigma,
        option_type: 'put',
        num_paths: 2000
      });

      const legacyRes = await optionsApi.priceLegacyLab({
        S0,
        K,
        T,
        r: mu,
        sigma,
        N
      });

      setPrices({
        bsPut: bsRes.price,
        mcPut: mcRes.price,
        legacyPut: legacyRes.price,
        mcError: mcRes.standard_error
      });

    } catch (err) {
      console.error('Simulation run failed:', err);
    } finally {
      setSimulating(false);
    }
  };

  useEffect(() => {
    runSimulation();
  }, []);

  const loadLabDefaults = () => {
    setS0(80);
    setMu(0.001);
    setSigma(0.03);
    setT(100 / 365.0);
    setN(1000);
    setK(100);
    setNumPaths(50);
  };

  return (
    <ProtectedRoute>
      <div className="space-y-6 pb-12">
        {/* Banner Header - Velzon Light Theme */}
        <div className="relative overflow-hidden rounded-xl bg-white p-6 sm:p-8 border border-slate-200/80 shadow-sm flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-[#4051B5] border border-indigo-100">
              <Cpu className="h-3.5 w-3.5" /> Geometric Brownian Motion Engine
            </span>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight sm:text-3xl">
              GBM & Monte Carlo <span className="text-[#4051B5]">Simulator</span>
            </h1>
            <p className="text-slate-500 text-xs sm:text-sm leading-relaxed">
              Simulate stochastic stock price paths via Geometric Brownian Motion (GBM) and evaluate Monte Carlo numerical option pricing against analytical Black-Scholes models.
            </p>
          </div>

          <div className="flex gap-3 flex-shrink-0">
            <button 
              onClick={loadLabDefaults}
              className="rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 px-4 py-2 text-xs font-bold text-slate-700 transition shadow-sm"
            >
              Lab Defaults
            </button>
            <button 
              onClick={runSimulation}
              disabled={simulating}
              className="flex items-center gap-2 rounded-lg bg-[#4051B5] hover:bg-[#34449a] px-4 py-2 text-xs font-semibold text-white shadow-sm transition disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${simulating ? 'animate-spin' : ''}`} />
              Run Simulation
            </button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Sliders Control Panel */}
          <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-6 h-fit">
            <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
              <Cpu className="h-4 w-4 text-[#4051B5]" /> Simulation Parameters
            </h3>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-600 mb-1">
                  <span>Initial Stock Price (S0)</span>
                  <span className="font-mono text-[#4051B5] font-bold">${S0}</span>
                </div>
                <input 
                  type="range" min="10" max="500" step="5" value={S0} 
                  onChange={(e) => setS0(Number(e.target.value))} 
                  className="w-full h-2 bg-slate-100 rounded-lg accent-[#4051B5] cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-600 mb-1">
                  <span>Strike Price (K)</span>
                  <span className="font-mono text-slate-800 font-bold">${K}</span>
                </div>
                <input 
                  type="range" min="10" max="500" step="5" value={K} 
                  onChange={(e) => setK(Number(e.target.value))} 
                  className="w-full h-2 bg-slate-100 rounded-lg accent-[#4051B5] cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-600 mb-1">
                  <span>Drift / Rate (mu / r)</span>
                  <span className="font-mono text-slate-800 font-bold">{(mu * 100).toFixed(2)}%</span>
                </div>
                <input 
                  type="range" min="-0.2" max="0.5" step="0.005" value={mu} 
                  onChange={(e) => setMu(Number(e.target.value))} 
                  className="w-full h-2 bg-slate-100 rounded-lg accent-[#4051B5] cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-600 mb-1">
                  <span>Volatility (sigma)</span>
                  <span className="font-mono text-slate-800 font-bold">{(sigma * 100).toFixed(1)}%</span>
                </div>
                <input 
                  type="range" min="0.01" max="1.5" step="0.01" value={sigma} 
                  onChange={(e) => setSigma(Number(e.target.value))} 
                  className="w-full h-2 bg-slate-100 rounded-lg accent-[#4051B5] cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-600 mb-1">
                  <span>Time to Maturity (T in Days)</span>
                  <span className="font-mono text-slate-800 font-bold">{Math.round(T * 365)} days</span>
                </div>
                <input 
                  type="range" min="5" max="365" step="5" value={Math.round(T * 365)} 
                  onChange={(e) => setT(Number(e.target.value) / 365.0)} 
                  className="w-full h-2 bg-slate-100 rounded-lg accent-[#4051B5] cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-600 mb-1">
                  <span>Number of Steps (N)</span>
                  <span className="font-mono text-slate-800 font-bold">{N}</span>
                </div>
                <input 
                  type="range" min="10" max="2000" step="50" value={N} 
                  onChange={(e) => setN(Number(e.target.value))} 
                  className="w-full h-2 bg-slate-100 rounded-lg accent-[#4051B5] cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-600 mb-1">
                  <span>Rendered Paths</span>
                  <span className="font-mono text-slate-800 font-bold">{numPaths}</span>
                </div>
                <input 
                  type="range" min="5" max="100" step="5" value={numPaths} 
                  onChange={(e) => setNumPaths(Number(e.target.value))} 
                  className="w-full h-2 bg-slate-100 rounded-lg accent-[#4051B5] cursor-pointer"
                />
              </div>
            </div>
          </div>

          {/* Path Charts & Distributions */}
          <div className="lg:col-span-2 space-y-6">
            {/* Paths Chart */}
            <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-4">
              <h3 className="text-base font-bold text-slate-800">Simulated Price Trajectories</h3>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={paths}>
                    <XAxis dataKey="step" stroke="#94a3b8" fontSize={11} />
                    <YAxis domain={['auto', 'auto']} stroke="#94a3b8" fontSize={11} tickFormatter={(v) => `$${v}`} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '12px', color: '#1e293b' }}
                    />
                    {Array.from({ length: numPaths }).map((_, idx) => (
                      <Line 
                        key={idx} 
                        type="monotone" 
                        dataKey={`path_${idx}`} 
                        stroke={`hsl(${220 + (idx * 5) % 40}, 60%, 50%)`} 
                        strokeWidth={1.2} 
                        dot={false} 
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              {/* Histogram of Terminal Prices */}
              <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-4">
                <h3 className="text-base font-bold text-slate-800">Terminal Price Distribution</h3>
                <div className="h-48 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={histogramData}>
                      <XAxis dataKey="name" stroke="#94a3b8" fontSize={10} />
                      <YAxis stroke="#94a3b8" fontSize={10} />
                      <Tooltip contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px' }} />
                      <Bar dataKey="frequency" fill="#4051B5" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-[11px] text-slate-400 text-center font-medium">Approaches log-normal distribution as paths count increases.</p>
              </div>

              {/* Pricing Model Comparison */}
              <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-4 flex flex-col justify-between">
                <h3 className="text-base font-bold text-slate-800">Put Price Model Comparison</h3>
                <div className="space-y-3 font-mono">
                  <div className="flex justify-between items-center text-xs py-1.5 border-b border-slate-100">
                    <span className="text-slate-600 font-sans font-medium">Black-Scholes (Analytical)</span>
                    <span className="font-bold text-[#0AB39C]">${prices.bsPut.toFixed(4)}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs py-1.5 border-b border-slate-100">
                    <span className="text-slate-600 font-sans font-medium">Monte Carlo (Standard)</span>
                    <span className="font-bold text-slate-800">
                      ${prices.mcPut.toFixed(4)} <span className="text-[10px] text-slate-400">± {prices.mcError.toFixed(4)}</span>
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-xs py-1.5 text-rose-600">
                    <span className="font-sans font-medium">Legacy Lab Model</span>
                    <span className="font-bold">${prices.legacyPut.toFixed(6)}</span>
                  </div>
                </div>

                {/* Socratic Callout */}
                <div className="rounded-xl bg-amber-50 border border-amber-200 p-4 text-xs">
                  <div className="flex items-start gap-2.5">
                    <HelpCircle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <p className="font-bold text-slate-800">Socratic Query:</p>
                      <p className="text-slate-600 leading-relaxed text-[11px]">
                        Notice the discrepancy? The Legacy Lab puts the price at <span className="font-mono text-rose-600 font-bold">${prices.legacyPut.toFixed(6)}</span> while Black-Scholes shows <span className="font-mono text-emerald-600 font-bold">${prices.bsPut.toFixed(4)}</span>.
                      </p>
                      <Link href="/learn" className="text-xs text-[#4051B5] hover:underline font-bold block mt-1">
                        Ask the Socratic Tutor to explain the bug &rarr;
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
