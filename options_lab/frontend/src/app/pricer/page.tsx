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
      <div className="space-y-6 pb-12">
        {/* Banner Header - Velzon Light Theme */}
        <div className="relative overflow-hidden rounded-xl bg-white p-6 sm:p-8 border border-slate-200/80 shadow-sm">
          <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-indigo-50/60 blur-2xl" />
          <div className="relative z-10 max-w-3xl space-y-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-[#4051B5] border border-indigo-100">
              <Percent className="h-3.5 w-3.5" /> Analytical Valuation Engine
            </span>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight sm:text-3xl">
              Black-Scholes Options <span className="text-[#4051B5]">Pricer & Greeks</span>
            </h1>
            <p className="text-slate-500 text-xs sm:text-sm leading-relaxed">
              Calculate analytical option prices and compute first/second order sensitivity Greeks (Delta, Gamma, Theta, Vega, Rho) dynamically across underlying volatility surfaces.
            </p>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Param Control Panel */}
          <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-6 h-fit">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                <Percent className="h-4 w-4 text-[#4051B5]" /> Option Parameters
              </h3>
              {/* Call/Put Selector */}
              <div className="flex rounded-lg bg-slate-100 p-1 border border-slate-200">
                <button 
                  onClick={() => setOptionType('call')}
                  className={`px-3 py-1 rounded-md text-xs font-bold uppercase transition ${
                    optionType === 'call' ? 'bg-[#4051B5] text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Call
                </button>
                <button 
                  onClick={() => setOptionType('put')}
                  className={`px-3 py-1 rounded-md text-xs font-bold uppercase transition ${
                    optionType === 'put' ? 'bg-[#4051B5] text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Put
                </button>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-600 mb-1">
                  <span>Underlying Asset Price (S)</span>
                  <span className="font-mono text-[#4051B5] font-bold">${S}</span>
                </div>
                <input 
                  type="range" min="10" max="300" step="1" value={S} 
                  onChange={(e) => setS(Number(e.target.value))} 
                  className="w-full h-2 bg-slate-100 rounded-lg accent-[#4051B5] cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-600 mb-1">
                  <span>Strike Price (K)</span>
                  <span className="font-mono text-slate-800 font-bold">${K}</span>
                </div>
                <input 
                  type="range" min="10" max="300" step="1" value={K} 
                  onChange={(e) => setK(Number(e.target.value))} 
                  className="w-full h-2 bg-slate-100 rounded-lg accent-[#4051B5] cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-600 mb-1">
                  <span>Time to Maturity (T in Years)</span>
                  <span className="font-mono text-slate-800 font-bold">{T}y ({Math.round(T * 365)}d)</span>
                </div>
                <input 
                  type="range" min="0.05" max="2" step="0.05" value={T} 
                  onChange={(e) => setT(Number(e.target.value))} 
                  className="w-full h-2 bg-slate-100 rounded-lg accent-[#4051B5] cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-600 mb-1">
                  <span>Risk-Free Rate (r)</span>
                  <span className="font-mono text-slate-800 font-bold">{(r * 100).toFixed(1)}%</span>
                </div>
                <input 
                  type="range" min="0" max="0.2" step="0.005" value={r} 
                  onChange={(e) => setR(Number(e.target.value))} 
                  className="w-full h-2 bg-slate-100 rounded-lg accent-[#4051B5] cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-600 mb-1">
                  <span>Implied Volatility (sigma)</span>
                  <span className="font-mono text-slate-800 font-bold">{(sigma * 100).toFixed(1)}%</span>
                </div>
                <input 
                  type="range" min="0.05" max="1.5" step="0.01" value={sigma} 
                  onChange={(e) => setSigma(Number(e.target.value))} 
                  className="w-full h-2 bg-slate-100 rounded-lg accent-[#4051B5] cursor-pointer"
                />
              </div>
            </div>
          </div>

          {/* Pricing Results & Greeks */}
          <div className="lg:col-span-2 space-y-6">
            {/* Main Price Card */}
            <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm flex flex-col sm:flex-row justify-between items-center">
              <div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Computed Fair Value</span>
                <h2 className="text-4xl font-extrabold font-mono text-[#0AB39C] mt-1">
                  ${price.toFixed(4)}
                </h2>
                <p className="text-xs text-slate-400 mt-1">Theoretical Black-Scholes analytical valuation</p>
              </div>
              
              <div className="w-full sm:w-auto mt-4 sm:mt-0 flex gap-3 overflow-x-auto py-2">
                <div className="text-center px-3.5 py-2 rounded-lg bg-indigo-50/50 border border-indigo-100">
                  <span className="text-[10px] text-slate-500 font-bold block">Delta</span>
                  <span className="font-mono text-xs text-[#4051B5] font-extrabold">{greeks.delta.toFixed(3)}</span>
                </div>
                <div className="text-center px-3.5 py-2 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[10px] text-slate-500 font-bold block">Gamma</span>
                  <span className="font-mono text-xs text-slate-800 font-extrabold">{greeks.gamma.toFixed(4)}</span>
                </div>
                <div className="text-center px-3.5 py-2 rounded-lg bg-rose-50/50 border border-rose-100">
                  <span className="text-[10px] text-slate-500 font-bold block">Theta</span>
                  <span className="font-mono text-xs text-rose-600 font-extrabold">{greeks.theta.toFixed(3)}</span>
                </div>
                <div className="text-center px-3.5 py-2 rounded-lg bg-amber-50/50 border border-amber-100">
                  <span className="text-[10px] text-slate-500 font-bold block">Vega</span>
                  <span className="font-mono text-xs text-amber-700 font-extrabold">{greeks.vega.toFixed(3)}</span>
                </div>
              </div>
            </div>

            {/* Greeks Surface Grid */}
            <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-base font-bold text-slate-800">Greeks Price Sensitivity Matrix</h3>
                <span className="text-xs text-slate-400 font-medium">Values change by underlying spot price (T = remaining days)</span>
              </div>
              
              <div className="overflow-x-auto max-h-72 border border-slate-200 rounded-lg">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-50 text-slate-600 font-bold uppercase border-b border-slate-200 sticky top-0">
                    <tr>
                      <th className="p-3">Spot Price</th>
                      <th className="p-3">Days Left</th>
                      <th className="p-3">Delta</th>
                      <th className="p-3">Gamma</th>
                      <th className="p-3">Theta</th>
                      <th className="p-3">Vega</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {surface.filter((_, idx) => idx % 6 === 0).map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="p-3 text-slate-800 font-bold">${row.spot}</td>
                        <td className="p-3 text-slate-500">{row.days_to_expiry}d</td>
                        <td className="p-3 text-[#0AB39C] font-semibold">{row.delta.toFixed(3)}</td>
                        <td className="p-3 text-slate-700">{row.gamma.toFixed(4)}</td>
                        <td className="p-3 text-rose-600 font-semibold">{row.theta.toFixed(3)}</td>
                        <td className="p-3 text-amber-700 font-semibold">{row.vega.toFixed(3)}</td>
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
