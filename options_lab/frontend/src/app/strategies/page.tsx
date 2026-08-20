'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  AreaChart,
  Area,
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { optionsApi } from '@/lib/api';
import { Layers, Plus, Trash2, ShieldAlert, Award, TrendingUp } from 'lucide-react';
import ProtectedRoute from '@/components/ProtectedRoute';

interface Leg {
  id: string;
  asset_type: 'stock' | 'option';
  option_type: 'call' | 'put' | null;
  position: 'long' | 'short';
  strike: number;
  expiry: number;
  entry_price: number;
  quantity: number;
}

export default function StrategiesPage() {
  const [underlyingSpot, setUnderlyingSpot] = useState<number>(100);
  const [legs, setLegs] = useState<Leg[]>([]);
  const [r, setR] = useState<number>(0.05);
  const [sigma, setSigma] = useState<number>(0.20);
  
  const [payoffGrid, setPayoffGrid] = useState<any[]>([]);
  const [riskMetrics, setRiskMetrics] = useState({
    max_profit: '0',
    max_loss: '0',
    breakevens: [] as number[],
    net_premium: 0,
    margin_required: 0,
    has_naked_short: false
  });

  const applyPreset = (presetName: string) => {
    let presetLegs: Leg[] = [];
    if (presetName === 'covered_call') {
      presetLegs = [
        {
          id: '1',
          asset_type: 'stock',
          option_type: null,
          position: 'long',
          strike: 0,
          expiry: 0.5,
          entry_price: underlyingSpot,
          quantity: 1
        },
        {
          id: '2',
          asset_type: 'option',
          option_type: 'call',
          position: 'short',
          strike: Math.round(underlyingSpot * 1.05),
          expiry: 0.5,
          entry_price: 3.50,
          quantity: 1
        }
      ];
    } else if (presetName === 'secured_put') {
      presetLegs = [
        {
          id: '1',
          asset_type: 'option',
          option_type: 'put',
          position: 'short',
          strike: Math.round(underlyingSpot * 0.95),
          expiry: 0.5,
          entry_price: 2.80,
          quantity: 1
        }
      ];
    } else if (presetName === 'naked_call') {
      presetLegs = [
        {
          id: '1',
          asset_type: 'option',
          option_type: 'call',
          position: 'short',
          strike: Math.round(underlyingSpot * 1.05),
          expiry: 0.5,
          entry_price: 2.20,
          quantity: 1
        }
      ];
    } else if (presetName === 'straddle') {
      presetLegs = [
        {
          id: '1',
          asset_type: 'option',
          option_type: 'call',
          position: 'long',
          strike: underlyingSpot,
          expiry: 0.5,
          entry_price: 5.20,
          quantity: 1
        },
        {
          id: '2',
          asset_type: 'option',
          option_type: 'put',
          position: 'long',
          strike: underlyingSpot,
          expiry: 0.5,
          entry_price: 4.80,
          quantity: 1
        }
      ];
    }
    setLegs(presetLegs);
  };

  const addLeg = () => {
    const newLeg: Leg = {
      id: Date.now().toString(),
      asset_type: 'option',
      option_type: 'call',
      position: 'long',
      strike: underlyingSpot,
      expiry: 0.5,
      entry_price: 3.0,
      quantity: 1
    };
    setLegs([...legs, newLeg]);
  };

  const removeLeg = (id: string) => {
    setLegs(legs.filter(l => l.id !== id));
  };

  const updateLeg = (id: string, field: keyof Leg, value: any) => {
    setLegs(legs.map(l => {
      if (l.id === id) {
        const updated = { ...l, [field]: value };
        if (field === 'asset_type' && value === 'stock') {
          updated.option_type = null;
          updated.strike = 0;
          updated.entry_price = underlyingSpot;
        } else if (field === 'asset_type' && value === 'option') {
          updated.option_type = 'call';
          updated.strike = underlyingSpot;
          updated.entry_price = 3.0;
        }
        return updated;
      }
      return l;
    }));
  };

  const calculatePayoff = async () => {
    if (legs.length === 0) {
      setPayoffGrid([]);
      return;
    }
    try {
      const payload = {
        legs: legs.map(l => ({
          asset_type: l.asset_type,
          option_type: l.option_type,
          position: l.position,
          strike: l.strike || null,
          expiry: l.expiry || null,
          entry_price: l.entry_price,
          quantity: l.quantity
        })),
        underlying_spot: underlyingSpot,
        r,
        sigma
      };
      const res = await optionsApi.simulateStrategy(payload);
      setPayoffGrid(res.payoff_grid);
      setRiskMetrics({
        max_profit: typeof res.max_profit === 'string' ? res.max_profit : `$${res.max_profit.toFixed(2)}`,
        max_loss: typeof res.max_loss === 'string' ? res.max_loss : `$${res.max_loss.toFixed(2)}`,
        breakevens: res.breakevens,
        net_premium: res.net_premium,
        margin_required: res.margin_required,
        has_naked_short: res.has_naked_short
      });
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (legs.length === 0) {
      applyPreset('covered_call');
    }
  }, []);

  useEffect(() => {
    calculatePayoff();
  }, [legs, underlyingSpot, r, sigma]);

  return (
    <ProtectedRoute>
      <div className="space-y-6 pb-12">
        {/* Banner Header - Velzon Light Theme */}
        <div className="relative overflow-hidden rounded-xl bg-white p-6 sm:p-8 border border-slate-200/80 shadow-sm">
          <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-indigo-50/60 blur-2xl" />
          <div className="relative z-10 max-w-3xl space-y-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-[#4051B5] border border-indigo-100">
              <Layers className="h-3.5 w-3.5" /> Strategy Builder & Payoff Engine
            </span>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight sm:text-3xl">
              Options Strategy <span className="text-[#4051B5]">Playground</span>
            </h1>
            <p className="text-slate-500 text-xs sm:text-sm leading-relaxed">
              Assemble multi-leg derivative positions, evaluate risk profile metrics, margin collateral requirements, and visualize time-decay P&L curves across underlying price movements.
            </p>
          </div>
        </div>

        {/* Preset Selection Buttons */}
        <div className="flex flex-wrap gap-3">
          <button onClick={() => applyPreset('covered_call')} className="rounded-xl bg-white border border-slate-200 px-4 py-2.5 text-xs font-bold text-slate-700 hover:border-[#4051B5] hover:text-[#4051B5] shadow-sm transition">
            Covered Call
          </button>
          <button onClick={() => applyPreset('secured_put')} className="rounded-xl bg-white border border-slate-200 px-4 py-2.5 text-xs font-bold text-slate-700 hover:border-emerald-500 hover:text-emerald-600 shadow-sm transition">
            Cash-Secured Put (Wheel)
          </button>
          <button onClick={() => applyPreset('naked_call')} className="rounded-xl bg-white border border-slate-200 px-4 py-2.5 text-xs font-bold text-slate-700 hover:border-rose-500 hover:text-rose-600 shadow-sm transition">
            Naked Call (High Risk)
          </button>
          <button onClick={() => applyPreset('straddle')} className="rounded-xl bg-white border border-slate-200 px-4 py-2.5 text-xs font-bold text-slate-700 hover:border-amber-500 hover:text-amber-600 shadow-sm transition">
            Long Straddle
          </button>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Legs Editor Panel */}
          <div className="lg:col-span-2 space-y-6">
            <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-4">
              <div className="flex justify-between items-center border-b border-slate-100 pb-3">
                <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                  <Layers className="h-4 w-4 text-[#4051B5]" /> Position Legs Configuration
                </h3>
                <button 
                  onClick={addLeg}
                  className="flex items-center gap-1 text-xs text-[#4051B5] hover:underline font-bold"
                >
                  <Plus className="h-3.5 w-3.5" /> Add Leg
                </button>
              </div>

              <div className="space-y-4">
                {legs.map((leg) => (
                  <div key={leg.id} className="grid grid-cols-2 md:grid-cols-7 gap-3 items-center border-b border-slate-100 pb-4">
                    <div>
                      <label className="text-[10px] text-slate-400 font-bold block mb-1">Asset</label>
                      <select 
                        value={leg.asset_type}
                        onChange={(e) => updateLeg(leg.id, 'asset_type', e.target.value)}
                        className="bg-slate-50 border border-slate-200 rounded-lg p-1.5 w-full text-xs text-slate-800 font-medium"
                      >
                        <option value="stock">Stock</option>
                        <option value="option">Option</option>
                      </select>
                    </div>

                    {leg.asset_type === 'option' ? (
                      <>
                        <div>
                          <label className="text-[10px] text-slate-400 font-bold block mb-1">Type</label>
                          <select 
                            value={leg.option_type || 'call'}
                            onChange={(e) => updateLeg(leg.id, 'option_type', e.target.value)}
                            className="bg-slate-50 border border-slate-200 rounded-lg p-1.5 w-full text-xs text-slate-800 font-medium"
                          >
                            <option value="call">Call</option>
                            <option value="put">Put</option>
                          </select>
                        </div>
                        <div>
                          <label className="text-[10px] text-slate-400 font-bold block mb-1">Strike</label>
                          <input 
                            type="number" value={leg.strike}
                            onChange={(e) => updateLeg(leg.id, 'strike', Number(e.target.value))}
                            className="bg-slate-50 border border-slate-200 rounded-lg p-1.5 w-full text-xs font-mono font-bold text-slate-800"
                          />
                        </div>
                      </>
                    ) : (
                      <div className="col-span-2 text-xs text-slate-400 font-medium mt-3 text-center">
                        Underlying Shares
                      </div>
                    )}

                    <div>
                      <label className="text-[10px] text-slate-400 font-bold block mb-1">Position</label>
                      <select 
                        value={leg.position}
                        onChange={(e) => updateLeg(leg.id, 'position', e.target.value)}
                        className="bg-slate-50 border border-slate-200 rounded-lg p-1.5 w-full text-xs text-slate-800 font-medium"
                      >
                        <option value="long">Buy (Long)</option>
                        <option value="short">Sell (Short)</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[10px] text-slate-400 font-bold block mb-1">Price</label>
                      <input 
                        type="number" value={leg.entry_price} step="0.1"
                        onChange={(e) => updateLeg(leg.id, 'entry_price', Number(e.target.value))}
                        className="bg-slate-50 border border-slate-200 rounded-lg p-1.5 w-full text-xs font-mono font-bold text-slate-800"
                      />
                    </div>

                    <div>
                      <label className="text-[10px] text-slate-400 font-bold block mb-1">Contracts</label>
                      <input 
                        type="number" value={leg.quantity} min="1"
                        onChange={(e) => updateLeg(leg.id, 'quantity', Number(e.target.value))}
                        className="bg-slate-50 border border-slate-200 rounded-lg p-1.5 w-full text-xs font-mono font-bold text-slate-800"
                      />
                    </div>

                    <div className="flex justify-end pt-4 md:pt-0">
                      <button 
                        onClick={() => removeLeg(leg.id)}
                        className="p-1.5 text-slate-400 hover:text-rose-600 transition"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Payoff Chart */}
            <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-base font-bold text-slate-800">Visual Payoff Diagram at Expiration</h3>
                <div className="flex items-center gap-4 text-xs font-semibold">
                  <span className="flex items-center gap-1.5 text-[#4051B5]">
                    <span className="w-3 h-0.5 bg-[#4051B5] rounded"></span> Expiration P&L
                  </span>
                  <span className="flex items-center gap-1.5 text-[#0AB39C]">
                    <span className="w-3 h-0.5 border-t-2 border-dashed border-[#0AB39C]"></span> Midway (Time-decay)
                  </span>
                </div>
              </div>
              <div className="h-72 w-full pt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={payoffGrid}>
                    <defs>
                      <linearGradient id="profitGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4051B5" stopOpacity={0.25}/>
                        <stop offset="95%" stopColor="#4051B5" stopOpacity={0.0}/>
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="spot" stroke="#475569" fontSize={11} tickFormatter={(val) => `$${val}`} />
                    <YAxis stroke="#475569" fontSize={11} tickFormatter={(val) => `$${Number(val).toFixed(0)}`} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '12px', color: '#1e293b', fontWeight: 'bold' }}
                      formatter={(val: any, name: string) => [
                        `$${Number(val).toFixed(2)}`,
                        name === 'expiry_pl' ? 'Expiration P&L' : 'Midway P&L'
                      ]}
                      labelFormatter={(val) => `Spot Price: $${val}`}
                    />
                    <ReferenceLine y={0} stroke="#64748b" strokeDasharray="3 3" />
                    <ReferenceLine x={underlyingSpot} stroke="#4051B5" strokeDasharray="3 3" label={{ value: 'Current Spot', fill: '#4051B5', fontSize: 10, fontWeight: 'bold' }} />
                    <Area type="monotone" dataKey="expiry_pl" name="expiry_pl" stroke="#4051B5" strokeWidth={2.5} fill="url(#profitGrad)" />
                    <Area type="monotone" dataKey="midway_pl" name="midway_pl" stroke="#0AB39C" strokeWidth={1.5} strokeDasharray="4 4" fill="none" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Right Metrics Panel */}
          <div className="space-y-6">
            <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-5">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Strategy Environment</h3>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-slate-600 font-bold block mb-1">Underlying Spot Price ($)</label>
                  <input 
                    type="number" value={underlyingSpot}
                    onChange={(e) => setUnderlyingSpot(Number(e.target.value))}
                    className="bg-slate-50 border border-slate-200 rounded-lg p-2 w-full text-xs font-mono font-bold text-slate-800"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-600 font-bold block mb-1">Implied Volatility (IV %)</label>
                  <input 
                    type="number" value={sigma * 100} step="1"
                    onChange={(e) => setSigma(Number(e.target.value) / 100)}
                    className="bg-slate-50 border border-slate-200 rounded-lg p-2 w-full text-xs font-mono font-bold text-slate-800"
                  />
                </div>
              </div>

              <hr className="border-slate-100" />

              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Risk Profile Metrics</h3>
              
              {riskMetrics.has_naked_short && (
                <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-bold">
                  <ShieldAlert className="h-4 w-4 shrink-0 text-rose-600" />
                  <span>Warning: Position contains uncovered naked short options!</span>
                </div>
              )}

              <div className="space-y-3">
                <div className="flex justify-between items-center p-3 rounded-lg bg-emerald-50/50 border border-emerald-100">
                  <span className="text-xs text-slate-600 font-bold">Max Profit</span>
                  <span className="text-xs font-mono font-extrabold text-emerald-600">{riskMetrics.max_profit}</span>
                </div>
                <div className="flex justify-between items-center p-3 rounded-lg bg-rose-50/50 border border-rose-100">
                  <span className="text-xs text-slate-600 font-bold">Max Loss</span>
                  <span className="text-xs font-mono font-extrabold text-rose-600">{riskMetrics.max_loss}</span>
                </div>
                <div className="flex justify-between items-center p-3 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-xs text-slate-600 font-bold">Net Premium</span>
                  <span className="text-xs font-mono font-bold text-slate-800">
                    {riskMetrics.net_premium >= 0 ? `+$${riskMetrics.net_premium.toFixed(2)} (Credit)` : `-$${Math.abs(riskMetrics.net_premium).toFixed(2)} (Debit)`}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-xs text-slate-600 font-bold">Margin Required</span>
                  <span className="text-xs font-mono font-bold text-[#4051B5]">${riskMetrics.margin_required.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
