'use client';

import React, { useState, useEffect } from 'react';
import { optionsApi } from '@/lib/api';
import { Percent, Activity, HelpCircle, TrendingUp } from 'lucide-react';
import ProtectedRoute from '@/components/ProtectedRoute';

export default function PricerPage() {
  const [S, setS] = useState<number>(100);
  const [K, setK] = useState<number>(100);
  const [T, setT] = useState<number>(0.5);
  const [r, setR] = useState<number>(0.05);
  const [sigma, setSigma] = useState<number>(0.20);
  const [optionType, setOptionType] = useState<string>('call');

  const [price, setPrice] = useState<number>(0);
  const [greeks, setGreeks] = useState({
    delta: 0,
    gamma: 0,
    theta: 0,
    vega: 0,
    rho: 0
  });

  const [surface, setSurface] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const calculatePricer = async () => {
    setLoading(true);
    try {
      const data = await optionsApi.priceAnalytical({
        S, K, T, r, sigma, option_type: optionType
      });
      setPrice(data.price);
      setGreeks(data.greeks);

      const surfaceRes = await optionsApi.getGreeksSurface({
        S, K, T, r, sigma, option_type: optionType
      });
      setSurface(surfaceRes.surface);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    calculatePricer();
  }, [S, K, T, r, sigma, optionType]);

  return (
    <ProtectedRoute>
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-100 font-sans">Black-Scholes Options Pricer & Greeks</h1>
        <p className="text-slate-400 text-sm">Calculate options price and analyze risk parameters (Greeks) dynamically.</p>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Param Control Panel */}
        <div className="glass-card p-6 space-y-6 h-fit">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-md font-bold text-slate-200 flex items-center gap-2">
              <Percent className="h-4 w-4 text-[#5ba4b5]" /> Pricing Metrics
            </h3>
            {/* Call/Put selector */}
            <div className="flex rounded-lg bg-[#12141c]/80 p-0.5 border border-slate-800">
              <button 
                onClick={() => setOptionType('call')}
                className={`px-3 py-1 rounded-md text-xs font-semibold uppercase tracking-wider transition ${
                  optionType === 'call' ? 'bg-[#5ba4b5] text-slate-900' : 'text-slate-400'
                }`}
              >
                Call
              </button>
              <button 
                onClick={() => setOptionType('put')}
                className={`px-3 py-1 rounded-md text-xs font-semibold uppercase tracking-wider transition ${
                  optionType === 'put' ? 'bg-[#5ba4b5] text-slate-900' : 'text-slate-400'
                }`}
              >
                Put
              </button>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                <span>Underlying Asset Price (S)</span>
                <span className="font-mono text-slate-200">${S}</span>
              </div>
              <input 
                type="range" min="10" max="300" step="1" value={S} 
                onChange={(e) => setS(Number(e.target.value))} 
                className="w-full accent-[#5ba4b5]"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                <span>Strike Price (K)</span>
                <span className="font-mono text-slate-200">${K}</span>
              </div>
              <input 
                type="range" min="10" max="300" step="1" value={K} 
                onChange={(e) => setK(Number(e.target.value))} 
                className="w-full accent-[#5ba4b5]"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                <span>Time to Maturity (T in Years)</span>
                <span className="font-mono text-slate-200">{T}y ({Math.round(T * 365)}d)</span>
              </div>
              <input 
                type="range" min="0.05" max="2" step="0.05" value={T} 
                onChange={(e) => setT(Number(e.target.value))} 
                className="w-full accent-[#5ba4b5]"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                <span>Risk-Free Rate (r)</span>
                <span className="font-mono text-slate-200">{(r * 100).toFixed(1)}%</span>
              </div>
              <input 
                type="range" min="0" max="0.2" step="0.005" value={r} 
                onChange={(e) => setR(Number(e.target.value))} 
                className="w-full accent-[#5ba4b5]"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                <span>Implied Volatility (sigma)</span>
                <span className="font-mono text-slate-200">{(sigma * 100).toFixed(1)}%</span>
              </div>
              <input 
                type="range" min="0.05" max="1.5" step="0.01" value={sigma} 
                onChange={(e) => setSigma(Number(e.target.value))} 
                className="w-full accent-[#5ba4b5]"
              />
            </div>
          </div>
        </div>

        {/* Pricing results & Greeks */}
        <div className="lg:col-span-2 space-y-8">
          {/* Main Price Card */}
          <div className="glass-card p-6 flex flex-col sm:flex-row justify-between items-center bg-gradient-to-br from-[#1b2230] to-[#12141a]">
            <div>
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Computed Fair Value</span>
              <h2 className="text-4xl font-extrabold font-mono text-[#7ec8a0] mt-1">
                ${price.toFixed(4)}
              </h2>
              <p className="text-[10px] text-slate-400 mt-1">Theoretical BS pricing valuation</p>
            </div>
            
            <div className="w-full sm:w-auto mt-4 sm:mt-0 flex gap-4 overflow-x-auto py-2">
              <div className="text-center px-4 py-2 border-r border-slate-800">
                <span className="text-[10px] text-slate-500 font-bold block">Delta</span>
                <span className="font-mono text-sm text-slate-200 font-bold">{greeks.delta.toFixed(3)}</span>
              </div>
              <div className="text-center px-4 py-2 border-r border-slate-800">
                <span className="text-[10px] text-slate-500 font-bold block">Gamma</span>
                <span className="font-mono text-sm text-slate-200 font-bold">{greeks.gamma.toFixed(4)}</span>
              </div>
              <div className="text-center px-4 py-2 border-r border-slate-800">
                <span className="text-[10px] text-slate-500 font-bold block">Theta</span>
                <span className="font-mono text-sm text-slate-200 font-bold">{greeks.theta.toFixed(3)}</span>
              </div>
              <div className="text-center px-4 py-2">
                <span className="text-[10px] text-slate-500 font-bold block">Vega</span>
                <span className="font-mono text-sm text-slate-200 font-bold">{greeks.vega.toFixed(3)}</span>
              </div>
            </div>
          </div>

          {/* Greeks Surface Grid */}
          <div className="glass-card p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-md font-bold text-slate-200">Greeks Price Sensitivity Matrix</h3>
              <span className="text-[10px] text-slate-400">Values change by underlying spot price (T = remaining days)</span>
            </div>
            
            <div className="overflow-x-auto max-h-64 border border-slate-800 rounded-lg">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[#12141a]/90 text-slate-400 sticky top-0">
                  <tr>
                    <th className="p-3">Spot Price</th>
                    <th className="p-3">Days Left</th>
                    <th className="p-3">Delta</th>
                    <th className="p-3">Gamma</th>
                    <th className="p-3">Theta</th>
                    <th className="p-3">Vega</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50 bg-[#161924]/30">
                  {surface.filter((_, idx) => idx % 6 === 0).map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/30">
                      <td className="p-3 text-slate-200">${row.spot}</td>
                      <td className="p-3 text-slate-400">{row.days_to_expiry}d</td>
                      <td className="p-3 text-[#7ec8a0]">{row.delta.toFixed(3)}</td>
                      <td className="p-3 text-slate-300">{row.gamma.toFixed(4)}</td>
                      <td className="p-3 text-[#dc3545]">{row.theta.toFixed(3)}</td>
                      <td className="p-3 text-[#d4a853]">{row.vega.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
    </ProtectedRoute>
  );
}
