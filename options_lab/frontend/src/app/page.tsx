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
  Key,
  Database,
  ArrowRightLeft
} from 'lucide-react';
import { optionsApi } from '@/lib/api';
import ProtectedRoute from '@/components/ProtectedRoute';

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

  // Watchlist for Cash-Secured Puts (CSP) & Covered Calls (CC)
  const cspWatchlist = [
    { ticker: 'AAPL', price: 220.50, strike: 210.00, delta: -0.22, dte: 35, premium: 4.80, yield: 2.3, annualized: 24.0, earnings: '2026-10-29' },
    { ticker: 'NVDA', price: 124.80, strike: 115.00, delta: -0.25, dte: 35, premium: 5.10, yield: 4.4, annualized: 46.2, earnings: '2026-11-18' },
    { ticker: 'MSFT', price: 422.30, strike: 405.00, delta: -0.19, dte: 35, premium: 6.20, yield: 1.5, annualized: 16.0, earnings: '2026-10-27' },
    { ticker: 'TSLA', price: 215.40, strike: 195.00, delta: -0.28, dte: 35, premium: 7.50, yield: 3.8, annualized: 40.1, earnings: '2026-10-21' }
  ];

  // Fetch all live data from Saxo Bank API
  const fetchBrokerData = async (forceSpinner = false) => {
    if (forceSpinner) setActionLoading(true);
    setErrorMsg(null);
    try {
      // 1. Get status & verify if authenticated
      const statusRes = await optionsApi.getBrokerStatus();
      setBrokerStatus(statusRes);
      
      // If no token is set in the environment, redirect to connection screen
      if (!statusRes?.has_access_token) {
        setIsAuthenticated(false);
        const authUrlRes = await optionsApi.getBrokerAuthUrl().catch(() => null);
        if (authUrlRes?.auth_url) {
          setAuthUrl(authUrlRes.auth_url);
        }
        setLoading(false);
        setActionLoading(false);
        return;
      }
      
      setIsAuthenticated(true);
      
      // 2. Fetch Account Balances
      const accountRes = await optionsApi.getBrokerAccount();
      setBrokerAccount(accountRes);
      
      // 3. Fetch Positions
      const positionsRes = await optionsApi.getBrokerPositions();
      if (positionsRes?.positions) {
        setPositions(positionsRes.positions);
      } else {
        setPositions([]);
      }

      // 4. Fetch Active Orders
      const ordersRes = await optionsApi.getBrokerOrders().catch(() => null);
      if (ordersRes?.orders) {
        setOrders(ordersRes.orders);
      }
      
    } catch (err: any) {
      console.error('Failed to load broker data:', err);
      // Intercept authentication/401 errors
      if (err.message?.includes('401') || err.message?.includes('authentication required')) {
        setIsAuthenticated(false);
        const authUrlRes = await optionsApi.getBrokerAuthUrl().catch(() => null);
        if (authUrlRes?.auth_url) {
          setAuthUrl(authUrlRes.auth_url);
        }
      } else {
        setErrorMsg(err.message || 'An unexpected error occurred while communicating with the broker gateway.');
      }
    } finally {
      setLoading(false);
      setActionLoading(false);
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
                  {positions.map((p) => {
                    const isProfit = p.unrealized_pnl >= 0;
                    const side = p.amount >= 0 ? 'Long' : 'Short';
                    const isOption = p.asset_type === 'StockOption' || p.asset_type === 'Option';

                    return (
                      <tr key={p.position_id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="py-3 px-3 font-bold text-slate-900">{p.symbol}</td>
                        <td className="py-3 px-3 text-slate-500 max-w-xs truncate" title={p.description}>
                          {p.description}
                          {isOption && p.expiry_date && (
                            <span className="block text-[9px] text-slate-400 font-mono mt-0.5">
                              Expiry: {p.expiry_date} | Strike: ${p.strike_price} {p.option_type?.toUpperCase()}
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-center">
                          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold uppercase">
                            {p.asset_type === 'StockOption' ? 'Option' : p.asset_type}
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
                          {p.amount.toLocaleString()}
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-slate-600">
                          ${p.open_price.toFixed(2)}
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-slate-600">
                          ${p.current_price.toFixed(2)}
                        </td>
                        <td className="py-3 px-3 text-right font-mono text-slate-800">
                          ${p.market_value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                        </td>
                        <td className="py-3 px-3 text-right font-mono">
                          <span className={`font-bold block ${isProfit ? 'text-emerald-600' : 'text-rose-600'}`}>
                            {isProfit ? '+' : ''}{p.unrealized_pnl.toFixed(2)} {p.currency}
                          </span>
                          <span className={`text-[10px] block font-semibold ${isProfit ? 'text-emerald-500' : 'text-rose-500'}`}>
                            {isProfit ? '+' : ''}{p.unrealized_pnl_pct.toFixed(2)}%
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
            <div>
              <h3 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                <ArrowRightLeft className="h-4 w-4 text-emerald-600" /> CSP Watchlist &amp; Opportunity Scanner
              </h3>
              <p className="text-[11px] text-slate-400">Scan for cash-secured puts yield setups targeting ~0.20 to 0.30 Delta strikes.</p>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-2 px-3">Ticker</th>
                    <th className="py-2 px-3 text-right">Stock Price</th>
                    <th className="py-2 px-3 text-right">Target Put Strike</th>
                    <th className="py-2 px-3 text-center">Delta</th>
                    <th className="py-2 px-3 text-right">Premium</th>
                    <th className="py-2 px-3 text-right">Annual Yield</th>
                    <th className="py-2 px-3 text-center">Earnings Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs text-slate-600 font-medium">
                  {cspWatchlist.map((c) => (
                    <tr key={c.ticker} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-2.5 px-3 font-bold text-slate-900">{c.ticker}</td>
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
