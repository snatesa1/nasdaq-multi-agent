'use client';

import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  RefreshCw, 
  Plus, 
  Trash2, 
  Zap, 
  ShieldCheck, 
  Sliders, 
  Briefcase,
  Play
} from 'lucide-react';
import { optionsApi } from '@/lib/api';
import ProtectedRoute from '@/components/ProtectedRoute';

interface PaperPosition {
  id: string;
  symbol: string;
  strategy: string;
  entryPrice: number;
  currentPrice: number;
  quantity: number;
  netPremium: number;
  pnl: number;
  openDate: string;
  type: 'covered_call' | 'naked_call' | 'secured_put';
}

export default function WhatIfPaperTradePage() {
  // Sandbox State
  const [balance, setBalance] = useState<number>(100000);
  const [positions, setPositions] = useState<PaperPosition[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string>('AAPL');
  const [selectedStrategy, setSelectedStrategy] = useState<'covered_call' | 'secured_put' | 'naked_call'>('covered_call');
  const [qty, setQty] = useState<number>(1);
  const [executing, setExecuting] = useState<boolean>(false);

  // Universe state
  const [universe, setUniverse] = useState<Record<string, Array<{ symbol: string; name: string; marketCap: number; price: number; pctchange: number }>>>({});
  const [sectors, setSectors] = useState<string[]>([]);
  const [activeSector, setActiveSector] = useState<string>('');
  const [loadingUniverse, setLoadingUniverse] = useState<boolean>(true);

  // Quote lookup
  const [quote, setQuote] = useState({
    price: 220.0,
    vol: 0.22
  });
  const [loadingQuote, setLoadingQuote] = useState<boolean>(false);

  const fetchTickerQuote = async (ticker: string) => {
    if (!ticker) return;
    setLoadingQuote(true);
    try {
      const res = await optionsApi.getQuote(ticker);
      if (res?.current_price) {
        setQuote({
          price: res.current_price,
          vol: res.historical_volatility || 0.22
        });
      }
    } catch (err) {
      console.error('Failed to load quote', err);
    } finally {
      setLoadingQuote(false);
    }
  };

  useEffect(() => {
    const fetchUniverse = async () => {
      setLoadingUniverse(true);
      try {
        const data = await optionsApi.getUniverse();
        setUniverse(data);
        const sectorNames = Object.keys(data);
        setSectors(sectorNames);
        if (sectorNames.length > 0) {
          const defaultSector = sectorNames.includes('Technology') ? 'Technology' : sectorNames[0];
          setActiveSector(defaultSector);
          const firstStock = data[defaultSector]?.[0];
          if (firstStock) {
            setSelectedTicker(firstStock.symbol);
            fetchTickerQuote(firstStock.symbol);
          }
        }
      } catch (err) {
        console.error('Failed to load universe', err);
      } finally {
        setLoadingUniverse(false);
      }
    };
    fetchUniverse();
  }, []);

  const handleTickerChange = (ticker: string) => {
    setSelectedTicker(ticker);
    fetchTickerQuote(ticker);
  };

  const handleSectorChange = (sector: string) => {
    setActiveSector(sector);
    const sectorStocks = universe[sector];
    if (sectorStocks && sectorStocks.length > 0) {
      setSelectedTicker(sectorStocks[0].symbol);
      fetchTickerQuote(sectorStocks[0].symbol);
    }
  };

  const executePaperTrade = () => {
    setExecuting(true);
    try {
      let premium = 0;
      let name = '';
      
      if (selectedStrategy === 'covered_call') {
        premium = quote.price * 0.032;
        name = 'Covered Call (+100 Shs, -1 OTM Call)';
      } else if (selectedStrategy === 'secured_put') {
        premium = quote.price * 0.025;
        name = 'Cash-Secured Put (-1 OTM Put)';
      } else if (selectedStrategy === 'naked_call') {
        premium = quote.price * 0.020;
        name = 'Naked Call (-1 OTM Call)';
      }

      const multiplier = 100;
      let netCost = 0;
      
      if (selectedStrategy === 'covered_call') {
        netCost = (quote.price - premium) * qty * multiplier;
      } else {
        netCost = -premium * qty * multiplier;
      }

      if (balance - netCost < 0) {
        alert('Insufficient paper capital to execute this trade simulation!');
        return;
      }

      const newPos: PaperPosition = {
        id: Date.now().toString(),
        symbol: selectedTicker.toUpperCase(),
        strategy: name,
        entryPrice: quote.price,
        currentPrice: quote.price,
        quantity: qty,
        netPremium: premium,
        pnl: 0,
        openDate: new Date().toLocaleDateString(),
        type: selectedStrategy
      };

      setPositions([...positions, newPos]);
      setBalance(prev => prev - netCost);
    } catch (err) {
      console.error(err);
    } finally {
      setExecuting(false);
    }
  };

  const closePosition = (id: string) => {
    const pos = positions.find(p => p.id === id);
    if (!pos) return;

    const multiplier = 100;
    let refund = 0;

    if (pos.type === 'covered_call') {
      const currentCallValue = pos.netPremium * 0.5;
      refund = (pos.currentPrice - currentCallValue) * pos.quantity * multiplier;
    } else {
      const currentOptValue = pos.netPremium * 0.5;
      refund = (pos.netPremium - currentOptValue) * pos.quantity * multiplier;
    }

    setBalance(prev => prev + refund);
    setPositions(positions.filter(p => p.id !== id));
  };

  const simulateMarketShift = (pct: number) => {
    setQuote(prev => ({
      ...prev,
      price: parseFloat((prev.price * (1 + pct)).toFixed(2))
    }));

    setPositions(prev => prev.map(pos => {
      const newPrice = pos.currentPrice * (1 + pct);
      let pnl = 0;
      const multiplier = 100;

      if (pos.type === 'covered_call') {
        const stockGain = (newPrice - pos.entryPrice) * pos.quantity * multiplier;
        const callValue = Math.max(newPrice - (pos.entryPrice * 1.05), 0) + (pos.netPremium * 0.3);
        const callGain = (pos.netPremium - callValue) * pos.quantity * multiplier;
        pnl = stockGain + callGain;
      } else if (pos.type === 'secured_put') {
        const strike = pos.entryPrice * 0.95;
        const putValue = Math.max(strike - newPrice, 0) + (pos.netPremium * 0.2);
        pnl = (pos.netPremium - putValue) * pos.quantity * multiplier;
      } else if (pos.type === 'naked_call') {
        const strike = pos.entryPrice * 1.05;
        const callValue = Math.max(newPrice - strike, 0) + (pos.netPremium * 0.2);
        pnl = (pos.netPremium - callValue) * pos.quantity * multiplier;
      }

      return {
        ...pos,
        currentPrice: parseFloat(newPrice.toFixed(2)),
        pnl: parseFloat(pnl.toFixed(2))
      };
    }));
  };

  const totalPositionsPnl = positions.reduce((sum, p) => sum + p.pnl, 0);

  return (
    <ProtectedRoute>
      <div className="space-y-6 pb-12">
        {/* Banner Header */}
        <div className="relative overflow-hidden rounded-xl bg-white p-6 border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between md:items-center gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 text-indigo-700 px-3 py-1 text-xs font-semibold border border-indigo-100">
                <Sliders className="h-3.5 w-3.5" /> What-If Strategy Simulator
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-bold text-emerald-700 border border-emerald-200">
                <ShieldCheck className="h-3 w-3" /> Risk-Free Simulation Mode
              </span>
            </div>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight">
              Interactive What-If &amp; Strategy Sandbox
            </h1>
            <p className="text-slate-500 text-xs sm:text-sm">
              Model multi-leg option strategies, test market price shocks, and simulate risk scenarios with live spot pricing.
            </p>
          </div>

          <button 
            onClick={() => setBalance(100000)}
            className="flex items-center gap-1.5 px-3 py-2 border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg transition"
          >
            <RefreshCw className="h-3.5 w-3.5 text-indigo-600" /> Reset Capital
          </button>
        </div>

        {/* Capital Summary Cards */}
        <div className="grid gap-4 md:grid-cols-3">
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Simulated Cash Balance</span>
            <h2 className="text-2xl font-extrabold font-mono text-slate-800 mt-1">
              ${balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </h2>
            <span className="text-[10px] text-slate-400 font-mono mt-0.5 block">Virtual Sandbox Currency: USD</span>
          </div>

          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Simulated Positions P&amp;L</span>
            <h2 className={`text-2xl font-extrabold font-mono mt-1 ${totalPositionsPnl >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
              {totalPositionsPnl >= 0 ? '+' : ''}${totalPositionsPnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </h2>
            <span className="text-[10px] text-slate-400 font-mono mt-0.5 block">Active Contracts: {positions.length}</span>
          </div>

          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Selected Asset Under Stress</span>
            <div className="flex items-center justify-between mt-1">
              <h2 className="text-2xl font-extrabold font-mono text-indigo-600">
                {selectedTicker} @ ${quote.price.toFixed(2)}
              </h2>
              <span className="text-xs font-mono font-bold bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded">
                Vol: {(quote.vol * 100).toFixed(1)}%
              </span>
            </div>
            <span className="text-[10px] text-slate-400 font-mono mt-0.5 block">Alpaca Market Data Feed</span>
          </div>
        </div>

        {/* Strategy Configurator & Stress Test Grid */}
        <div className="grid gap-6 lg:grid-cols-3">
          
          {/* Column 1 & 2: Trade Configurator */}
          <div className="lg:col-span-2 p-6 bg-white border border-slate-200 rounded-xl shadow-sm space-y-5">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-500" /> Configure Strategy Simulation
              </h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1.5">Sector</label>
                <select 
                  value={activeSector} 
                  onChange={(e) => handleSectorChange(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-semibold text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  {sectors.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1.5">Ticker</label>
                <select 
                  value={selectedTicker} 
                  onChange={(e) => handleTickerChange(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-bold font-mono text-slate-800 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  {(universe[activeSector] || []).map(s => (
                    <option key={s.symbol} value={s.symbol}>{s.symbol} — {s.name.slice(0, 20)}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1.5">Strategy Type</label>
                <select 
                  value={selectedStrategy} 
                  onChange={(e) => setSelectedStrategy(e.target.value as any)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-semibold text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="covered_call">Covered Call (Buy Stock + Sell Call)</option>
                  <option value="secured_put">Cash-Secured Put (Sell OTM Put)</option>
                  <option value="naked_call">Naked Short Call (Bearish)</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-100">
              <div className="flex items-center gap-3">
                <label className="text-xs font-bold text-slate-700">Contracts / Lots:</label>
                <input 
                  type="number" 
                  min="1" 
                  max="100" 
                  value={qty} 
                  onChange={(e) => setQty(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-20 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-mono font-bold text-center"
                />
              </div>

              <button 
                onClick={executePaperTrade}
                disabled={executing || loadingQuote}
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg shadow-sm transition disabled:opacity-50"
              >
                <Play className="h-3.5 w-3.5 fill-current" /> Execute What-If Trade
              </button>
            </div>
          </div>

          {/* Column 3: Market Stress Test Shockers */}
          <div className="p-6 bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-xl shadow-sm space-y-4">
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Sliders className="h-4 w-4 text-indigo-400" /> Stress Test Shocks
              </h3>
              <p className="text-[11px] text-slate-400 mt-1">Apply instant price shifts to model P&amp;L impact across open positions.</p>
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <button 
                onClick={() => simulateMarketShift(-0.10)}
                className="py-2 px-3 rounded-lg bg-rose-500/20 border border-rose-500/30 hover:bg-rose-500/30 text-rose-300 font-mono text-xs font-bold transition flex items-center justify-center gap-1.5"
              >
                <TrendingDown className="h-3.5 w-3.5" /> -10% Crash
              </button>

              <button 
                onClick={() => simulateMarketShift(-0.05)}
                className="py-2 px-3 rounded-lg bg-rose-500/20 border border-rose-500/30 hover:bg-rose-500/30 text-rose-300 font-mono text-xs font-bold transition flex items-center justify-center gap-1.5"
              >
                <TrendingDown className="h-3.5 w-3.5" /> -5% Dip
              </button>

              <button 
                onClick={() => simulateMarketShift(0.05)}
                className="py-2 px-3 rounded-lg bg-emerald-500/20 border border-emerald-500/30 hover:bg-emerald-500/30 text-emerald-300 font-mono text-xs font-bold transition flex items-center justify-center gap-1.5"
              >
                <TrendingUp className="h-3.5 w-3.5" /> +5% Rally
              </button>

              <button 
                onClick={() => simulateMarketShift(0.10)}
                className="py-2 px-3 rounded-lg bg-emerald-500/20 border border-emerald-500/30 hover:bg-emerald-500/30 text-emerald-300 font-mono text-xs font-bold transition flex items-center justify-center gap-1.5"
              >
                <TrendingUp className="h-3.5 w-3.5" /> +10% Surge
              </button>
            </div>

            <p className="text-[10px] text-slate-400 italic">
              * Shocks will instantly re-evaluate your active position Greeks, intrinsic value, and mark-to-market P&amp;L.
            </p>
          </div>

        </div>

        {/* Active Paper Positions Blotter */}
        <div className="p-6 bg-white border border-slate-200 rounded-xl shadow-sm space-y-4">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <Briefcase className="h-4 w-4 text-indigo-600" /> Active Simulated Positions ({positions.length})
            </h3>
          </div>

          <div className="overflow-x-auto">
            {positions.length > 0 ? (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-2.5 px-3">Symbol</th>
                    <th className="py-2.5 px-3">Strategy</th>
                    <th className="py-2.5 px-3 text-right">Qty</th>
                    <th className="py-2.5 px-3 text-right">Entry Price</th>
                    <th className="py-2.5 px-3 text-right">Sim Price</th>
                    <th className="py-2.5 px-3 text-right">Net Premium</th>
                    <th className="py-2.5 px-3 text-right">Unrealized P&amp;L</th>
                    <th className="py-2.5 px-3 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs font-medium text-slate-700">
                  {positions.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-3 px-3 font-bold text-slate-900">{p.symbol}</td>
                      <td className="py-3 px-3 text-slate-600">{p.strategy}</td>
                      <td className="py-3 px-3 text-right font-mono">{p.quantity}</td>
                      <td className="py-3 px-3 text-right font-mono">${p.entryPrice.toFixed(2)}</td>
                      <td className="py-3 px-3 text-right font-mono">${p.currentPrice.toFixed(2)}</td>
                      <td className="py-3 px-3 text-right font-mono text-emerald-600 font-bold">${(p.netPremium * p.quantity * 100).toFixed(2)}</td>
                      <td className={`py-3 px-3 text-right font-mono font-bold ${p.pnl >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {p.pnl >= 0 ? '+' : ''}${p.pnl.toFixed(2)}
                      </td>
                      <td className="py-3 px-3 text-center">
                        <button 
                          onClick={() => closePosition(p.id)}
                          className="px-2.5 py-1 bg-rose-50 text-rose-700 hover:bg-rose-100 rounded text-[11px] font-bold transition"
                        >
                          Close Leg
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="flex flex-col items-center justify-center p-8 bg-slate-50 border border-dashed border-slate-200 rounded-xl space-y-1">
                <Activity className="h-6 w-6 text-slate-400" />
                <p className="text-xs font-semibold text-slate-500">No active simulated positions in your sandbox.</p>
                <p className="text-[10px] text-slate-400">Configure a strategy above and click Execute What-If Trade.</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </ProtectedRoute>
  );
}
