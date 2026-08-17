'use client';

import React, { useState, useEffect } from 'react';
import { 
  Briefcase, 
  ArrowUpRight, 
  DollarSign, 
  RefreshCw, 
  X, 
  ShieldAlert, 
  ShieldCheck, 
  Layers, 
  History, 
  TrendingUp, 
  AlertCircle,
  Activity,
  CheckCircle2,
  Clock
} from 'lucide-react';
import { optionsApi } from '@/lib/api';
import ProtectedRoute from '@/components/ProtectedRoute';
import {
  BrokerStatus,
  BrokerAccountSummary,
  BrokerPosition,
  BrokerOrder
} from '@/types/broker';

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
  const [activeTab, setActiveTab] = useState<'broker_audit' | 'simulator'>('broker_audit');
  
  // ── Real / SIM Broker Gateway State ───────────────────────────────────────
  const [brokerStatus, setBrokerStatus] = useState<BrokerStatus | null>(null);
  const [brokerAccount, setBrokerAccount] = useState<BrokerAccountSummary | null>(null);
  const [brokerPositions, setBrokerPositions] = useState<BrokerPosition[]>([]);
  const [brokerOrders, setBrokerOrders] = useState<BrokerOrder[]>([]);
  const [loadingBroker, setLoadingBroker] = useState<boolean>(true);
  const [refreshingBroker, setRefreshingBroker] = useState<boolean>(false);
  const [brokerError, setBrokerError] = useState<string | null>(null);
  const [manualToken, setManualToken] = useState<string>('');
  const [savingToken, setSavingToken] = useState<boolean>(false);
  const [tokenSuccessMsg, setTokenSuccessMsg] = useState<string | null>(null);
  const [authUrl, setAuthUrl] = useState<string>('');

  // ── Simulator Sandbox State ───────────────────────────────────────────────
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

  // ── Fetch Broker Gateway Data (Account, Positions, Orders) ────────────────
  const fetchBrokerData = async (isManual: boolean = false) => {
    if (isManual) setRefreshingBroker(true);
    else setLoadingBroker(true);
    setBrokerError(null);

    try {
      const [statusRes, accountRes, positionsRes, ordersRes] = await Promise.all([
        optionsApi.getBrokerStatus().catch(() => null),
        optionsApi.getBrokerAccount().catch((err) => {
          console.error("Failed to load broker account", err);
          return null;
        }),
        optionsApi.getBrokerPositions().catch((err) => {
          console.error("Failed to load broker positions", err);
          return { positions: [], total_positions_count: 0, total_unrealized_pnl: 0 };
        }),
        optionsApi.getBrokerOrders().catch((err) => {
          console.error("Failed to load broker orders", err);
          return { orders: [], total_orders_count: 0 };
        })
      ]);

      if (statusRes) setBrokerStatus(statusRes);
      if (accountRes) setBrokerAccount(accountRes);
      if (positionsRes) setBrokerPositions(positionsRes.positions || []);
      if (ordersRes) setBrokerOrders(ordersRes.orders || []);

      // Fetch auth URL
      optionsApi.getBrokerAuthUrl().then((res) => {
        if (res?.auth_url) setAuthUrl(res.auth_url);
      }).catch(() => {});
    } catch (err: any) {
      console.error("Failed to sync broker gateway:", err);
      setBrokerError(err.message || "Failed to connect to broker environment.");
    } finally {
      setLoadingBroker(false);
      setRefreshingBroker(false);
    }
  };

  const handleSetToken = async () => {
    if (!manualToken.trim()) return;
    setSavingToken(true);
    setTokenSuccessMsg(null);
    setBrokerError(null);
    try {
      await optionsApi.setBrokerToken({ token: manualToken.trim() });
      setTokenSuccessMsg("✅ Live Saxo token registered! Refreshing blotter...");
      setManualToken('');
      await fetchBrokerData(true);
    } catch (err: any) {
      setBrokerError(err.message || "Failed to register Saxo token.");
    } finally {
      setSavingToken(false);
    }
  };

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

  useEffect(() => {
    fetchBrokerData();

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

  const executeTrade = async () => {
    setExecuting(true);
    try {
      let premium = 0;
      let name = '';
      
      if (selectedStrategy === 'covered_call') {
        premium = quote.price * 0.035;
        name = 'Covered Call';
      } else if (selectedStrategy === 'secured_put') {
        premium = quote.price * 0.028;
        name = 'Cash-Secured Put';
      } else if (selectedStrategy === 'naked_call') {
        premium = quote.price * 0.022;
        name = 'Naked Call';
      }

      const multiplier = 100;
      let netCost = 0;
      
      if (selectedStrategy === 'covered_call') {
        netCost = (quote.price - premium) * qty * multiplier;
      } else {
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
      price: prev.price * (1 + pct)
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
        currentPrice: newPrice,
        pnl: parseFloat(pnl.toFixed(2))
      };
    }));
  };

  const totalPositionsPnl = brokerPositions.reduce((sum, p) => sum + p.unrealized_pnl, 0);

  return (
    <ProtectedRoute>
      <div className="space-y-6 pb-12">
        {/* Banner Header */}
        <div className="relative overflow-hidden rounded-xl bg-white p-6 sm:p-8 border border-slate-200/80 shadow-sm flex flex-col md:flex-row justify-between md:items-center gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold border ${
                brokerAccount?.environment === 'LIVE'
                  ? 'bg-amber-50 text-amber-800 border-amber-200'
                  : 'bg-indigo-50 text-[#4051B5] border-indigo-100'
              }`}>
                <Briefcase className="h-3.5 w-3.5" /> 
                {brokerAccount?.environment === 'LIVE' ? 'LIVE Broker Gateway' : 'Saxo SIM Sandbox'}
              </span>

              {brokerStatus?.allow_live_execution ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-[11px] font-bold text-rose-700 border border-rose-200">
                  <ShieldAlert className="h-3 w-3" /> Live Orders Enabled
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-bold text-emerald-700 border border-emerald-200">
                  <ShieldCheck className="h-3 w-3" /> Safety Shield Active (Read-Only)
                </span>
              )}
            </div>

            <h1 className="text-2xl font-bold text-slate-800 tracking-tight sm:text-3xl">
              Options Trading & <span className="text-[#4051B5]">Broker Gateway</span>
            </h1>
            <p className="text-slate-500 text-xs sm:text-sm leading-relaxed">
              Real-time account balances, live open positions audit, and executed orders ledger with type-safe execution isolation.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => fetchBrokerData(true)}
              disabled={refreshingBroker || loadingBroker}
              className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 px-4 py-2.5 text-xs font-bold text-slate-700 transition shadow-sm disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 text-[#4051B5] ${refreshingBroker ? 'animate-spin' : ''}`} />
              Sync Broker Data
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 space-x-2">
          <button
            onClick={() => setActiveTab('broker_audit')}
            className={`flex items-center gap-2 pb-3 px-4 text-xs font-bold transition border-b-2 ${
              activeTab === 'broker_audit'
                ? 'border-[#4051B5] text-[#4051B5]'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Layers className="h-4 w-4" /> Live / SIM Account Audit ({brokerPositions.length} Positions)
          </button>
          <button
            onClick={() => setActiveTab('simulator')}
            className={`flex items-center gap-2 pb-3 px-4 text-xs font-bold transition border-b-2 ${
              activeTab === 'simulator'
                ? 'border-[#4051B5] text-[#4051B5]'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Activity className="h-4 w-4" /> Interactive Strategy Simulator & What-If
          </button>
        </div>

        {brokerError && (
          <div className="rounded-xl bg-rose-50 p-4 border border-rose-200 flex items-center gap-3 text-rose-800 text-xs">
            <AlertCircle className="h-4 w-4 flex-shrink-0 text-rose-600" />
            <span>{brokerError}</span>
          </div>
        )}

        {/* ── TAB 1: BROKER LIVE/SIM AUDIT & ORDERS ─────────────────────────── */}
        {activeTab === 'broker_audit' && (
          <div className="space-y-6">
            {/* Live Saxo Authentication & Token Connector Bar */}
            <div className="p-5 rounded-xl bg-white border border-slate-200/80 shadow-sm space-y-4">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3 border-b border-slate-100 pb-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-800">Live App: <span className="text-[#4051B5]">Akpegis-Agent</span></span>
                    <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono font-bold">AppKey: 086a7ec0...</span>
                    <span className="text-[10px] bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded font-mono font-bold">Endpoint: live.logonvalidation.net</span>
                  </div>
                  <p className="text-xs text-slate-500">
                    Connect using your 24-hr Developer Token from Saxo Developer Portal or log in via Saxo OAuth.
                  </p>
                </div>

                {authUrl && (
                  <a
                    href={authUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 rounded-lg bg-[#4051B5] hover:bg-[#34449a] text-white px-3.5 py-2 text-xs font-semibold shadow-sm transition flex-shrink-0"
                  >
                    Authorize via Saxo Login <ArrowUpRight className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>

              {/* Token Input Field */}
              <div className="flex flex-col sm:flex-row gap-2.5 items-center">
                <input
                  type="password"
                  placeholder="Paste Saxo 24-hr Developer Access Token or OAuth Code here..."
                  value={manualToken}
                  onChange={(e) => setManualToken(e.target.value)}
                  className="flex-1 w-full bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2 text-xs font-mono text-slate-800 focus:outline-none focus:ring-1 focus:ring-[#4051B5]"
                />
                <button
                  onClick={handleSetToken}
                  disabled={savingToken || !manualToken.trim()}
                  className="w-full sm:w-auto rounded-lg bg-slate-800 hover:bg-slate-900 text-white px-4 py-2 text-xs font-bold transition shadow-sm disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {savingToken ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : null}
                  Register Token
                </button>
              </div>

              {tokenSuccessMsg && (
                <div className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 p-2.5 rounded-lg">
                  {tokenSuccessMsg}
                </div>
              )}
            </div>

            {/* Account Summary Cards */}
            <div className="grid gap-4 md:grid-cols-4">
              <div className="p-5 bg-white border border-slate-200/80 rounded-xl shadow-sm">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Total Account Equity</span>
                <h2 className="text-2xl font-extrabold font-mono text-slate-800 mt-1">
                  ${(brokerAccount?.total_equity || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </h2>
                <span className="text-[10px] text-slate-400 font-mono mt-0.5 block">
                  Account: {brokerAccount?.account_id || 'Connecting...'}
                </span>
              </div>

              <div className="p-5 bg-white border border-slate-200/80 rounded-xl shadow-sm">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Cash Available</span>
                <h2 className="text-2xl font-extrabold font-mono text-slate-800 mt-1">
                  ${(brokerAccount?.cash_available || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </h2>
                <span className="text-[10px] text-slate-400 font-mono mt-0.5 block">
                  Currency: {brokerAccount?.currency || 'USD'}
                </span>
              </div>

              <div className="p-5 bg-white border border-slate-200/80 rounded-xl shadow-sm">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Margin Available / Used</span>
                <h2 className="text-2xl font-extrabold font-mono text-slate-800 mt-1">
                  ${(brokerAccount?.margin_available || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </h2>
                <span className="text-[10px] text-slate-400 font-mono mt-0.5 block">
                  Used: ${(brokerAccount?.margin_used || 0).toFixed(2)}
                </span>
              </div>

              <div className="p-5 bg-white border border-slate-200/80 rounded-xl shadow-sm">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Open Positions P&L</span>
                <h2 className={`text-2xl font-extrabold font-mono mt-1 ${
                  totalPositionsPnl >= 0 ? 'text-[#0AB39C]' : 'text-[#F06548]'
                }`}>
                  {totalPositionsPnl >= 0 ? '+' : ''}
                  ${totalPositionsPnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </h2>
                <span className="text-[10px] text-slate-400 font-mono mt-0.5 block">
                  {brokerPositions.length} active holdings
                </span>
              </div>
            </div>

            {/* Positions Table */}
            <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-4">
              <div className="flex justify-between items-center">
                <div>
                  <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                    <Briefcase className="h-4 w-4 text-[#4051B5]" /> Real-Time Open Positions
                  </h3>
                  <p className="text-xs text-slate-400">Current open equity & options contracts tracked on broker gateway</p>
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  Updated: {brokerAccount?.updated_at ? new Date(brokerAccount.updated_at).toLocaleTimeString() : 'N/A'}
                </span>
              </div>

              {loadingBroker ? (
                <div className="py-12 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin text-[#4051B5]" /> Loading live positions from broker...
                </div>
              ) : brokerPositions.length === 0 ? (
                <div className="py-10 text-center text-xs text-slate-400">
                  No open positions found in this broker environment.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-100 text-slate-400 font-semibold text-[11px]">
                        <th className="pb-3 font-semibold">Instrument / Symbol</th>
                        <th className="pb-3 font-semibold">Asset Type</th>
                        <th className="pb-3 font-semibold">Qty / Amount</th>
                        <th className="pb-3 font-semibold">Entry / Open</th>
                        <th className="pb-3 font-semibold">Mark Price</th>
                        <th className="pb-3 font-semibold">Market Value</th>
                        <th className="pb-3 font-semibold text-right">Unrealized P&L</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {brokerPositions.map((pos) => (
                        <tr key={pos.position_id} className="hover:bg-slate-50/50 transition">
                          <td className="py-3.5">
                            <div className="font-bold text-slate-800 flex items-center gap-2">
                              <span>{pos.symbol}</span>
                              {pos.strike_price && (
                                <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono">
                                  ${pos.strike_price} {pos.option_type?.toUpperCase()}
                                </span>
                              )}
                            </div>
                            <div className="text-[11px] text-slate-400">{pos.description}</div>
                          </td>
                          <td className="py-3.5">
                            <span className={`inline-flex rounded px-2 py-0.5 text-[10px] font-bold ${
                              pos.asset_type === 'StockOption' 
                                ? 'bg-indigo-50 text-[#4051B5]' 
                                : 'bg-slate-100 text-slate-700'
                            }`}>
                              {pos.asset_type}
                            </span>
                          </td>
                          <td className="py-3.5 font-mono font-bold text-slate-800">{pos.amount}</td>
                          <td className="py-3.5 font-mono text-slate-600">${pos.open_price.toFixed(2)}</td>
                          <td className="py-3.5 font-mono text-slate-800 font-bold">${pos.current_price.toFixed(2)}</td>
                          <td className="py-3.5 font-mono text-slate-800 font-bold">${pos.market_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                          <td className="py-3.5 font-mono text-right font-bold">
                            <span className={pos.unrealized_pnl >= 0 ? 'text-[#0AB39C]' : 'text-[#F06548]'}>
                              {pos.unrealized_pnl >= 0 ? '+' : ''}${pos.unrealized_pnl.toFixed(2)} ({pos.unrealized_pnl_pct >= 0 ? '+' : ''}{pos.unrealized_pnl_pct.toFixed(2)}%)
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Executed Orders History Table */}
            <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-4">
              <div className="flex justify-between items-center">
                <div>
                  <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                    <History className="h-4 w-4 text-[#4051B5]" /> Executed Orders & Activity Audit
                  </h3>
                  <p className="text-xs text-slate-400">Chronological ledger of executed, working, and staged broker orders</p>
                </div>
                <span className="text-xs font-mono font-bold text-[#4051B5] bg-indigo-50 px-2.5 py-1 rounded-lg border border-indigo-100">
                  Total Orders: {brokerOrders.length}
                </span>
              </div>

              {loadingBroker ? (
                <div className="py-10 text-center text-xs text-slate-400">Loading order history...</div>
              ) : brokerOrders.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-400">
                  No executed or working orders recorded.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-100 text-slate-400 font-semibold text-[11px]">
                        <th className="pb-3">Order ID</th>
                        <th className="pb-3">Symbol / Contract</th>
                        <th className="pb-3">Side</th>
                        <th className="pb-3">Type</th>
                        <th className="pb-3">Amount</th>
                        <th className="pb-3">Limit Price</th>
                        <th className="pb-3">Filled Price</th>
                        <th className="pb-3">Status</th>
                        <th className="pb-3 text-right">Placed At</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {brokerOrders.map((ord) => (
                        <tr key={ord.order_id} className="hover:bg-slate-50/50 transition">
                          <td className="py-3 font-mono text-[11px] text-slate-500 font-bold">{ord.order_id}</td>
                          <td className="py-3">
                            <span className="font-bold text-slate-800">{ord.symbol}</span>
                            <div className="text-[10px] text-slate-400">{ord.description}</div>
                          </td>
                          <td className="py-3">
                            <span className={`inline-flex rounded px-2 py-0.5 text-[10px] font-bold ${
                              ord.buy_sell === 'Buy' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                            }`}>
                              {ord.buy_sell}
                            </span>
                          </td>
                          <td className="py-3 text-slate-600 font-mono">{ord.order_type}</td>
                          <td className="py-3 font-mono font-bold text-slate-800">{ord.amount}</td>
                          <td className="py-3 font-mono text-slate-700">${ord.order_price.toFixed(2)}</td>
                          <td className="py-3 font-mono text-slate-800 font-bold">
                            {ord.filled_price != null ? `$${ord.filled_price.toFixed(2)}` : '—'}
                          </td>
                          <td className="py-3">
                            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${
                              ord.status === 'Filled' 
                                ? 'bg-emerald-50 text-emerald-700' 
                                : ord.status === 'Working' 
                                ? 'bg-blue-50 text-blue-700'
                                : 'bg-slate-100 text-slate-600'
                            }`}>
                              {ord.status === 'Filled' ? <CheckCircle2 className="h-3 w-3" /> : <Clock className="h-3 w-3" />}
                              {ord.status}
                            </span>
                          </td>
                          <td className="py-3 text-right font-mono text-[11px] text-slate-400">
                            {new Date(ord.placed_at).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── TAB 2: INTERACTIVE STRATEGY SIMULATOR ──────────────────────────── */}
        {activeTab === 'simulator' && (
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Trade Executor */}
            <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-5 h-fit">
              <h3 className="text-base font-bold text-slate-800 border-b border-slate-100 pb-3">Execute Strategy Leg</h3>

              <div className="space-y-4">
                <div>
                  <label className="text-[10px] text-slate-400 font-bold block mb-1 flex justify-between items-center">
                    <span>Sector Universe</span>
                    {!loadingUniverse && activeSector && (
                      <span className="text-[10px] text-[#4051B5] font-mono font-bold">Active: {activeSector}</span>
                    )}
                  </label>
                  {loadingUniverse ? (
                    <div className="h-8 animate-pulse bg-slate-100 rounded-lg border border-slate-200"></div>
                  ) : (
                    <div className="flex gap-1.5 overflow-x-auto pb-1.5 pt-0.5 no-scrollbar scroll-smooth">
                      {sectors.map((sec) => (
                        <button
                          key={sec}
                          type="button"
                          onClick={() => handleSectorChange(sec)}
                          className={`text-[10px] font-bold px-2.5 py-1 rounded-lg transition whitespace-nowrap ${
                            activeSector === sec 
                              ? 'bg-[#4051B5] text-white shadow-sm font-bold' 
                              : 'bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200'
                          }`}
                        >
                          {sec}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <label className="text-[10px] text-slate-400 font-bold block mb-1">Underlying Ticker (Top Momentum)</label>
                  {loadingUniverse ? (
                    <div className="text-xs text-slate-400 py-1.5 font-mono flex items-center gap-2">
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" /> Loading stock universe...
                    </div>
                  ) : (
                    <select 
                      value={selectedTicker}
                      onChange={(e) => setSelectedTicker(e.target.value)}
                      className="bg-slate-50 border border-slate-200 rounded-lg p-2 w-full text-xs text-slate-800 font-mono font-bold"
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
                  <label className="text-[10px] text-slate-400 font-bold block mb-1">Income Strategy Preset</label>
                  <select 
                    value={selectedStrategy}
                    onChange={(e) => setSelectedStrategy(e.target.value)}
                    className="bg-slate-50 border border-slate-200 rounded-lg p-2 w-full text-xs text-slate-800 font-medium"
                  >
                    <option value="covered_call">Covered Call (Long stock + Short Call)</option>
                    <option value="secured_put">Cash-Secured Put (Short Put + Cash Reserve)</option>
                    <option value="naked_call">Naked Call (Short Call Only — High Risk)</option>
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs font-mono py-2.5 bg-slate-50 rounded-lg px-3 border border-slate-200/60">
                  <div>
                    <span className="text-slate-400 block text-[10px] font-sans font-semibold">Est. Premium</span>
                    <span className="text-[#0AB39C] font-bold">+${(quote.price * (selectedStrategy === 'covered_call' ? 0.035 : selectedStrategy === 'secured_put' ? 0.028 : 0.022)).toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] font-sans font-semibold">Strike Target</span>
                    <span className="text-slate-800 font-bold">
                      ${selectedStrategy === 'secured_put' ? Math.round(quote.price * 0.95) : Math.round(quote.price * 1.05)}
                    </span>
                  </div>
                </div>

                <div>
                  <label className="text-[10px] text-slate-400 font-bold block mb-1">Quantity (Contracts / Lots)</label>
                  <input 
                    type="number" min="1" value={qty}
                    onChange={(e) => setQty(Number(e.target.value))}
                    className="bg-slate-50 border border-slate-200 rounded-lg p-2 w-full text-xs font-mono font-bold text-slate-800"
                  />
                </div>

                <button 
                  onClick={executeTrade}
                  disabled={executing}
                  className="w-full rounded-lg bg-[#4051B5] hover:bg-[#34449a] text-white py-2.5 text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  Place Simulated Trade
                </button>
              </div>
            </div>

            {/* Positions Ledger & Market Shifter */}
            <div className="lg:col-span-2 space-y-6">
              {/* Shift Panel */}
              <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-base font-bold text-slate-800">Simulate Market Events (What-If Shifts)</h3>
                  <span className="text-xs text-slate-400 font-medium">Shift spot prices to evaluate real-time P&L changes</span>
                </div>
                
                <div className="grid grid-cols-4 gap-3 text-center">
                  <button 
                    onClick={() => simulateMarketShift(-0.10)}
                    className="rounded-lg bg-rose-50 border border-rose-200 text-rose-700 py-2 text-xs font-bold hover:bg-rose-100 transition shadow-sm"
                  >
                    Market Drops 10%
                  </button>
                  <button 
                    onClick={() => simulateMarketShift(-0.03)}
                    className="rounded-lg bg-amber-50 border border-amber-200 text-amber-700 py-2 text-xs font-bold hover:bg-amber-100 transition shadow-sm"
                  >
                    Market Drops 3%
                  </button>
                  <button 
                    onClick={() => simulateMarketShift(0.03)}
                    className="rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 py-2 text-xs font-bold hover:bg-emerald-100 transition shadow-sm"
                  >
                    Market Rises 3%
                  </button>
                  <button 
                    onClick={() => simulateMarketShift(0.10)}
                    className="rounded-lg bg-indigo-50 border border-indigo-200 text-[#4051B5] py-2 text-xs font-bold hover:bg-indigo-100 transition shadow-sm"
                  >
                    Market Rises 10%
                  </button>
                </div>
              </div>

              {/* Open Positions List */}
              <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-4">
                <h3 className="text-base font-bold text-slate-800">Sandbox Simulated Positions</h3>

                {positions.length === 0 ? (
                  <div className="text-center py-12 text-xs text-slate-400">
                    No active sandbox positions. Execute a trade on the left to start testing outcomes.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {positions.map((pos) => (
                      <div key={pos.id} className="flex justify-between items-center border-b border-slate-100 pb-3.5 last:border-0 last:pb-0">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-800">{pos.symbol}</span>
                            <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-[10px] text-[#4051B5] font-bold border border-indigo-100">{pos.strategy}</span>
                          </div>
                          <div className="flex gap-4 text-[11px] text-slate-500 font-mono">
                            <span>Qty: {pos.quantity}</span>
                            <span>Entry: ${pos.entryPrice.toFixed(2)}</span>
                            <span>Current: ${pos.currentPrice.toFixed(2)}</span>
                          </div>
                        </div>

                        <div className="flex items-center gap-6">
                          <div className="text-right">
                            <span className={`text-xs font-bold font-mono ${pos.pnl >= 0 ? 'text-[#0AB39C]' : 'text-[#F06548]'}`}>
                              {pos.pnl >= 0 ? '+' : ''}${pos.pnl.toFixed(2)}
                            </span>
                            <span className="block text-[10px] text-slate-400 font-mono">Premium: ${pos.netPremium.toFixed(2)}</span>
                          </div>
                          <button 
                            onClick={() => closePosition(pos.id)}
                            className="text-slate-400 hover:text-rose-600 transition p-1"
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
        )}
      </div>
    </ProtectedRoute>
  );
}
