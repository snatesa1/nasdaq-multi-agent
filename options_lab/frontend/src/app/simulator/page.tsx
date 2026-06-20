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
      // Paths is nested list of shape (numPaths, N+1)
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
        r: mu, // risk free rate in pricing is drift under risk neutral
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

  // Preset button to trigger exact user lab parameters
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
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">GBM & Monte Carlo Sandbox</h1>
          <p className="text-slate-400 text-sm">Simulate stock price paths and compare analytical and numerical option prices.</p>
        </div>
        <div className="flex gap-4">
          <button 
            onClick={loadLabDefaults}
            className="rounded-lg border border-slate-700 bg-slate-900/50 px-4 py-2 text-xs font-semibold text-[#accent] transition hover:bg-slate-800 hover:text-[#d4a853]"
          >
            Load User Lab Parameters
          </button>
          <button 
            onClick={runSimulation}
            disabled={simulating}
            className="flex items-center gap-2 rounded-lg bg-[#5ba4b5] px-4 py-2 text-xs font-semibold text-slate-900 transition hover:bg-[#4a91a2] disabled:opacity-50"
          >
            <RefreshCw className={`h-3 w-3 ${simulating ? 'animate-spin' : ''}`} />
            Run Simulation
          </button>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Sliders Control Panel */}
        <div className="glass-card p-6 space-y-6 h-fit">
          <h3 className="text-md font-bold text-slate-200 flex items-center gap-2">
            <Cpu className="h-4 w-4 text-[#5ba4b5]" /> Simulation Parameters
          </h3>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                <span>Initial Stock Price (S0)</span>
                <span className="font-mono text-slate-200">${S0}</span>
              </div>
              <input 
                type="range" min="10" max="500" step="5" value={S0} 
                onChange={(e) => setS0(Number(e.target.value))} 
                className="w-full accent-[#5ba4b5]"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                <span>Strike Price (K)</span>
                <span className="font-mono text-slate-200">${K}</span>
              </div>
              <input 
                type="range" min="10" max="500" step="5" value={K} 
                onChange={(e) => setK(Number(e.target.value))} 
                className="w-full accent-[#5ba4b5]"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                <span>Drift / Rate (mu / r)</span>
                <span className="font-mono text-slate-200">{(mu * 100).toFixed(2)}%</span>
              </div>
              <input 
                type="range" min="-0.2" max="0.5" step="0.005" value={mu} 
                onChange={(e) => setMu(Number(e.target.value))} 
                className="w-full accent-[#5ba4b5]"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                <span>Volatility (sigma)</span>
                <span className="font-mono text-slate-200">{(sigma * 100).toFixed(1)}%</span>
              </div>
              <input 
                type="range" min="0.01" max="1.5" step="0.01" value={sigma} 
                onChange={(e) => setSigma(Number(e.target.value))} 
                className="w-full accent-[#5ba4b5]"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                <span>Time to Maturity (T in Days)</span>
                <span className="font-mono text-slate-200">{Math.round(T * 365)} days</span>
              </div>
              <input 
                type="range" min="5" max="365" step="5" value={Math.round(T * 365)} 
                onChange={(e) => setT(Number(e.target.value) / 365.0)} 
                className="w-full accent-[#5ba4b5]"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                <span>Number of Steps (N)</span>
                <span className="font-mono text-slate-200">{N}</span>
              </div>
              <input 
                type="range" min="10" max="2000" step="50" value={N} 
                onChange={(e) => setN(Number(e.target.value))} 
                className="w-full accent-[#5ba4b5]"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                <span>Rendered Paths</span>
                <span className="font-mono text-slate-200">{numPaths}</span>
              </div>
              <input 
                type="range" min="5" max="100" step="5" value={numPaths} 
                onChange={(e) => setNumPaths(Number(e.target.value))} 
                className="w-full accent-[#5ba4b5]"
              />
            </div>
          </div>
        </div>

        {/* Path Charts & Distributions */}
        <div className="lg:col-span-2 space-y-8">
          {/* Paths Chart */}
          <div className="glass-card p-6 space-y-4">
            <h3 className="text-md font-bold text-slate-200">Simulated Price Trajectories</h3>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={paths}>
                  <XAxis dataKey="step" stroke="rgba(255,255,255,0.05)" tick={{ fill: '#64748b', fontSize: 10 }} />
                  <YAxis domain={['auto', 'auto']} stroke="rgba(255,255,255,0.05)" tick={{ fill: '#64748b', fontSize: 10 }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#161924', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px' }}
                    labelStyle={{ color: '#64748b', fontSize: 10 }}
                  />
                  {Array.from({ length: numPaths }).map((_, idx) => (
                    <Line 
                      key={idx} 
                      type="monotone" 
                      dataKey={`path_${idx}`} 
                      stroke={`hsla(${200 + (idx * 3) % 40}, 30%, 40%, 0.35)`} 
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
            <div className="glass-card p-6 space-y-4">
              <h3 className="text-md font-bold text-slate-200">Terminal Price Distribution</h3>
              <div className="h-48 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={histogramData}>
                    <XAxis dataKey="name" stroke="rgba(255,255,255,0.05)" tick={{ fill: '#64748b', fontSize: 9 }} />
                    <YAxis stroke="rgba(255,255,255,0.05)" tick={{ fill: '#64748b', fontSize: 9 }} />
                    <Tooltip contentStyle={{ backgroundColor: '#161924', border: 'none', borderRadius: '4px' }} />
                    <Bar dataKey="frequency" fill="#5ba4b5" opacity={0.7} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className="text-[10px] text-slate-400 text-center">Approaches log-normal distribution as paths count increases.</p>
            </div>

            {/* Pricing Model Comparison */}
            <div className="glass-card p-6 space-y-4 flex flex-col justify-between">
              <h3 className="text-md font-bold text-slate-200">Put Price Evaluation</h3>
              <div className="space-y-3 font-mono">
                <div className="flex justify-between items-center text-xs py-1 border-b border-slate-800">
                  <span className="text-slate-400">Black-Scholes (Analytical)</span>
                  <span className="font-semibold text-slate-200">${prices.bsPut.toFixed(4)}</span>
                </div>
                <div className="flex justify-between items-center text-xs py-1 border-b border-slate-800">
                  <span className="text-slate-400">Monte Carlo (Standard)</span>
                  <span className="font-semibold text-slate-200">
                    ${prices.mcPut.toFixed(4)} <span className="text-[10px] text-slate-500">± {prices.mcError.toFixed(4)}</span>
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs py-1 text-[#dc3545]">
                  <span>Legacy Lab Model</span>
                  <span className="font-semibold">${prices.legacyPut.toFixed(6)}</span>
                </div>
              </div>

              {/* Socratic callout */}
              <div className="rounded-lg bg-red-500/5 p-3 border border-red-500/10 text-xs">
                <div className="flex items-start gap-2">
                  <HelpCircle className="h-4 w-4 text-[#dc3545] flex-shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <p className="font-semibold text-slate-200">Socratic Query:</p>
                    <p className="text-slate-400 leading-relaxed">
                      Notice the massive discrepancy? The Legacy Lab puts the price at <span className="font-mono text-red-400">${prices.legacyPut.toFixed(6)}</span> while Black-Scholes shows <span className="font-mono text-[#7ec8a0]">${prices.bsPut.toFixed(4)}</span>.
                    </p>
                    <Link href="/learn" className="text-xs text-[#5ba4b5] hover:underline font-semibold block mt-1">
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
