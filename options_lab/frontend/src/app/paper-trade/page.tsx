'use client';

import React, { useState, useEffect } from 'react';
import { Briefcase, ArrowUpRight, DollarSign, RefreshCw, X, ShieldAlert } from 'lucide-react';
import { optionsApi } from '@/lib/api';
import ProtectedRoute from '@/components/ProtectedRoute';

interface Position {
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

export default function PaperTradePage() {
  const [balance, setBalance] = useState<number>(100000);
  const [positions, setPositions] = useState<Position[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string>('AAPL');
  const [selectedStrategy, setSelectedStrategy] = useState<string>('covered_call');
  const [qty, setQty] = useState<number>(1);
  const [executing, setExecuting] = useState(false);

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

  const fetchTickerQuote = async () => {
    if (!selectedTicker) return;
    try {
      const res = await optionsApi.getQuote(selectedTicker);
      setQuote({
        price: res.current_price,
        vol: res.historical_volatility
      });
    } catch (err) {
      console.error(err);
    }
  };

  // Fetch universe on mount
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
          }
        }
      } catch (err) {
        console.error("Failed to load universe", err);
      } finally {
        setLoadingUniverse(false);
      }
    };
    fetchUniverse();
  }, []);

  useEffect(() => {
    fetchTickerQuote();
  }, [selectedTicker]);

  const handleSectorChange = (sector: string) => {
    setActiveSector(sector);
    const sectorStocks = universe[sector];
    if (sectorStocks && sectorStocks.length > 0) {
      setSelectedTicker(sectorStocks[0].symbol);
    }
  };

  // Execute strategy trade
  const executeTrade = async () => {
    setExecuting(true);
    try {
      let premium = 0;
      let name = '';
      
      // Calculate realistic premium values based on strategy
      if (selectedStrategy === 'covered_call') {
        // Long Stock at spot, Short Call at strike (spot + 5%)
        // Premium received = ~3% of spot price
        premium = quote.price * 0.035;
        name = 'Covered Call';
      } else if (selectedStrategy === 'secured_put') {
        // Short Put at strike (spot - 5%)
        // Premium received = ~2.5% of spot price
        premium = quote.price * 0.028;
        name = 'Cash-Secured Put';
      } else if (selectedStrategy === 'naked_call') {
        // Short Call at strike (spot + 5%) without stock
        premium = quote.price * 0.022;
        name = 'Naked Call';
      }

      // Entry cost / credit calculation
      // Covered call: Pay for stock (spot * 100) - receive premium (prem * 100)
      const multiplier = 100;
      let netCost = 0;
      
      if (selectedStrategy === 'covered_call') {
        netCost = (quote.price - premium) * qty * multiplier;
      } else {
        // short put/call gives credit
        netCost = -premium * qty * multiplier;
      }

      if (balance - netCost < 0) {
        alert("Insufficient capital to execute trade!");
        return;
      }

      const newPos: Position = {
        id: Date.now().toString(),
        symbol: selectedTicker.toUpperCase(),
        strategy: name,
        entryPrice: quote.price,
        currentPrice: quote.price,
        quantity: qty,
        netPremium: premium,
        pnl: 0,
        openDate: new Date().toLocaleDateString(),
        type: selectedStrategy as any
      };

      setPositions([...positions, newPos]);
      setBalance(prev => prev - netCost);
    } catch (err) {
      console.error(err);
    } finally {
      setExecuting(false);
    }
  };

  // Close position early
  const closePosition = (id: string) => {
    const pos = positions.find(p => p.id === id);
    if (!pos) return;

    const multiplier = 100;
    let refund = 0;

    if (pos.type === 'covered_call') {
      // Sell stock at spot + buy back call at current valuation (assume 50% decay for ease of simulation)
      const currentCallValue = pos.netPremium * 0.5;
      refund = (pos.currentPrice - currentCallValue) * pos.quantity * multiplier;
    } else {
      // Buy back option at current valuation
      const currentOptValue = pos.netPremium * 0.5;
      refund = (pos.netPremium - currentOptValue) * pos.quantity * multiplier;
    }

    setBalance(prev => prev + refund);
    setPositions(positions.filter(p => p.id !== id));
  };

  // Simulates price movements and recalculates P&L
  const simulateMarketShift = (pct: number) => {
    setQuote(prev => ({
      ...prev,
      price: prev.price * (1 + pct)
    }));

    setPositions(prev => prev.map(pos => {
      const newPrice = pos.currentPrice * (1 + pct);
      let pnl = 0;
      const multiplier = 100;

      if (pos.type === 'covered_call') {
        // Stock P&L + Call decay P&L
        const stockGain = (newPrice - pos.entryPrice) * pos.quantity * multiplier;
        // Call loses value as price drops, increases if price rises. 
        // Simple modeling: call value is intrinsic + some time value
        const callValue = Math.max(newPrice - (pos.entryPrice * 1.05), 0) + (pos.netPremium * 0.3);
        const callGain = (pos.netPremium - callValue) * pos.quantity * multiplier;
        pnl = stockGain + callGain;
      } else if (pos.type === 'secured_put') {
        // Put gains if stock rises (expires worthless), loses if stock falls below strike
        const strike = pos.entryPrice * 0.95;
        const putValue = Math.max(strike - newPrice, 0) + (pos.netPremium * 0.2);
        pnl = (pos.netPremium - putValue) * pos.quantity * multiplier;
      } else if (pos.type === 'naked_call') {
        // Call loses if stock rises (unlimited risk!)
        const strike = pos.entryPrice * 1.05;
        const callValue = Math.max(newPrice - strike, 0) + (pos.netPremium * 0.2);
        pnl = (pos.netPremium - callValue) * pos.quantity * multiplier;
      }

      return {
        ...pos,
        currentPrice: newPrice,
        pnl: parseFloat(pnl.toFixed(2))
      };
    }));
  };

  return (
    <ProtectedRoute>
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <Briefcase className="h-6 w-6 text-[#5ba4b5]" /> Zero-Loss Paper Trading Sandbox
          </h1>
          <p className="text-slate-400 text-sm">Practice execution of multi-leg income strategies with real-time portfolio metrics.</p>
        </div>
      </div>

      {/* Portfolio overview */}
      <div className="grid gap-6 md:grid-cols-3">
        <div className="glass-card p-6">
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Available Cash</span>
          <h2 className="text-3xl font-extrabold font-mono text-slate-200 mt-1">${balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</h2>
        </div>
        <div className="glass-card p-6">
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Net Open Positions</span>
          <h2 className="text-3xl font-extrabold font-mono text-slate-200 mt-1">{positions.length}</h2>
        </div>
        <div className="glass-card p-6">
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Total Open P&L</span>
          <h2 className={`text-3xl font-extrabold font-mono mt-1 ${
            positions.reduce((sum, p) => sum + p.pnl, 0) >= 0 ? 'text-[#7ec8a0]' : 'text-[#dc3545]'
          }`}>
            {positions.reduce((sum, p) => sum + p.pnl, 0) >= 0 ? '+' : ''}
            ${positions.reduce((sum, p) => sum + p.pnl, 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </h2>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Trade Executor */}
        <div className="glass-card p-6 space-y-6 h-fit">
          <h3 className="text-md font-bold text-slate-200 border-b border-slate-800 pb-3">Execute Strategy Leg</h3>

          <div className="space-y-4">
            <div>
              <label className="text-[10px] text-slate-500 font-bold block mb-1 flex justify-between items-center">
                <span>Sector Tab</span>
                {!loadingUniverse && activeSector && (
                  <span className="text-[8px] text-[#d4a853] font-mono font-normal">Active: {activeSector}</span>
                )}
              </label>
              {loadingUniverse ? (
                <div className="h-8 animate-pulse bg-slate-900/60 rounded border border-slate-800/80"></div>
              ) : (
                <div className="flex gap-1.5 overflow-x-auto pb-1.5 pt-0.5 no-scrollbar scroll-smooth">
                  {sectors.map((sec) => (
                    <button
                      key={sec}
                      type="button"
                      onClick={() => handleSectorChange(sec)}
                      className={`text-[9px] font-bold px-2 py-0.5 rounded transition whitespace-nowrap ${
                        activeSector === sec 
                          ? 'bg-[#d4a853] text-slate-950 shadow-md shadow-[#d4a853]/20 font-extrabold' 
                          : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                      }`}
                    >
                      {sec}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="text-[10px] text-slate-500 font-bold block mb-1">Underlying Ticker (Top 10 Momentum)</label>
              {loadingUniverse ? (
                <div className="text-xs text-slate-500 py-1.5 font-mono flex items-center gap-2">
                  <RefreshCw className="h-3 w-3 animate-spin" /> Loading stock universe...
                </div>
              ) : (
                <select 
                  value={selectedTicker}
                  onChange={(e) => setSelectedTicker(e.target.value)}
                  className="rounded p-1.5 w-full text-xs bg-slate-900 border border-slate-800 text-slate-200 font-mono"
                >
                  {universe[activeSector]?.map((stock) => (
                    <option key={stock.symbol} value={stock.symbol}>
                      {stock.symbol} — ${stock.price.toFixed(2)} ({stock.pctchange >= 0 ? '+' : ''}{stock.pctchange.toFixed(2)}%)
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div>
              <label className="text-[10px] text-slate-500 font-bold block mb-1">Income Strategy Preset</label>
              <select 
                value={selectedStrategy}
                onChange={(e) => setSelectedStrategy(e.target.value)}
                className="rounded p-1.5 w-full text-xs"
              >
                <option value="covered_call">Covered Call (Long stock + Short Call)</option>
                <option value="secured_put">Cash-Secured Put (Short Put + Cash Reserve)</option>
                <option value="naked_call">Naked Call (Short Call Only — High Risk)</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono py-2 bg-[#12141c]/50 rounded-lg px-3">
              <div>
                <span className="text-slate-500 block">Est. Premium</span>
                <span className="text-[#7ec8a0] font-semibold">+${(quote.price * (selectedStrategy === 'covered_call' ? 0.035 : selectedStrategy === 'secured_put' ? 0.028 : 0.022)).toFixed(2)}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Strike Target</span>
                <span className="text-slate-200">
                  ${selectedStrategy === 'secured_put' ? Math.round(quote.price * 0.95) : Math.round(quote.price * 1.05)}
                </span>
              </div>
            </div>

            <div>
              <label className="text-[10px] text-slate-500 font-bold block mb-1">Quantity (Contracts / Lots)</label>
              <input 
                type="number" min="1" value={qty}
                onChange={(e) => setQty(Number(e.target.value))}
                className="rounded p-1.5 w-full text-xs font-mono"
              />
            </div>

            <button 
              onClick={executeTrade}
              disabled={executing}
              className="w-full rounded-lg bg-[#5ba4b5] hover:bg-[#4a91a2] text-slate-900 py-2.5 text-xs font-semibold transition"
            >
              Place Simulated Trade
            </button>
          </div>
        </div>

        {/* Positions ledger & Market Shifter */}
        <div className="lg:col-span-2 space-y-6">
          {/* Shift Panel */}
          <div className="glass-card p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-md font-bold text-slate-200">Simulate Market Events (What-If Shifts)</h3>
              <span className="text-[10px] text-slate-400">Shift spot prices to evaluate real-time P&L changes</span>
            </div>
            
            <div className="grid grid-cols-4 gap-3 text-center">
              <button 
                onClick={() => simulateMarketShift(-0.10)}
                className="rounded-lg bg-red-500/10 border border-red-500/20 text-[#dc3545] py-2 text-xs font-semibold hover:bg-red-500/20 transition"
              >
                Market Drops 10%
              </button>
              <button 
                onClick={() => simulateMarketShift(-0.03)}
                className="rounded-lg bg-red-500/5 border border-red-500/10 text-red-400 py-2 text-xs font-semibold hover:bg-red-500/10 transition"
              >
                Market Drops 3%
              </button>
              <button 
                onClick={() => simulateMarketShift(0.03)}
                className="rounded-lg bg-emerald-500/5 border border-emerald-500/10 text-[#7ec8a0] py-2 text-xs font-semibold hover:bg-emerald-500/10 transition"
              >
                Market Rises 3%
              </button>
              <button 
                onClick={() => simulateMarketShift(0.10)}
                className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-[#7ec8a0] py-2 text-xs font-semibold hover:bg-emerald-500/20 transition"
              >
                Market Rises 10%
              </button>
            </div>
          </div>

          {/* Open positions list */}
          <div className="glass-card p-6 space-y-4">
            <h3 className="text-md font-bold text-slate-200">Open Sandbox Positions</h3>

            {positions.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-500">
                No active positions. Execute a trade above to start testing outcomes.
              </div>
            ) : (
              <div className="space-y-4">
                {positions.map((pos) => (
                  <div key={pos.id} className="flex justify-between items-center border-b border-slate-800 pb-3 last:border-0 last:pb-0">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-200">{pos.symbol}</span>
                        <span className="rounded bg-[#5ba4b5]/10 px-2 py-0.5 text-[9px] text-[#5ba4b5] font-semibold">{pos.strategy}</span>
                      </div>
                      <div className="flex gap-4 text-[10px] text-slate-400 font-mono">
                        <span>Qty: {pos.quantity}</span>
                        <span>Entry Spot: ${pos.entryPrice.toFixed(2)}</span>
                        <span>Current Spot: ${pos.currentPrice.toFixed(2)}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <span className={`text-xs font-bold font-mono ${pos.pnl >= 0 ? 'text-[#7ec8a0]' : 'text-[#dc3545]'}`}>
                          {pos.pnl >= 0 ? '+' : ''}${pos.pnl.toFixed(2)}
                        </span>
                        <span className="block text-[9px] text-slate-500 font-mono">Premium: ${pos.netPremium.toFixed(2)}</span>
                      </div>
                      <button 
                        onClick={() => closePosition(pos.id)}
                        className="text-slate-500 hover:text-slate-300 transition"
                        title="Close Position"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
    </ProtectedRoute>
  );
}
