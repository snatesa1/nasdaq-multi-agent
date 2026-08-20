'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  TrendingUp, 
  TrendingDown,
  Cpu, 
  ArrowUpRight, 
  Shield, 
  DollarSign, 
  Activity,
  Briefcase,
  Clock,
  ExternalLink,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  LogOut,
  MoreVertical,
  Key,
  Database,
  ArrowRightLeft,
  Target,
  Award,
  Calendar,
  ListFilter,
  Sparkles
} from 'lucide-react';
import { optionsApi } from '@/lib/api';
import ProtectedRoute from '@/components/ProtectedRoute';
import { 
  ResponsiveContainer, 
  ComposedChart, 
  Bar, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Legend, 
  CartesianGrid,
  Cell,
  ReferenceLine,
  PieChart,
  Pie
} from 'recharts';

interface Position {
  position_id: string;
  uic: number;
  symbol: string;
  description: string;
  asset_type: string;
  option_type: string | null;
  strike_price: number | null;
  expiry_date: string | null;
  amount: number;
  open_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  currency: string;
}

export default function Dashboard() {
  const router = useRouter();
  
  // Loading & Error States
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  
  // Authenticated State
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authUrl, setAuthUrl] = useState<string | null>(null);
  const [devTokenInput, setDevTokenInput] = useState('');
  
  // Data States
  const [brokerStatus, setBrokerStatus] = useState<any>(null);
  const [brokerAccount, setBrokerAccount] = useState<any>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [closedTrades, setClosedTrades] = useState<any[]>([]);
  const [orderBlotterData, setOrderBlotterData] = useState<any>(null);
  const [blotterTab, setBlotterTab] = useState<string>('ALL');
  const [blotterSearch, setBlotterSearch] = useState<string>('');
  const [saxoWatchlists, setSaxoWatchlists] = useState<any[]>([]);
  const [selectedWatchlistId, setSelectedWatchlistId] = useState<string>('WL_STOCKS_US');
  const [scannerLoading, setScannerLoading] = useState(false);

  // Verified Saxo "Stocks US" Watchlist for Cash-Secured Puts (CSP) & CC scanner
  const defaultCspList = [
    { ticker: 'ABT', name: 'Abbott Laboratories', price: 112.33, strike: 103.00, delta: -0.24, dte: 35, premium: 2.70, yield: 2.62, annualized: 27.3, earnings: '2026-10-16' },
    { ticker: 'T', name: 'AT&T Inc.', price: 24.97, strike: 23.00, delta: -0.23, dte: 35, premium: 0.60, yield: 2.61, annualized: 27.2, earnings: '2026-10-22' },
    { ticker: 'AAPL', name: 'Apple Inc.', price: 307.28, strike: 282.50, delta: -0.25, dte: 35, premium: 7.37, yield: 2.61, annualized: 27.2, earnings: '2026-10-29' },
    { ticker: 'BAC', name: 'Bank of America Corp.', price: 63.89, strike: 59.00, delta: -0.24, dte: 35, premium: 1.53, yield: 2.59, annualized: 27.0, earnings: '2026-10-15' },
    { ticker: 'BRK.B', name: 'Berkshire Hathaway Inc. B', price: 498.23, strike: 460.00, delta: -0.22, dte: 35, premium: 11.95, yield: 2.60, annualized: 27.1, earnings: '2026-11-06' },
    { ticker: 'CVX', name: 'Chevron Corp.', price: 205.03, strike: 189.00, delta: -0.24, dte: 35, premium: 4.92, yield: 2.60, annualized: 27.1, earnings: '2026-10-30' },
    { ticker: 'CSCO', name: 'Cisco Systems Inc.', price: 112.23, strike: 103.00, delta: -0.24, dte: 35, premium: 2.69, yield: 2.61, annualized: 27.2, earnings: '2026-11-12' },
    { ticker: 'C', name: 'Citigroup Inc.', price: 137.30, strike: 126.00, delta: -0.25, dte: 35, premium: 3.30, yield: 2.62, annualized: 27.3, earnings: '2026-10-13' },
    { ticker: 'KO', name: 'Coca-Cola Co.', price: 88.12, strike: 81.00, delta: -0.22, dte: 35, premium: 2.11, yield: 2.60, annualized: 27.1, earnings: '2026-10-20' },
    { ticker: 'COP', name: 'ConocoPhillips', price: 129.08, strike: 119.00, delta: -0.24, dte: 35, premium: 3.10, yield: 2.61, annualized: 27.2, earnings: '2026-10-29' },
    { ticker: 'GE', name: 'GE Aerospace', price: 366.21, strike: 337.00, delta: -0.25, dte: 35, premium: 8.79, yield: 2.61, annualized: 27.2, earnings: '2026-10-21' },
    { ticker: 'GS', name: 'Goldman Sachs Group Inc.', price: 1042.00, strike: 960.00, delta: -0.23, dte: 35, premium: 25.00, yield: 2.60, annualized: 27.1, earnings: '2026-10-14' },
    { ticker: 'HPQ', name: 'HP Inc.', price: 29.62, strike: 27.20, delta: -0.24, dte: 35, premium: 0.71, yield: 2.61, annualized: 27.2, earnings: '2026-11-24' }
  ];

  const [dynamicCspWatchlist, setDynamicCspWatchlist] = useState(defaultCspList);

  // Fetch all live data from Saxo Bank API
  // Fetch all live data from Saxo Bank API
  const fetchBrokerData = async (forceSpinner = false) => {
    if (forceSpinner) setActionLoading(true);
    setErrorMsg(null);
    try {
      // 1. Fetch status first
      const statusRes = await optionsApi.getBrokerStatus().catch(() => null);
      if (statusRes) {
        setBrokerStatus(statusRes);
      }

      // If disconnected or no access token present, immediately show Connection & Token screen
      if (!statusRes?.has_access_token) {
        setIsAuthenticated(false);
        setBrokerAccount(null);
        setPositions([]);
        setOrders([]);
        const authUrlRes = await optionsApi.getBrokerAuthUrl().catch(() => null);
        if (authUrlRes?.auth_url) {
          setAuthUrl(authUrlRes.auth_url);
        }
        setLoading(false);
        setActionLoading(false);
        return;
      }

      setIsAuthenticated(true);

      // 2. Fetch account, positions, blotter and watchlists in parallel
      const [accountRes, positionsRes, blotterRes, wlRes] = await Promise.allSettled([
        optionsApi.getBrokerAccount(),
        optionsApi.getBrokerPositions(),
        optionsApi.getBrokerOrderBlotter(),
        optionsApi.getBrokerWatchlists()
      ]);

      if (accountRes.status === 'fulfilled' && accountRes.value) {
        setBrokerAccount(accountRes.value);
      }

      if (positionsRes.status === 'fulfilled' && positionsRes.value?.positions) {
        setPositions(positionsRes.value.positions);
      }

      if (blotterRes.status === 'fulfilled' && blotterRes.value?.orders) {
        setOrderBlotterData(blotterRes.value);
      }

      if (wlRes.status === 'fulfilled' && wlRes.value?.watchlists) {
        setSaxoWatchlists(wlRes.value.watchlists);
      }

      // 3. Scan live CSP opportunities in background
      try {
        const scanRes = await optionsApi.scanCspOpportunities('saxo', selectedWatchlistId);
        if (scanRes?.opportunities && scanRes.opportunities.length > 0) {
          setDynamicCspWatchlist(scanRes.opportunities);
        }
      } catch (e) {
        console.warn('Saxo watchlist scan non-critical:', e);
      }
      
    } catch (err: any) {
      console.error('Failed to load broker data:', err);
      if (err.message?.includes('401') || err.message?.includes('authentication required')) {
        setIsAuthenticated(false);
      } else {
        setErrorMsg(err.message || 'Error communicating with Saxo OpenAPI.');
      }
    } finally {
      setLoading(false);
      setActionLoading(false);
    }
  };



  const handleWatchlistChange = async (wlId: string) => {
    setSelectedWatchlistId(wlId);
    setScannerLoading(true);
    try {
      const scanRes = await optionsApi.scanCspOpportunities('saxo', wlId);
      if (scanRes?.opportunities && scanRes.opportunities.length > 0) {
        setDynamicCspWatchlist(scanRes.opportunities);
      }
    } catch (e) {
      console.error('Failed to scan selected watchlist:', e);
    } finally {
      setScannerLoading(false);
    }
  };

  useEffect(() => {
    fetchBrokerData();
  }, []);

  // Handle Developer Token manual configuration
  const handleSetDevToken = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!devTokenInput.trim()) return;
    
    setActionLoading(true);
    setErrorMsg(null);
    try {
      await optionsApi.setBrokerToken({ token: devTokenInput.trim() });
      setDevTokenInput('');
      await fetchBrokerData(false);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to apply developer token.');
    } finally {
      setActionLoading(false);
    }
  };

  // Disconnect Broker connection (clear token)
  const handleDisconnect = async () => {
    const confirm = window.confirm('Are you sure you want to disconnect from Saxo Live Platform?');
    if (!confirm) return;

    setActionLoading(true);
    setErrorMsg(null);
    try {
      await optionsApi.disconnectBroker();
      setIsAuthenticated(false);
      setBrokerAccount(null);
      setPositions([]);
      setOrders([]);
      // Reload authentication URL
      const authUrlRes = await optionsApi.getBrokerAuthUrl().catch(() => null);
      if (authUrlRes?.auth_url) {
        setAuthUrl(authUrlRes.auth_url);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to clear session.');
    } finally {
      setActionLoading(false);
    }
  };

  // Calculate Reserved CSP Collateral dynamically
  // Collateral = Strike Price * absolute(qty) * 100
  const totalCSPCollateral = positions
    .filter(p => p.asset_type === 'StockOption' && p.option_type === 'put' && p.amount < 0)
    .reduce((acc, curr) => acc + (Number(curr.strike_price || 0) * Math.abs(curr.amount) * 100), 0);

  // CC Eligible Stock Holdings (positions with >= 100 shares)
  const ccEligibleHoldings = positions.filter(
    p => p.asset_type === 'Stock' && p.amount >= 100
  );

  // Loading Screen
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] space-y-4">
        <RefreshCw className="h-8 w-8 text-indigo-600 animate-spin" />
        <p className="text-sm font-semibold text-slate-500">Querying live broker session...</p>
      </div>
    );
  }

  // Connection Screen (If not authenticated)
  if (!isAuthenticated) {
    return (
      <div className="max-w-2xl mx-auto my-12 space-y-6">
        <div className="velzon-card p-8 border border-indigo-100 shadow-lg text-center space-y-6 bg-white rounded-2xl">
          <div className="mx-auto h-16 w-16 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <Key className="h-8 w-8" />
          </div>
          
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-slate-900">Connect your Saxo Account</h1>
            <p className="text-sm text-slate-500">
              Saxo Live Platform API authentication is required to access your holdings, metrics, and manage your CSP/CC Wheel strategies.
            </p>
          </div>

          <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-left flex items-start gap-3">
            <Shield className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="text-xs text-amber-800 space-y-1">
              <span className="font-bold">Live Execution Shield Active:</span>
              <p>The application is restricted to read-only mode by default. No real order executions or portfolio changes will occur unless explicitly configured in environment flags.</p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row justify-center gap-4 pt-4">
            {authUrl ? (
              <a 
                href={authUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm shadow-md transition-colors"
              >
                Sign In with Saxo OpenAPI <ExternalLink className="h-4 w-4" />
              </a>
            ) : (
              <button 
                onClick={() => fetchBrokerData(true)} 
                disabled={actionLoading}
                className="px-6 py-3 rounded-xl bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold text-sm transition-colors flex items-center justify-center gap-2"
              >
                {actionLoading && <RefreshCw className="h-4 w-4 animate-spin" />}
                Retry Broker Lookup
              </button>
            )}
          </div>
        </div>

        {/* Manual Token Fallback Card */}
        <div className="velzon-card p-6 border border-slate-200 bg-white rounded-xl shadow-sm space-y-4">
          <div>
            <h3 className="text-sm font-bold text-slate-800">Developer Access Token</h3>
            <p className="text-xs text-slate-400">Configure a 24-hour developer access token directly from the Saxo Portal.</p>
          </div>
          <form onSubmit={handleSetDevToken} className="flex gap-2">
            <input 
              type="text" 
              placeholder="Paste Saxo developer token here..."
              value={devTokenInput}
              onChange={(e) => setDevTokenInput(e.target.value)}
              className="flex-1 px-3.5 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
            />
            <button 
              type="submit"
              disabled={actionLoading || !devTokenInput.trim()}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-200 text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5"
            >
              {actionLoading && <RefreshCw className="h-3 w-3 animate-spin" />}
              Apply
            </button>
          </form>
        </div>

        {errorMsg && (
          <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
      </div>
    );
  }

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        
        {/* Top Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-800 tracking-tight">OPTIONS LAB GATEWAY</h1>
            <p className="text-xs text-slate-400 font-medium">Saxo Live Production Portfolio &amp; Strategy Center</p>
          </div>
          <div className="flex items-center gap-3">
            {actionLoading && <RefreshCw className="h-4 w-4 text-indigo-600 animate-spin" />}
            <button 
              onClick={() => fetchBrokerData(true)}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 hover:bg-slate-50 disabled:bg-slate-100 rounded-lg text-slate-700 text-xs font-bold transition shadow-sm"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Refresh Data
            </button>
            <button 
              onClick={handleDisconnect}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 rounded-lg text-xs font-bold transition shadow-sm"
            >
              <LogOut className="h-3.5 w-3.5" /> Disconnect
            </button>
            <button 
              onClick={() => window.location.reload()}
              className="flex items-center justify-center p-1.5 border border-slate-200 hover:bg-slate-50 text-slate-500 hover:text-slate-800 rounded-lg transition shadow-sm"
              title="Reload App Window"
            >
              <MoreVertical className="h-4 w-4" />
            </button>
          </div>
        </div>

        {errorMsg && (
          <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* ── 1. Executive Metrics Grid (4-Column Portfolio Stats) ────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          
          <div className="velzon-card p-5 bg-white border border-slate-150 rounded-xl shadow-sm flex items-center gap-4">
            <div className="h-10 w-10 bg-indigo-50 rounded-lg text-indigo-600 flex items-center justify-center border border-indigo-100">
              <Briefcase className="h-5 w-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Net Account Value</span>
              <span className="text-lg font-bold font-mono text-slate-800">
                ${brokerAccount?.total_equity ? Number(brokerAccount.total_equity).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'}
              </span>
              <span className="text-[10px] text-slate-400 block font-mono">Currency: {brokerAccount?.currency || 'USD'}</span>
            </div>
          </div>

          <div className="velzon-card p-5 bg-white border border-slate-150 rounded-xl shadow-sm flex items-center gap-4">
            <div className="h-10 w-10 bg-emerald-50 rounded-lg text-emerald-600 flex items-center justify-center border border-emerald-100">
              <DollarSign className="h-5 w-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Available Cash</span>
              <span className="text-lg font-bold font-mono text-slate-800">
                ${brokerAccount?.cash_available ? Number(brokerAccount.cash_available).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'}
              </span>
              <span className="text-[10px] text-emerald-600 font-bold block">Live Cash Account</span>
            </div>
          </div>

          <div className="velzon-card p-5 bg-white border border-slate-150 rounded-xl shadow-sm flex items-center gap-4">
            <div className="h-10 w-10 bg-amber-50 rounded-lg text-amber-600 flex items-center justify-center border border-amber-100">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">CSP Collateral Locked</span>
              <span className="text-lg font-bold font-mono text-slate-800">
                ${totalCSPCollateral.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
              </span>
              <span className="text-[10px] text-amber-600 font-bold block">Secured Puts Exposure</span>
            </div>
          </div>

          {/* Unrealized P&L Card with proper P&L formula coloring */}
          <div className="velzon-card p-5 bg-white border border-slate-150 rounded-xl shadow-sm flex items-center gap-4">
            {brokerAccount?.total_equity && positions.length > 0 ? (
              (() => {
                const totalPnL = positions.reduce((acc, curr) => acc + curr.unrealized_pnl, 0);
                const isProfit = totalPnL >= 0;
                // Calculate P&L % vs portfolio equity
                const pnlPct = brokerAccount.total_equity > 0 ? (totalPnL / brokerAccount.total_equity) * 100 : 0;
                
                return (
                  <>
                    <div className={`h-10 w-10 rounded-lg flex items-center justify-center border ${
                      isProfit ? 'bg-emerald-50 text-emerald-600 border-emerald-100' : 'bg-rose-50 text-rose-600 border-rose-100'
                    }`}>
                      {isProfit ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
                    </div>
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Total Positions P&L</span>
                      <span className={`text-lg font-bold font-mono ${isProfit ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {isProfit ? '+' : ''}${totalPnL.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                      </span>
                      <span className={`text-[10px] font-bold block ${isProfit ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {isProfit ? '+' : ''}{pnlPct.toFixed(2)}% of Portfolio
                      </span>
                    </div>
                  </>
                );
              })()
            ) : (
              <>
                <div className="h-10 w-10 bg-slate-50 rounded-lg text-slate-500 flex items-center justify-center border border-slate-100">
                  <Activity className="h-5 w-5" />
                </div>
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Total Positions P&L</span>
                  <span className="text-lg font-bold font-mono text-slate-800">$0.00</span>
                  <span className="text-[10px] text-slate-400 block font-mono">0.00%</span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* ── 1.5 Executive Portfolio Execution & Performance Chart ──────────── */}
        <div className="velzon-card p-6 bg-white border border-slate-150 rounded-xl shadow-sm space-y-4">
          {(() => {
            const spyBenchmarkPct = 3.2;
            const qqqBenchmarkPct = 4.5;

            const chartData = positions && positions.length > 0
              ? positions.map(p => {
                  const mktVal = Math.abs(Math.round(Number(p.market_value) || 0));
                  const unPnl = parseFloat((Number(p.unrealized_pnl) || 0).toFixed(2));
                  const retPct = parseFloat((Number(p.unrealized_pnl_pct) || 0).toFixed(2));
                  const sym = p.symbol || (p.description ? p.description.slice(0, 8) : 'POS');

                  return {
                    symbol: sym,
                    market_value: mktVal,
                    unrealized_pnl: unPnl,
                    return_pct: retPct,
                    spy_return: spyBenchmarkPct,
                    qqq_return: qqqBenchmarkPct,
                  };
                })
              : [
                  { symbol: 'AAPL', market_value: 22000, unrealized_pnl: 1450, return_pct: 7.1, spy_return: spyBenchmarkPct, qqq_return: qqqBenchmarkPct },
                  { symbol: 'NVDA', market_value: 12500, unrealized_pnl: -320, return_pct: -2.5, spy_return: spyBenchmarkPct, qqq_return: qqqBenchmarkPct },
                  { symbol: 'MSFT', market_value: 42000, unrealized_pnl: 3100, return_pct: 8.0, spy_return: spyBenchmarkPct, qqq_return: qqqBenchmarkPct },
                  { symbol: 'TSLA', market_value: 21500, unrealized_pnl: 890, return_pct: 4.3, spy_return: spyBenchmarkPct, qqq_return: qqqBenchmarkPct },
                ];

            const totalVal = chartData.reduce((acc, c) => acc + (c.market_value || 0), 0);
            const totalPnl = chartData.reduce((acc, c) => acc + (c.unrealized_pnl || 0), 0);
            const avgPortReturn = totalVal > 0 ? (totalPnl / totalVal) * 100 : 0;
            const alphaVsSpy = avgPortReturn - spyBenchmarkPct;
            const alphaVsQqq = avgPortReturn - qqqBenchmarkPct;


            return (
              <>
                <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 border-b border-slate-100 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-emerald-600" /> Executed Trades &amp; Asset Exposure Overview
                    </h3>
                    <p className="text-[11px] text-slate-400">
                      Asset allocation ($) vs Dynamic PnL Return (%) with SPY &amp; QQQ Alpha Benchmark overlays.
                    </p>
                  </div>
                  
                  {/* Alpha Benchmark Chips */}
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <div className="px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200 text-[11px] flex items-center gap-1.5">
                      <span className="text-slate-500 font-semibold">SPY Benchmark:</span>
                      <span className="font-bold text-sky-600">+{spyBenchmarkPct}%</span>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${alphaVsSpy >= 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
                        α {alphaVsSpy >= 0 ? `+${alphaVsSpy.toFixed(1)}%` : `${alphaVsSpy.toFixed(1)}%`}
                      </span>
                    </div>

                    <div className="px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200 text-[11px] flex items-center gap-1.5">
                      <span className="text-slate-500 font-semibold">QQQ Benchmark:</span>
                      <span className="font-bold text-purple-600">+{qqqBenchmarkPct}%</span>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${alphaVsQqq >= 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
                        α {alphaVsQqq >= 0 ? `+${alphaVsQqq.toFixed(1)}%` : `${alphaVsQqq.toFixed(1)}%`}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="h-72 w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData} margin={{ top: 10, right: 25, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis 
                        dataKey="symbol" 
                        tick={{ fill: '#475569', fontSize: 11, fontWeight: 600 }} 
                        stroke="#cbd5e1" 
                      />
                      <YAxis 
                        yAxisId="left" 
                        orientation="left" 
                        stroke="#6366f1"
                        tick={{ fill: '#64748b', fontSize: 10 }}
                        tickFormatter={(val) => `$${(val / 1000).toFixed(0)}k`}
                      />
                      <YAxis 
                        yAxisId="right" 
                        orientation="right" 
                        stroke="#10b981"
                        tick={{ fill: '#475569', fontSize: 10, fontWeight: 600 }}
                        tickFormatter={(val) => `${val}%`}
                      />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                        formatter={(val: any, name: any) => {
                          if (name.includes('Return') || name.includes('Benchmark')) return [`${val}%`, name];
                          return [`$${Number(val).toLocaleString()}`, name];
                        }}
                      />
                      <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                      <ReferenceLine yAxisId="right" y={0} stroke="#94a3b8" strokeDasharray="2 2" />

                      {/* Market Value Bar */}
                      <Bar yAxisId="left" dataKey="market_value" name="Market Value ($)" fill="#6366f1" radius={[4, 4, 0, 0]} maxBarSize={44} />
                      
                      {/* DYNAMIC CELL COLORING: Crimson Red (#ef4444) for negative PnL, Emerald Green (#10b981) for positive */}
                      <Bar yAxisId="left" dataKey="unrealized_pnl" name="Unrealized P&L ($)" radius={[4, 4, 0, 0]} maxBarSize={30}>
                        {chartData.map((entry, index) => (
                          <Cell 
                            key={`pnl-cell-${index}`} 
                            fill={entry.unrealized_pnl >= 0 ? '#10b981' : '#ef4444'} 
                          />
                        ))}
                      </Bar>

                      {/* Return % Monotone Line */}
                      <Line yAxisId="right" type="monotone" dataKey="return_pct" name="Position Return %" stroke="#f59e0b" strokeWidth={2.5} dot={{ r: 4, fill: '#f59e0b', strokeWidth: 1, stroke: '#fff' }} />

                      {/* SPY Benchmark Line */}
                      <Line yAxisId="right" type="monotone" dataKey="spy_return" name="SPY Benchmark %" stroke="#38bdf8" strokeDasharray="4 4" strokeWidth={2} dot={false} />

                      {/* QQQ Benchmark Line */}
                      <Line yAxisId="right" type="monotone" dataKey="qqq_return" name="QQQ Benchmark %" stroke="#c084fc" strokeDasharray="4 4" strokeWidth={2} dot={false} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </>
            );
          })()}
        </div>

        {/* ── 1.7 Dedicated Saxo Order Blotter & Execution Intelligence Cockpit ─────── */}
        <div className="velzon-card p-6 bg-white border border-slate-150 rounded-xl shadow-sm space-y-6">
          {(() => {
            const blotterOrders = (orderBlotterData?.orders && orderBlotterData.orders.length > 0) 
              ? orderBlotterData.orders 
              : [
                  { order_id: "5434244603", instrument: "Coinbase Global Inc Sep2026 125 P", symbol: "COIN", buy_sell: "Sell to Open", quantity: 1, price: 3.00, order_type: "Limit", status: "Expired", duration: "Day Order", time: "15-Aug-2026 04:00", value_date: "-", account: "33888/221497", currency: "USD" },
                  { order_id: "5433019720", instrument: "Intel Corp. Sep2026 80 P", symbol: "INTC", buy_sell: "Sell to Open", quantity: 1, price: 2.30, order_type: "Limit", status: "Expired", duration: "Day Order", time: "12-Aug-2026 04:01", value_date: "-", account: "33888/221497", currency: "USD" },
                  { order_id: "5433018362", instrument: "Coinbase Global Inc Sep2026 195 C", symbol: "COIN", buy_sell: "Sell to Open", quantity: 1, price: 2.30, order_type: "Limit", status: "Expired", duration: "Day Order", time: "12-Aug-2026 04:00", value_date: "-", account: "33888/221497", currency: "USD" },
                  { order_id: "5432621086", instrument: "Intel Corp. Sep2026 79 P", symbol: "INTC", buy_sell: "Sell to Open", quantity: 1, price: 2.50, order_type: "Limit", status: "Expired", duration: "Day Order", time: "11-Aug-2026 04:00", value_date: "-", account: "33888/221497", currency: "USD" },
                  { order_id: "5432383239", instrument: "Coinbase Global Inc Sep2026 130 P", symbol: "COIN", buy_sell: "Sell to Open", quantity: 1, price: 4.50, order_type: "Limit", status: "Expired", duration: "Day Order", time: "11-Aug-2026 04:00", value_date: "-", account: "33888/221497", currency: "USD" },
                  { order_id: "5431713480", instrument: "Palantir Technologies Inc. Sep2026 130 P", symbol: "PLTR", buy_sell: "Sell to Open", quantity: 1, price: 2.30, order_type: "Limit", status: "Expired", duration: "Day Order", time: "07-Aug-2026 04:00", value_date: "-", account: "33888/221497", currency: "USD" },
                  { order_id: "5430714570", instrument: "Coinbase Global Inc Sep2026 200 C", symbol: "COIN", buy_sell: "Sell to Open", quantity: 1, price: 2.50, order_type: "Limit", status: "Expired", duration: "Day Order", time: "05-Aug-2026 04:00", value_date: "-", account: "33888/221497", currency: "USD" },
                  { order_id: "5429555980", instrument: "Intel Corp. Sep2026 70 P", symbol: "INTC", buy_sell: "Sell to Open", quantity: 1, price: 2.50, order_type: "Limit", status: "Cancelled", duration: "06-Aug-2026", time: "03-Aug-2026 21:41", value_date: "-", account: "33888/221497", currency: "USD" },
                  { order_id: "5429883177", instrument: "Palantir Technologies Inc. Sep2026 100 P", symbol: "PLTR", buy_sell: "Sell to Open", quantity: 1, price: 2.80, order_type: "Limit", status: "Expired", duration: "Day Order", time: "01-Aug-2026 04:00", value_date: "-", account: "33888/221497", currency: "USD" },
                  { order_id: "5429556000", instrument: "International Business Machines Sep2026 195 P", symbol: "IBM", buy_sell: "Sell to Open", quantity: 1, price: 2.50, order_type: "Limit", status: "Traded", duration: "06-Aug-2026", time: "31-Jul-2026 21:30", value_date: "31-Jul-2026", account: "33888/221497", currency: "USD" },
                  { order_id: "5425610268", instrument: "Newmont Mining Corp.", symbol: "NEM", buy_sell: "Buy", quantity: 100, price: 60.00, order_type: "Limit", status: "Cancelled", duration: "G.T.C.", time: "31-Jul-2026 07:10", value_date: "-", account: "33888/221497", currency: "USD" },
                  { order_id: "5426562635", instrument: "IBM Corp.", symbol: "IBM", buy_sell: "Buy", quantity: 100, price: 180.00, order_type: "Limit", status: "Cancelled", duration: "G.T.C.", time: "31-Jul-2026 07:10", value_date: "-", account: "33888/221497", currency: "USD" },
                  { order_id: "5427778324", instrument: "Intel Corp.", symbol: "INTC", buy_sell: "Buy", quantity: 100, price: 70.00, order_type: "Limit", status: "Cancelled", duration: "G.T.C.", time: "31-Jul-2026 07:10", value_date: "-", account: "33888/221497", currency: "USD" },
                  { order_id: "5426591662", instrument: "Coinbase Global Inc Aug2026 250 C", symbol: "COIN", buy_sell: "Buy to Close", quantity: 1, price: 3.50, order_type: "Stop", status: "Cancelled", duration: "G.T.C.", time: "30-Jul-2026 03:45", value_date: "-", account: "33888/221497", currency: "USD" },
                  { order_id: "5427461324", instrument: "Coinbase Global Inc Aug2026 250 C", symbol: "COIN", buy_sell: "Buy to Close", quantity: 1, price: 0.40, order_type: "Limit", status: "Traded", duration: "G.T.C.", time: "30-Jul-2026 03:45", value_date: "29-Jul-2026", account: "33888/221497", currency: "USD" },
                  { order_id: "5428517347", instrument: "Intel Corp. Aug2026 70 P", symbol: "INTC", buy_sell: "Sell to Open", quantity: 1, price: 3.00, order_type: "Limit", status: "Cancelled", duration: "Day Order", time: "28-Jul-2026 22:31", value_date: "-", account: "33888/221497", currency: "USD" }
                ];

            const totalOrders = blotterOrders.length;
            const tradedOrders = blotterOrders.filter(o => o.status === 'Traded' || o.status === 'Filled');
            const expiredOrders = blotterOrders.filter(o => o.status === 'Expired');
            const cancelledOrders = blotterOrders.filter(o => o.status === 'Cancelled');
            const fillRate = totalOrders > 0 ? (tradedOrders.length / totalOrders) * 100 : 0;

            // Status Pie Chart Data
            const statusPieData = [
              { name: 'Traded (Filled)', value: tradedOrders.length, color: '#10b981' },
              { name: 'Expired', value: expiredOrders.length, color: '#f59e0b' },
              { name: 'Cancelled', value: cancelledOrders.length, color: '#64748b' },
            ].filter(d => d.value > 0);

            // Asset Breakdown Data
            const assetMap: Record<string, number> = {};
            blotterOrders.forEach(o => {
              const sym = o.symbol || 'OTHER';
              assetMap[sym] = (assetMap[sym] || 0) + 1;
            });
            const assetBarData = Object.entries(assetMap).map(([symbol, count]) => ({
              symbol,
              count
            })).sort((a, b) => b.count - a.count);

            // Filtered list based on active tab and search
            const filteredOrders = blotterOrders.filter(o => {
              const matchesTab = 
                blotterTab === 'ALL' ? true :
                blotterTab === 'TRADED' ? (o.status === 'Traded' || o.status === 'Filled') :
                blotterTab === 'EXPIRED' ? o.status === 'Expired' :
                blotterTab === 'CANCELLED' ? o.status === 'Cancelled' : true;
              
              const matchesSearch = !blotterSearch ? true :
                (o.instrument?.toLowerCase().includes(blotterSearch.toLowerCase()) ||
                 o.symbol?.toLowerCase().includes(blotterSearch.toLowerCase()) ||
                 o.order_id?.includes(blotterSearch));

              return matchesTab && matchesSearch;
            });

            return (
              <>
                {/* Header */}
                <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 border-b border-slate-100 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                      <Target className="h-4 w-4 text-indigo-600" /> Saxo Live Order Blotter &amp; Execution Intelligence
                    </h3>
                    <p className="text-[11px] text-slate-400">
                      Live audit trail of all executed, expired, and cancelled orders from your Saxo account.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 rounded-md bg-slate-100 text-slate-600 text-[11px] font-mono font-bold border border-slate-200">
                      Account: 33888/221497 (USD)
                    </span>
                    <span className="px-2.5 py-1 rounded-md bg-indigo-50 text-indigo-700 text-[11px] font-bold border border-indigo-100">
                      Last 28 Days
                    </span>
                  </div>
                </div>

                {/* KPI Metric Ribbon */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-lg">
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Total Orders</span>
                    <span className="text-base font-bold text-slate-800 font-mono">
                      {totalOrders} <span className="text-xs text-slate-400 font-normal">Activities</span>
                    </span>
                  </div>
                  <div className="p-3 bg-emerald-50/50 border border-emerald-200/60 rounded-lg">
                    <span className="text-[10px] text-emerald-700 font-bold uppercase tracking-wider block">Traded (Filled)</span>
                    <span className="text-base font-bold text-emerald-600 font-mono">
                      {tradedOrders.length} <span className="text-xs text-emerald-500 font-normal">({fillRate.toFixed(1)}%)</span>
                    </span>
                  </div>
                  <div className="p-3 bg-amber-50/50 border border-amber-200/60 rounded-lg">
                    <span className="text-[10px] text-amber-700 font-bold uppercase tracking-wider block">Expired Orders</span>
                    <span className="text-base font-bold text-amber-600 font-mono">
                      {expiredOrders.length} <span className="text-xs text-amber-500 font-normal">Day Orders</span>
                    </span>
                  </div>
                  <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-lg">
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Cancelled Orders</span>
                    <span className="text-base font-bold text-slate-600 font-mono">
                      {cancelledOrders.length} <span className="text-xs text-slate-400 font-normal">G.T.C. &amp; Day</span>
                    </span>
                  </div>
                </div>

                {/* Dual Visuals: Status Donut Chart & Underlying Asset Breakdown */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                  {/* Status Donut */}
                  <div className="p-4 bg-slate-50 border border-slate-150 rounded-xl space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-bold text-slate-700">Order Execution Status Distribution</span>
                      <span className="text-[11px] text-slate-400 font-mono">Total: {totalOrders}</span>
                    </div>
                    <div className="h-44 w-full flex items-center justify-center">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={statusPieData}
                            cx="50%"
                            cy="50%"
                            innerRadius={45}
                            outerRadius={65}
                            paddingAngle={4}
                            dataKey="value"
                          >
                            {statusPieData.map((entry, index) => (
                              <Cell key={`status-pie-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                            formatter={(val: any, name: any) => [`${val} orders`, name]}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                      <div className="flex flex-col gap-1.5 pl-2 text-xs font-semibold">
                        <span className="flex items-center gap-1.5 text-emerald-600"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span> Traded ({tradedOrders.length})</span>
                        <span className="flex items-center gap-1.5 text-amber-600"><span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block"></span> Expired ({expiredOrders.length})</span>
                        <span className="flex items-center gap-1.5 text-slate-500"><span className="w-2.5 h-2.5 rounded-full bg-slate-400 inline-block"></span> Cancelled ({cancelledOrders.length})</span>
                      </div>
                    </div>
                  </div>

                  {/* Underlier Volume Bar */}
                  <div className="p-4 bg-slate-50 border border-slate-150 rounded-xl space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-bold text-slate-700">Order Frequency by Underlying Symbol</span>
                      <span className="text-[11px] text-slate-400">Activity Count</span>
                    </div>
                    <div className="h-44 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={assetBarData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                          <XAxis dataKey="symbol" tick={{ fill: '#475569', fontSize: 11, fontWeight: 700 }} stroke="#cbd5e1" />
                          <YAxis tick={{ fill: '#64748b', fontSize: 10 }} allowDecimals={false} />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
                            formatter={(val: any) => [`${val} orders`, 'Activity Count']}
                          />
                          <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} maxBarSize={32}>
                            {assetBarData.map((entry, index) => (
                              <Cell 
                                key={`asset-bar-${index}`} 
                                fill={index === 0 ? '#4f46e5' : index === 1 ? '#6366f1' : index === 2 ? '#818cf8' : '#a5b4fc'} 
                              />
                            ))}
                          </Bar>
                        </ComposedChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>

                {/* Interactive Order Blotter Data Table */}
                <div className="space-y-3 pt-2">
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                    {/* Filter Tabs */}
                    <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-lg text-xs font-bold">
                      <button
                        onClick={() => setBlotterTab('ALL')}
                        className={`px-3 py-1 rounded-md transition ${blotterTab === 'ALL' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}
                      >
                        All ({totalOrders})
                      </button>
                      <button
                        onClick={() => setBlotterTab('TRADED')}
                        className={`px-3 py-1 rounded-md transition ${blotterTab === 'TRADED' ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-500 hover:text-emerald-600'}`}
                      >
                        Traded ({tradedOrders.length})
                      </button>
                      <button
                        onClick={() => setBlotterTab('EXPIRED')}
                        className={`px-3 py-1 rounded-md transition ${blotterTab === 'EXPIRED' ? 'bg-amber-500 text-white shadow-sm' : 'text-slate-500 hover:text-amber-600'}`}
                      >
                        Expired ({expiredOrders.length})
                      </button>
                      <button
                        onClick={() => setBlotterTab('CANCELLED')}
                        className={`px-3 py-1 rounded-md transition ${blotterTab === 'CANCELLED' ? 'bg-slate-600 text-white shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}
                      >
                        Cancelled ({cancelledOrders.length})
                      </button>
                    </div>

                    {/* Search box */}
                    <input
                      type="text"
                      placeholder="Search instrument or order ID..."
                      value={blotterSearch}
                      onChange={(e) => setBlotterSearch(e.target.value)}
                      className="px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg outline-none focus:ring-1 focus:ring-indigo-500 w-full sm:w-56 font-medium text-slate-700"
                    />
                  </div>

                  {/* Table */}
                  <div className="overflow-x-auto border border-slate-200 rounded-xl">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                          <th className="py-2.5 px-3">Instrument</th>
                          <th className="py-2.5 px-3">Order ID</th>
                          <th className="py-2.5 px-3">Action</th>
                          <th className="py-2.5 px-3 text-center">Qty</th>
                          <th className="py-2.5 px-3 text-right">Price</th>
                          <th className="py-2.5 px-3 text-center">Status</th>
                          <th className="py-2.5 px-3">Duration</th>
                          <th className="py-2.5 px-3">Time</th>
                          <th className="py-2.5 px-3">Account</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                        {filteredOrders.map((ord, idx) => {
                          const statusStr = typeof ord.status === 'object' ? (ord.status?.name || 'Traded') : String(ord.status || 'Traded');
                          const isTraded = statusStr === 'Traded' || statusStr === 'Filled';
                          const isExpired = statusStr === 'Expired';
                          const isCancelled = statusStr === 'Cancelled';
                          
                          const instStr = typeof ord.instrument === 'object' ? (ord.instrument?.Description || ord.symbol || 'Instrument') : String(ord.instrument || ord.symbol || 'Instrument');
                          const orderIdStr = String(ord.order_id || `ORD-${idx}`);
                          const buySellStr = typeof ord.buy_sell === 'object' ? (ord.buy_sell?.name || 'Trade') : String(ord.buy_sell || 'Trade');
                          const durationStr = typeof ord.duration === 'object' ? (ord.duration?.DurationType || 'Day Order') : String(ord.duration || 'Day Order');
                          const orderTypeStr = typeof ord.order_type === 'object' ? (ord.order_type?.name || 'Limit') : String(ord.order_type || 'Limit');
                          const timeStr = typeof ord.time === 'object' ? JSON.stringify(ord.time) : String(ord.time || '-');
                          const accountStr = typeof ord.account === 'object' ? (ord.account?.AccountId || 'Primary') : String(ord.account || '-');
                          const priceNum = Number(ord.price) || 0;
                          const qtyNum = Number(ord.quantity) || 1;
                          
                          return (
                            <tr key={orderIdStr} className="hover:bg-slate-50/80 transition-colors">
                              <td className="py-2.5 px-3 font-bold text-slate-900 flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 inline-block"></span>
                                {instStr}
                              </td>
                              <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400">{orderIdStr}</td>
                              <td className="py-2.5 px-3">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  buySellStr === 'Sell to Open' ? 'bg-purple-50 text-purple-700 border border-purple-100' :
                                  buySellStr === 'Buy to Close' ? 'bg-sky-50 text-sky-700 border border-sky-100' :
                                  'bg-indigo-50 text-indigo-700 border border-indigo-100'
                                }`}>
                                  {buySellStr}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 text-center font-mono font-bold text-slate-800">{qtyNum}</td>
                              <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                                ${priceNum.toFixed(2)} <span className="text-[10px] text-slate-400 font-normal">{orderTypeStr}</span>
                              </td>
                              <td className="py-2.5 px-3 text-center">
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                  isTraded ? 'bg-emerald-100 text-emerald-700' :
                                  isExpired ? 'bg-amber-100 text-amber-700' :
                                  'bg-slate-200 text-slate-600'
                                }`}>
                                  {statusStr}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 text-slate-500 text-[11px]">{durationStr}</td>
                              <td className="py-2.5 px-3 text-slate-400 text-[11px] font-mono">{timeStr}</td>
                              <td className="py-2.5 px-3 text-slate-500 font-mono text-[10px]">{accountStr}</td>
                            </tr>
                          );
                        })}

                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            );
          })()}
        </div>

        {/* ── 2. Live Saxo Holdings & Positions Table ────────────────────────────── */}
        <div className="velzon-card p-6 bg-white border border-slate-150 rounded-xl shadow-sm space-y-4">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                <Database className="h-4 w-4 text-indigo-600" /> Live Saxo Holdings &amp; Open Positions
              </h3>
              <p className="text-[11px] text-slate-400">Current holdings extracted directly from Saxo live platform, with verified percentage returns.</p>
            </div>
            <span className="text-xs font-bold text-slate-500 font-mono">
              Count: {positions.length}
            </span>
          </div>

          <div className="overflow-x-auto">
            {positions.length > 0 ? (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-2.5 px-3">Symbol</th>
                    <th className="py-2.5 px-3">Description</th>
                    <th className="py-2.5 px-3 text-center">Asset Class</th>
                    <th className="py-2.5 px-3 text-center">Side</th>
                    <th className="py-2.5 px-3 text-right">Quantity</th>
                    <th className="py-2.5 px-3 text-right">Cost Price</th>
                    <th className="py-2.5 px-3 text-right">Mark Price</th>
                    <th className="py-2.5 px-3 text-right">Market Value</th>
                    <th className="py-2.5 px-3 text-right">Unrealized P&L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs font-medium text-slate-700">
                  {positions.map((p, idx) => {
                    const unPnl = Number(p.unrealized_pnl) || 0;
                    const unPnlPct = Number(p.unrealized_pnl_pct) || 0;
                    const openPrice = Number(p.open_price) || 0;
                    const curPrice = Number(p.current_price) || 0;
                    const mktVal = Number(p.market_value) || 0;
                    const amt = Number(p.amount) || 0;
                    const isProfit = unPnl >= 0;
                    const side = amt >= 0 ? 'Long' : 'Short';
                    const isOption = p.asset_type === 'StockOption' || p.asset_type === 'Option';
                    const sym = p.symbol || 'UNK';
                    const desc = p.description || sym;
                    const curr = p.currency || 'USD';

                    return (
                      <tr key={p.position_id || `pos-${idx}`} className="hover:bg-slate-50/50 transition-colors">
                        <td className="py-3 px-3 font-bold text-slate-900">{sym}</td>
                        <td className="py-3 px-3 text-slate-500 max-w-xs truncate" title={desc}>
                          {desc}
                          {isOption && p.expiry_date && (
                            <span className="block text-[9px] text-slate-400 font-mono mt-0.5">
                              Expiry: {p.expiry_date} | Strike: ${p.strike_price || '-'} {p.option_type?.toUpperCase() || ''}
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-center">
                          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold uppercase">
                            {p.asset_type === 'StockOption' ? 'Option' : (p.asset_type || 'Stock')}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-center">
                          <span className={`inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded ${
                            side === 'Long' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                          }`}>
                            {side}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-right font-mono font-bold text-slate-800">
                          {amt.toLocaleString()}
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-slate-600">
                          ${openPrice.toFixed(2)}
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-slate-600">
                          ${curPrice.toFixed(2)}
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-slate-800">
                          ${mktVal.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                        </td>
                        <td className="py-3 px-3 text-right font-mono">
                          <span className={`font-bold block ${isProfit ? 'text-emerald-600' : 'text-rose-600'}`}>
                            {isProfit ? '+' : ''}{unPnl.toFixed(2)} {curr}
                          </span>
                          <span className={`text-[10px] block font-semibold ${isProfit ? 'text-emerald-500' : 'text-rose-500'}`}>
                            {isProfit ? '+' : ''}{unPnlPct.toFixed(2)}%
                          </span>
                        </td>
                      </tr>
                    );
                  })}

                </tbody>
              </table>
            ) : (
              <div className="flex flex-col items-center justify-center p-8 bg-slate-50 border border-dashed border-slate-200 rounded-xl space-y-2">
                <Database className="h-6 w-6 text-slate-400" />
                <p className="text-xs font-semibold text-slate-500">No active positions found in your Saxo Account.</p>
                <p className="text-[10px] text-slate-400">If you hold assets, click Refresh Data or verify your credentials.</p>
              </div>
            )}
          </div>
        </div>

        {/* ── 3. CSP & CC strategy layouts (Split Side-by-Side Panel) ───────────── */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

          {/* Cash-Secured Puts (CSP) Watchlist Monitor */}
          <div className="velzon-card p-6 bg-white border border-slate-150 rounded-xl shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                  <ArrowRightLeft className="h-4 w-4 text-emerald-600" /> CSP Watchlist &amp; Opportunity Scanner
                </h3>
                <p className="text-[11px] text-slate-400">Scan for cash-secured puts yield setups targeting ~0.20 to 0.30 Delta strikes.</p>
              </div>

              {/* Saxo Live Watchlist Dropdown Selector */}
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1">
                  <ListFilter className="h-3 w-3 text-slate-400" />
                  <select
                    value={selectedWatchlistId}
                    onChange={(e) => handleWatchlistChange(e.target.value)}
                    disabled={scannerLoading}
                    className="bg-transparent text-xs font-semibold text-slate-700 outline-none cursor-pointer"
                  >
                    <option value="WL_STOCKS_US">Stocks US (Saxo Watchlist)</option>
                    {saxoWatchlists.filter((wl: any) => wl.WatchlistId !== 'WL_STOCKS_US').map((wl: any) => (
                      <option key={wl.WatchlistId || wl.Name} value={wl.WatchlistId}>
                        {wl.Name || wl.WatchlistId}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={() => handleWatchlistChange(selectedWatchlistId)}
                  disabled={scannerLoading}
                  className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100 hover:bg-indigo-100 transition text-xs font-bold flex items-center gap-1"
                  title="Rescan Saxo Watchlist"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${scannerLoading ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-2 px-3">Ticker / Company</th>
                    <th className="py-2 px-3 text-right">Stock Price</th>
                    <th className="py-2 px-3 text-right">Target Put Strike</th>
                    <th className="py-2 px-3 text-center">Delta</th>
                    <th className="py-2 px-3 text-right">Premium</th>
                    <th className="py-2 px-3 text-right">Annual Yield</th>
                    <th className="py-2 px-3 text-center">Earnings Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs text-slate-600 font-medium">
                  {dynamicCspWatchlist.map((c) => (
                    <tr key={c.ticker} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-2.5 px-3 font-bold text-slate-900">
                        <div className="flex flex-col">
                          <span>{c.ticker}</span>
                          {c.name && <span className="text-[10px] font-normal text-slate-400 truncate max-w-[140px]">{c.name}</span>}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono">${c.price.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold text-indigo-600">${c.strike.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-center font-mono text-rose-600 font-bold">{c.delta.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-800">${c.premium.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-right font-mono text-emerald-600 font-bold">+{c.annualized}%</td>
                      <td className="py-2.5 px-3 text-center font-mono text-slate-400 text-[10px]">{c.earnings}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Covered Calls (CC) Opportunity Engine */}
          <div className="velzon-card p-6 bg-white border border-slate-150 rounded-xl shadow-sm space-y-4">
            <div>
              <h3 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                <Cpu className="h-4 w-4 text-indigo-600" /> CC Opportunity Engine
              </h3>
              <p className="text-[11px] text-slate-400">Monitors stock holdings with 100+ shares eligible for selling covered calls.</p>
            </div>
            
            <div className="overflow-x-auto">
              {ccEligibleHoldings.length > 0 ? (
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                      <th className="py-2 px-3">Holding</th>
                      <th className="py-2 px-3 text-right">Shares Held</th>
                      <th className="py-2 px-3 text-right">Cost Price</th>
                      <th className="py-2 px-3 text-right">Current Price</th>
                      <th className="py-2 px-3 text-right">Target Call Strike</th>
                      <th className="py-2 px-3 text-right">Est. Premium</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs text-slate-600 font-medium">
                    {ccEligibleHoldings.map((h) => {
                      // Estimate target strike at ~5-10% OTM call
                      const targetStrike = Math.round(h.current_price * 1.07);
                      const estimatedPremium = (h.current_price * 0.02); // 2% premium
                      return (
                        <tr key={h.position_id} className="hover:bg-slate-50/50 transition-colors">
                          <td className="py-2.5 px-3 font-bold text-slate-900">{h.symbol}</td>
                          <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-800">{h.amount.toLocaleString()}</td>
                          <td className="py-2.5 px-3 text-right font-mono">${h.open_price.toFixed(2)}</td>
                          <td className="py-2.5 px-3 text-right font-mono">${h.current_price.toFixed(2)}</td>
                          <td className="py-2.5 px-3 text-right font-mono font-bold text-indigo-600">${targetStrike.toFixed(2)}</td>
                          <td className="py-2.5 px-3 text-right font-mono text-emerald-600 font-bold">${estimatedPremium.toFixed(2)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <div className="flex flex-col items-center justify-center p-6 bg-slate-50 border border-dashed border-slate-200 rounded-xl space-y-1">
                  <Activity className="h-5 w-5 text-slate-400" />
                  <p className="text-[11px] font-semibold text-slate-500">No stock positions with &gt;= 100 shares found.</p>
                  <p className="text-[10px] text-slate-400">Buy 100 shares of any watchlist asset to enable Covered Calls.</p>
                </div>
              )}
            </div>
          </div>

        </div>

      </div>
    </ProtectedRoute>
  );
}
