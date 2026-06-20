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

  // Built-in presets
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
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">Options Strategy Playground</h1>
        <p className="text-slate-400 text-sm">Assemble multi-leg derivative positions and evaluate their visual time-decay P&L.</p>
      </div>

      {/* Preset bar */}
      <div className="flex flex-wrap gap-3">
        <button onClick={() => applyPreset('covered_call')} className="rounded-lg bg-slate-900 border border-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:border-[#7ec8a0] hover:text-[#7ec8a0] transition">
          Covered Call
        </button>
        <button onClick={() => applyPreset('secured_put')} className="rounded-lg bg-slate-900 border border-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:border-[#5ba4b5] hover:text-[#5ba4b5] transition">
          Cash-Secured Put
        </button>
        <button onClick={() => applyPreset('naked_call')} className="rounded-lg bg-slate-900 border border-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:border-[#dc3545] hover:text-[#dc3545] transition">
          Naked Call (High Risk)
        </button>
        <button onClick={() => applyPreset('straddle')} className="rounded-lg bg-slate-900 border border-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 hover:border-[#d4a853] hover:text-[#d4a853] transition">
          Long Straddle
        </button>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Legs editor */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-card p-6 space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="text-md font-bold text-slate-200 flex items-center gap-2">
                <Layers className="h-4 w-4 text-[#5ba4b5]" /> Position Legs
              </h3>
              <button 
                onClick={addLeg}
                className="flex items-center gap-1 text-xs text-[#5ba4b5] hover:underline font-semibold"
              >
                <Plus className="h-3 w-3" /> Add Leg
              </button>
            </div>

            <div className="space-y-4">
              {legs.map((leg, index) => (
                <div key={leg.id} className="grid grid-cols-2 md:grid-cols-7 gap-3 items-center border-b border-slate-800/40 pb-4">
                  <div>
                    <label className="text-[10px] text-slate-500 font-bold block mb-1">Asset</label>
                    <select 
                      value={leg.asset_type}
                      onChange={(e) => updateLeg(leg.id, 'asset_type', e.target.value)}
                      className="rounded p-1.5 w-full text-xs"
                    >
                      <option value="stock">Stock</option>
                      <option value="option">Option</option>
                    </select>
                  </div>

                  {leg.asset_type === 'option' ? (
                    <>
                      <div>
                        <label className="text-[10px] text-slate-500 font-bold block mb-1">Type</label>
                        <select 
                          value={leg.option_type || 'call'}
                          onChange={(e) => updateLeg(leg.id, 'option_type', e.target.value)}
                          className="rounded p-1.5 w-full text-xs"
                        >
                          <option value="call">Call</option>
                          <option value="put">Put</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-500 font-bold block mb-1">Strike</label>
                        <input 
                          type="number" value={leg.strike}
                          onChange={(e) => updateLeg(leg.id, 'strike', Number(e.target.value))}
                          className="rounded p-1.5 w-full text-xs font-mono"
                        />
                      </div>
                    </>
                  ) : (
                    <div className="col-span-2 text-xs text-slate-500 italic mt-3 text-center">
                      Underlying Shares
                    </div>
                  )}

                  <div>
                    <label className="text-[10px] text-slate-500 font-bold block mb-1">Position</label>
                    <select 
                      value={leg.position}
                      onChange={(e) => updateLeg(leg.id, 'position', e.target.value)}
                      className="rounded p-1.5 w-full text-xs"
                    >
                      <option value="long">Buy (Long)</option>
                      <option value="short">Sell (Short)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[10px] text-slate-500 font-bold block mb-1">Price/Premium</label>
                    <input 
                      type="number" step="0.1" value={leg.entry_price}
                      onChange={(e) => updateLeg(leg.id, 'entry_price', Number(e.target.value))}
                      className="rounded p-1.5 w-full text-xs font-mono"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] text-slate-500 font-bold block mb-1">Quantity</label>
                    <input 
                      type="number" min="1" value={leg.quantity}
                      onChange={(e) => updateLeg(leg.id, 'quantity', Number(e.target.value))}
                      className="rounded p-1.5 w-full text-xs font-mono"
                    />
                  </div>

                  <div className="flex justify-center mt-3">
                    <button 
                      onClick={() => removeLeg(leg.id)}
                      className="text-red-500 hover:text-red-400 p-1.5"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Payoff chart */}
          <div className="glass-card p-6 space-y-4">
            <h3 className="text-md font-bold text-slate-200">Profit & Loss Trajectory</h3>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={payoffGrid}>
                  <defs>
                    <linearGradient id="profitGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#7ec8a0" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#7ec8a0" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="lossGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#dc3545" stopOpacity={0}/>
                      <stop offset="95%" stopColor="#dc3545" stopOpacity={0.2}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="spot" stroke="rgba(255,255,255,0.05)" tick={{ fill: '#64748b', fontSize: 10 }} />
                  <YAxis stroke="rgba(255,255,255,0.05)" tick={{ fill: '#64748b', fontSize: 10 }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#161924', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px' }}
                    labelStyle={{ color: '#64748b', fontSize: 10 }}
                  />
                  <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" strokeWidth={1.5} />
                  <ReferenceLine x={underlyingSpot} stroke="rgba(255,255,255,0.1)" strokeDasharray="3 3" />
                  
                  {/* Primary Area showing expiry P&L */}
                  <Area 
                    type="monotone" 
                    dataKey="expiry_pl" 
                    stroke="#7ec8a0" 
                    strokeWidth={2.5} 
                    fill="url(#profitGrad)" 
                    dot={false} 
                  />
                  {/* Secondary Line showing early decay payoff */}
                  <Area 
                    type="monotone" 
                    dataKey="midway_pl" 
                    stroke="#5ba4b5" 
                    strokeWidth={1.5} 
                    strokeDasharray="4 4"
                    fill="none" 
                    dot={false} 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="flex justify-center gap-6 text-[10px] text-slate-400">
              <div className="flex items-center gap-1.5">
                <div className="h-0.5 w-6 bg-[#7ec8a0]" /> Expiry Payoff
              </div>
              <div className="flex items-center gap-1.5">
                <div className="h-0.5 w-6 bg-[#5ba4b5] border-dashed border-t" /> Midway (Time-decay)
              </div>
            </div>
          </div>
        </div>

        {/* Risk summary & inputs */}
        <div className="space-y-6">
          <div className="glass-card p-6 space-y-6 h-fit">
            <h3 className="text-md font-bold text-slate-200">Risk Profile</h3>

            <div className="space-y-3 text-xs font-mono">
              <div className="flex justify-between items-center py-2 border-b border-slate-800">
                <span className="text-slate-400">Net Flow</span>
                <span className={`font-semibold ${riskMetrics.net_premium >= 0 ? 'text-[#7ec8a0]' : 'text-slate-200'}`}>
                  {riskMetrics.net_premium >= 0 
                    ? `+$${riskMetrics.net_premium.toFixed(2)} (Credit)` 
                    : `-$${Math.abs(riskMetrics.net_premium).toFixed(2)} (Debit)`
                  }
                </span>
              </div>

              <div className="flex justify-between items-center py-2 border-b border-slate-800">
                <span className="text-slate-400">Max Profit</span>
                <span className="font-semibold text-[#7ec8a0]">{riskMetrics.max_profit}</span>
              </div>

              <div className="flex justify-between items-center py-2 border-b border-slate-800">
                <span className="text-slate-400">Max Loss</span>
                <span className={`font-semibold ${riskMetrics.max_loss.includes('Unlimited') ? 'text-[#dc3545]' : 'text-slate-200'}`}>
                  {riskMetrics.max_loss}
                </span>
              </div>

              <div className="flex justify-between items-center py-2 border-b border-slate-800">
                <span className="text-slate-400">Break-Even Points</span>
                <span className="font-semibold text-[#d4a853]">
                  {riskMetrics.breakevens.length > 0 
                    ? riskMetrics.breakevens.map(b => `$${b}`).join(', ') 
                    : 'None'
                  }
                </span>
              </div>

              {riskMetrics.margin_required > 0 && (
                <div className="flex justify-between items-center py-2 text-[#d4a853]">
                  <span>Est. Margin Required</span>
                  <span className="font-semibold">${riskMetrics.margin_required.toFixed(2)}</span>
                </div>
              )}
            </div>

            {/* General parameters */}
            <div className="border-t border-slate-800 pt-4 space-y-4">
              <div>
                <label className="text-[10px] text-slate-500 font-bold block mb-1">Underlying Spot Price</label>
                <input 
                  type="number" value={underlyingSpot}
                  onChange={(e) => setUnderlyingSpot(Number(e.target.value))}
                  className="rounded p-1.5 w-full text-xs font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] text-slate-500 font-bold block mb-1">Annual Rate (r)</label>
                  <input 
                    type="number" step="0.01" value={r}
                    onChange={(e) => setR(Number(e.target.value))}
                    className="rounded p-1.5 w-full text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 font-bold block mb-1">Volatility (&sigma;)</label>
                  <input 
                    type="number" step="0.01" value={sigma}
                    onChange={(e) => setSigma(Number(e.target.value))}
                    className="rounded p-1.5 w-full text-xs font-mono"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Naked Short callout */}
          {riskMetrics.has_naked_short && (
            <div className="rounded-lg bg-red-500/5 p-4 border border-red-500/10 text-xs">
              <div className="flex gap-2">
                <ShieldAlert className="h-4 w-4 text-[#dc3545] flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-semibold text-slate-200 uppercase tracking-wider text-[10px]">Short Naked Option Warning</p>
                  <p className="text-slate-400 leading-relaxed">
                    Selling options naked (without underlying shares or collateral) exposes you to severe margin requirements and 
                    theoretically infinite loss potentials if the market breaches your strike. Consider changing to a **Covered Call** or buying an OTM option to limit your risk.
                  </p>
                  <Link href="/learn" className="text-xs text-[#5ba4b5] hover:underline font-semibold block mt-1">
                    Ask the Socratic Tutor how to hedge this naked call &rarr;
                  </Link>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
    </ProtectedRoute>
  );
}
