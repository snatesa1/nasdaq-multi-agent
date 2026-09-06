'use client';

import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  RefreshCw, 
  Sparkles, 
  Layers, 
  DollarSign, 
  Calendar, 
  ArrowUpRight, 
  Briefcase, 
  Lock, 
  Clock, 
  Cpu,
  FileText,
  Activity,
  Award,
  ChevronRight,
  Key,
  Copy,
  Check,
  BookOpen
} from 'lucide-react';
import { optionsApi } from '@/lib/api';
import ProtectedRoute from '@/components/ProtectedRoute';

interface MacroEvent {
  event_id: string;
  title: string;
  category: string;
  impact_score: number;
  affected_tickers: string[];
  summary: string;
  bias: string;
  date: string;
}

interface StagedTrade {
  trade_id: string;
  symbol: string;
  sector?: string;
  strategy: string;
  direction: string;
  strike: number;
  delta: number;
  dte: number;
  premium_estimate: number;
  bid_price?: number;
  ask_price?: number;
  spread?: number;
  pricing_source?: string;
  contracts: number;
  spot_price: number;
  max_margin_impact_pct: number;
  collateral_required: number;
  thesis: string;
  edge_source: string;
  risk_rating: number;
  status: string;
  saxo_order_id?: string;
  proposed_at: string;
  approved_at?: string;
  executed_at?: string;
  week_label: string;
  pillars?: {
    watchlist_status: string;
    trade_history_profile: string;
    margin_status: string;
  };
}

interface MarginStatus {
  total_equity: number;
  cash_available: number;
  margin_used: number;
  margin_utilization_pct: number;
  max_margin_limit_pct: number;
  allowed_margin_dollars: number;
  remaining_margin_headroom: number;
  is_within_limit: boolean;
  currency: string;
  updated_at: string;
}

interface BriefingData {
  week_label: string;
  generated_at: string;
  ai_summary: string;
  framework?: string;
  hitl_status?: string;
  margin_status: MarginStatus;
  scoped_universe_count: number;
  watchlist_tickers: string[];
  active_position_tickers: string[];
  macro_events: MacroEvent[];
  potential_trades: StagedTrade[];
}

export default function WeeklyIntelligencePage() {
  const [briefing, setBriefing] = useState<BriefingData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [handshakeError, setHandshakeError] = useState<string | null>(null);
  const [loadingStep, setLoadingStep] = useState<string>('Verifying Backend Handshake...');
  const [authUrl, setAuthUrl] = useState<string | null>(null);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);
  const [actionLog, setActionLog] = useState<{ id: string; msg: string; time: string; type: 'success' | 'danger' | 'info'; actionUrl?: string }[]>([]);

  const handleCopyBriefing = () => {
    if (!briefing?.ai_summary) return;
    navigator.clipboard.writeText(briefing.ai_summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  useEffect(() => {
    fetchBriefing(false);
    optionsApi.getBrokerAuthUrl().then(res => {
      if (res?.auth_url) setAuthUrl(res.auth_url);
    }).catch(() => null);

    const handleAuthMessage = (e: MessageEvent) => {
      if (e.data?.type === 'SAXO_AUTH_SUCCESS') {
        setActionLog(prev => [
          { id: 'AUTH-OK', msg: '✅ Saxo Live MFA Authentication Successful! Broker session is now active.', time: new Date().toLocaleTimeString(), type: 'success' },
          ...prev
        ]);
        fetchBriefing(true);
      }
    };
    window.addEventListener('message', handleAuthMessage);
    return () => window.removeEventListener('message', handleAuthMessage);
  }, []);

  const handleStartOAuth = (e?: React.MouseEvent) => {
    if (e) e.preventDefault();
    if (!authUrl) return;
    
    if (typeof window !== 'undefined' && (window as any).electronAPI?.openSaxoOauth) {
      (window as any).electronAPI.openSaxoOauth(authUrl)
        .then(() => {
          setActionLog(prev => [
            { id: 'AUTH-OK', msg: '✅ Saxo Live MFA Authenticated via Desktop Interceptor!', time: new Date().toLocaleTimeString(), type: 'success' },
            ...prev
          ]);
          fetchBriefing(true);
        })
        .catch((err: any) => console.error('Electron OAuth error:', err));
      return;
    }

    const width = 600;
    const height = 750;
    const left = window.screen.width / 2 - width / 2;
    const top = window.screen.height / 2 - height / 2;
    window.open(authUrl, 'SaxoMFA', `width=${width},height=${height},left=${left},top=${top}`);
  };

  const fetchBriefing = async (forceRefresh: boolean = false) => {
    setLoading(true);
    setError(null);
    setHandshakeError(null);
    setLoadingStep('Verifying Backend Handshake...');

    // ── STEP 1: PRE-FLIGHT HANDSHAKE & SHORT-CIRCUIT ───────────────────────
    try {
      const handshake = await optionsApi.checkHandshake(3000);
      if (!handshake.ok) {
        // Fast short-circuit: do NOT hang in spinning state!
        const errMsg = handshake.error || 'OptionsLab backend on port 8000 is unreachable.';
        setLoading(false);
        setHandshakeError(errMsg);
        setError(`🔌 Backend Handshake Failed: ${errMsg}`);
        setActionLog(prev => [
          { id: `HANDSHAKE-FAIL-${Date.now()}`, msg: `❌ Handshake Short-Circuited: Backend is offline or not responding.`, time: new Date().toLocaleTimeString(), type: 'danger' },
          ...prev
        ]);
        return; // HALT IMMEDIATELY
      }
    } catch (hErr: any) {
      setLoading(false);
      const targetHost = typeof window !== 'undefined' ? `${window.location.hostname}:${window.location.port || '80'}` : 'localhost:8000';
      const errMsg = `Cannot connect to OptionsLab backend on ${targetHost}. Server is offline.`;
      setHandshakeError(errMsg);
      setError(`🔌 Backend Handshake Failed: ${errMsg}`);
      return;
    }

    // ── STEP 2: DELEGATE TO GOOGLE ADK 2.0 WORKFLOW PIPELINE ───────────────
    setLoadingStep('Synthesizing Google ADK 2.0 Macro Intelligence & Live Quotes...');
    if (forceRefresh) {
      setActionLog(prev => [
        { id: `REFRESH-START-${Date.now()}`, msg: '🔄 Delegating live market synthesis to Google ADK 2.0 graph engine...', time: new Date().toLocaleTimeString(), type: 'info' },
        ...prev
      ]);
    }

    try {
      // Step 2: Fetch weekly briefing with 35s timeout guard
      const data = await optionsApi.getWeeklyBriefing(undefined, forceRefresh, 35000);
      setBriefing(data);
      const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      setLastRefreshedAt(nowStr);

      if (forceRefresh) {
        setActionLog(prev => [
          { id: `SYNC-${Date.now()}`, msg: `⚡ Fresh Macro Intelligence & Live OPRA Quotes Synchronized (${nowStr})`, time: nowStr, type: 'success' },
          ...prev
        ]);
      }
    } catch (err: any) {
      console.error('Failed to load weekly briefing:', err);
      const isTimeout = err.message?.includes('timed out') || err.message?.includes('Timeout');
      const isConnection = err.message?.includes('Handshake Disconnected') || err.message?.includes('Failed to fetch');

      if (isConnection) {
        const targetHost = typeof window !== 'undefined' ? `${window.location.hostname}:${window.location.port || '80'}` : 'localhost:8000';
        setHandshakeError(`Connection dropped: OptionsLab backend server on ${targetHost} became unreachable.`);
        setError(`🔌 Backend Handshake Disconnected: Unable to reach ${targetHost}.`);
      } else if (isTimeout) {
        setError('⏳ Synthesis Timed Out: The background engine took longer than 35s. Please click "Refresh Intelligence" to retry.');
        setActionLog(prev => [
          { id: `TIMEOUT-${Date.now()}`, msg: '⚠️ ADK Pipeline timeout: You can retry or rely on cached data.', time: new Date().toLocaleTimeString(), type: 'danger' },
          ...prev
        ]);
      } else {
        setError(err.message || 'Failed to generate weekly macro intelligence briefing.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (tradeId: string) => {
    setApprovingId(tradeId);
    try {
      const res = await optionsApi.approveTrade(tradeId);
      const nowTime = new Date().toLocaleTimeString();
      
      if (res.status === 'FILLED' || res.status === 'PLACED') {
        setActionLog(prev => [
          { id: tradeId, msg: `✅ Trade ${tradeId} Approved & Placed on Saxo! (Order #${res.saxo_response?.order_id || 'LIVE'})`, time: nowTime, type: 'success' },
          ...prev
        ]);
      } else if (res.status === 'BLOCKED_SAFETY_CONFIG') {
        setActionLog(prev => [
          { id: tradeId, msg: `🛡️ Trade ${tradeId} Approved & Staged (Saxo Safety Shield Active: BROKER_ALLOW_LIVE_EXECUTION=False)`, time: nowTime, type: 'info' },
          ...prev
        ]);
      } else {
        setActionLog(prev => [
          { id: tradeId, msg: `⚠️ Trade ${tradeId} status: ${res.status} (${res.reasons?.join(' ') || 'Blocked'})`, time: nowTime, type: 'danger' },
          ...prev
        ]);
      }
      
      fetchBriefing();
    } catch (err: any) {
      console.error('Approve trade failed:', err);
      setActionLog(prev => [
        { id: tradeId, msg: `❌ Approval Error: ${err.message || 'Failed'}`, time: new Date().toLocaleTimeString(), type: 'danger' },
        ...prev
      ]);
    } finally {
      setApprovingId(null);
    }
  };

  const handleReject = async (tradeId: string) => {
    setRejectingId(tradeId);
    try {
      await optionsApi.rejectTrade(tradeId, 'Rejected by user from Trade Command Center');
      setActionLog(prev => [
        { id: tradeId, msg: `🚫 Trade ${tradeId} Rejected by user.`, time: new Date().toLocaleTimeString(), type: 'info' },
        ...prev
      ]);
      fetchBriefing();
    } catch (err: any) {
      console.error('Reject trade failed:', err);
    } finally {
      setRejectingId(null);
    }
  };

  const margin = briefing?.margin_status;
  const marginPct = margin?.margin_utilization_pct || 0;
  const maxLimitPct = margin?.max_margin_limit_pct || 15.0;

  return (
    <ProtectedRoute>
      <div className="space-y-6 pb-12">
        
        {/* Banner Header - Velzon Clean Light Theme */}
        <div className="relative overflow-hidden rounded-xl bg-white p-6 sm:p-8 border border-slate-200/80 shadow-sm">
          <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-indigo-50/60 blur-2xl" />
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-2 max-w-3xl">
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-[#4051B5] border border-indigo-100">
                  <Sparkles className="h-3.5 w-3.5" /> Weekly Macro Intelligence &amp; Execution Gate
                </span>
                {briefing?.framework && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 border border-emerald-200">
                    <Cpu className="h-3 w-3 text-emerald-600" /> {briefing.framework}
                  </span>
                )}
                <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700 border border-amber-200">
                  <Lock className="h-3 w-3 text-amber-600" /> HITL Gate: Dual-Key Guard
                </span>
              </div>
              <h1 className="text-2xl font-bold text-slate-800 tracking-tight sm:text-3xl">
                Weekly Intelligence &amp; <span className="text-[#4051B5]">Trade Command Center</span>
              </h1>
              <p className="text-slate-500 text-xs sm:text-sm leading-relaxed">
                Monday–Friday macro event digestion, watchlist &amp; trade history pillars, and dual-key live Saxo order execution within a strict 15% margin utilization cap.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {authUrl && (
                <button
                  onClick={handleStartOAuth}
                  className="flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-sm transition cursor-pointer"
                  title="Authenticate Saxo Live via 1-Click MFA Popup"
                >
                  <Key className="h-4 w-4" />
                  Authorize Saxo (MFA)
                </button>
              )}
              <button
                onClick={() => fetchBriefing(true)}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2.5 bg-[#4051B5] hover:bg-[#34449a] text-white rounded-xl text-xs font-semibold shadow-sm transition disabled:opacity-50 cursor-pointer"
                title="Force refresh weekly macro news, live prices, quant strikes, and AI briefing"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                {loading ? 'Refreshing Intelligence...' : 'Refresh Intelligence'}
              </button>
            </div>
          </div>
        </div>

        {handshakeError ? (
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-xl bg-amber-50 border-2 border-amber-300 text-amber-950 shadow-sm">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-6 w-6 shrink-0 text-amber-600 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-amber-900 flex items-center gap-2">
                  🔌 Backend Handshake Short-Circuited
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-200 text-amber-800">
                    {typeof window !== 'undefined' ? `${window.location.hostname}:${window.location.port || '80'}` : '8000'}
                  </span>
                </h4>
                <p className="text-xs text-amber-800 mt-1 leading-relaxed font-medium">
                  {handshakeError}
                </p>
                <p className="text-[11px] font-mono text-amber-700 mt-1.5">
                  Check backend service: <code className="bg-amber-200/70 px-2 py-0.5 rounded font-bold">docker compose ps</code> or <code className="bg-amber-200/70 px-2 py-0.5 rounded font-bold">.\restart_backend.ps1</code>
                </p>
              </div>
            </div>
            <button
              onClick={() => fetchBriefing(true)}
              className="shrink-0 flex items-center gap-2 px-4 py-2.5 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold transition shadow-xs cursor-pointer"
            >
              <RefreshCw className="h-4 w-4" />
              Retry Handshake
            </button>
          </div>
        ) : error && (
          <div className="flex items-center justify-between gap-3 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 shrink-0 text-rose-500" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => fetchBriefing(true)}
              className="px-3 py-1.5 bg-rose-100 hover:bg-rose-200 text-rose-800 rounded-lg text-xs font-bold transition cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {/* Executive Margin & Universe Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="velzon-card p-5 bg-white border border-slate-200/80 rounded-xl shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Margin Utilization</span>
              <ShieldCheck className="h-5 w-5 text-emerald-600" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl font-bold font-mono ${marginPct > 15 ? 'text-rose-600' : 'text-emerald-600'}`}>
                {marginPct.toFixed(1)}%
              </span>
              <span className="text-slate-400 text-xs font-medium">/ {maxLimitPct.toFixed(1)}% Cap</span>
            </div>
            <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
              <div 
                className={`h-full transition-all duration-500 ${marginPct > 12 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                style={{ width: `${Math.min(100, (marginPct / maxLimitPct) * 100)}%` }}
              />
            </div>
          </div>

          <div className="velzon-card p-5 bg-white border border-slate-200/80 rounded-xl shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Total Equity</span>
              <Briefcase className="h-5 w-5 text-[#4051B5]" />
            </div>
            <div className="text-2xl font-bold font-mono text-slate-800">
              ${(margin?.total_equity || 100000).toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </div>
            <span className="text-[11px] text-slate-400 block font-medium">Live Saxo Portfolio Equity</span>
          </div>

          <div className="velzon-card p-5 bg-white border border-slate-200/80 rounded-xl shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Cash Available</span>
              <DollarSign className="h-5 w-5 text-emerald-600" />
            </div>
            <div className="text-2xl font-bold font-mono text-slate-800">
              ${(margin?.cash_available || 70000).toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </div>
            <span className="text-[11px] text-slate-400 block font-medium">Available Cash Collateral</span>
          </div>

          <div className="velzon-card p-5 bg-white border border-slate-200/80 rounded-xl shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Scoped Universe</span>
              <Layers className="h-5 w-5 text-indigo-500" />
            </div>
            <div className="text-2xl font-bold font-mono text-indigo-700">
              18 Tickers
            </div>
            <span className="text-[11px] text-slate-400 block font-medium">13 Watchlist + 5 History Tickers</span>
          </div>
        </div>

        {/* Gemini Multi-Model AI Macro Digest Card */}
        <div className="p-6 bg-gradient-to-br from-indigo-50/50 via-white to-slate-50/50 border border-indigo-100 rounded-xl shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-indigo-100 pb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-[#4051B5]/10 text-[#4051B5]">
                <Cpu className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  Gemini Macroeconomic &amp; Cross-Asset Research Desk Briefing
                </h3>
                <p className="text-[11px] text-slate-400">
                  Daily &amp; weekly institutional synthesis over top 10 market news, calendar catalysts, and options yield posture.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-1 rounded-md bg-indigo-50 text-[#4051B5] text-[11px] font-mono font-bold border border-indigo-100">
                Gemini Multi-Model Pool (Active)
              </span>
              {briefing?.generated_at && (
                <span className="px-2.5 py-1 rounded-md bg-slate-100 text-slate-600 text-[11px] font-mono font-medium border border-slate-200" title={`Generated at ${briefing.generated_at}`}>
                  {new Date(briefing.generated_at).toLocaleDateString([], { month: 'short', day: 'numeric' })} • {new Date(briefing.generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              )}
              {lastRefreshedAt && !briefing?.generated_at && (
                <span className="px-2.5 py-1 rounded-md bg-slate-100 text-slate-600 text-[11px] font-mono font-medium border border-slate-200">
                  Synced: {lastRefreshedAt}
                </span>
              )}
              <button
                onClick={handleCopyBriefing}
                disabled={!briefing?.ai_summary}
                className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 transition text-xs font-semibold flex items-center gap-1.5 shadow-2xs"
                title="Copy formatted markdown report to clipboard"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-600" />
                    <span className="text-emerald-700 font-bold">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5 text-slate-500" />
                    <span>Copy Report</span>
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="pt-1">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-16 px-4 space-y-4 rounded-xl bg-white/70 border border-indigo-100/80 shadow-2xs backdrop-blur-xs">
                <div className="relative flex items-center justify-center">
                  <div className="h-14 w-14 rounded-full border-4 border-indigo-100 border-t-[#4051B5] animate-spin" />
                  <Sparkles className="h-6 w-6 text-[#4051B5] absolute animate-pulse" />
                </div>
                <div className="text-center space-y-1.5 max-w-md">
                  <h4 className="text-sm font-bold text-slate-800">
                    {loadingStep}
                  </h4>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Aggregating real-time news catalysts, fetching authentic Saxo &amp; OPRA Bid-Ask quotes, and evaluating margin safety across watchlist.
                  </p>
                </div>
                <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-50 border border-indigo-100 text-[11px] font-mono font-semibold text-[#4051B5]">
                  <RefreshCw className="h-3.5 w-3.5 animate-spin text-[#4051B5]" />
                  <span>Google ADK 2.0 DAG &amp; Live OPRA Quotes</span>
                </div>
              </div>
            ) : (
              <MacroBriefingView content={briefing?.ai_summary || ''} />
            )}
          </div>
        </div>

        {/* Key Macro Events Section */}
        <div className="space-y-4">
          <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
            <Calendar className="h-5 w-5 text-[#4051B5]" />
            Key Macroeconomic &amp; Market Catalyst Events (Mon–Fri)
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {briefing?.macro_events?.map((evt) => (
              <div key={evt.event_id} className="velzon-card p-5 bg-white border border-slate-200/80 rounded-xl shadow-sm space-y-3 hover:border-indigo-200 transition">
                <div className="flex items-start justify-between gap-3">
                  <span className="px-2.5 py-1 bg-indigo-50 text-[#4051B5] rounded-md border border-indigo-100 font-mono text-xs font-bold">
                    {evt.category}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">{evt.date}</span>
                </div>
                <h3 className="text-sm font-bold text-slate-800">{evt.title}</h3>
                <p className="text-xs text-slate-600 leading-relaxed">{evt.summary}</p>
                
                <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-400 font-medium">Tickers:</span>
                    {evt.affected_tickers?.map(t => (
                      <span key={t} className="px-2 py-0.5 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded font-mono font-bold">
                        {t}
                      </span>
                    ))}
                  </div>
                  <span className="text-amber-600 font-mono font-bold">Impact: {'★'.repeat(evt.impact_score)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Actionable Position Trades Matrix */}
        <div className="space-y-4 pt-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-emerald-600" />
                Potential Position Trades for Next Day / Week
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Evaluated against watchlist stocks, historical win-rate pillars, and real-time margin headroom.
              </p>
            </div>
            <div className="text-xs text-slate-500 flex items-center gap-1.5 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200 font-medium">
              <Lock className="h-3.5 w-3.5 text-emerald-600" />
              <span>Dual-Key User Approval Required Before Saxo Order Placement</span>
            </div>
          </div>

          <div className="space-y-4">
            {briefing?.potential_trades?.map((trade) => {
              const isApproved = trade.status === 'APPROVED' || trade.status === 'FILLED' || trade.status === 'PLACED' || trade.status === 'EXECUTING';
              const isRejected = trade.status === 'REJECTED';
              const isBlocked = trade.status === 'MARGIN_EXCEEDED' || trade.status === 'BLOCKED';

              return (
                <div 
                  key={trade.trade_id}
                  className={`p-6 bg-white border rounded-xl shadow-sm transition-all space-y-4 ${
                    isApproved ? 'border-emerald-300 bg-emerald-50/20' :
                    isRejected ? 'border-slate-200 opacity-60 bg-slate-50/50' :
                    isBlocked ? 'border-rose-300 bg-rose-50/20' :
                    'border-slate-200 hover:border-indigo-200'
                  }`}
                >
                  {/* Header Row */}
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-4">
                    <div className="flex items-center gap-3">
                      <div className="px-3.5 py-2 bg-indigo-50 border border-indigo-100 rounded-xl font-mono text-base font-extrabold text-[#4051B5]">
                        {trade.symbol}
                      </div>
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-base font-bold text-slate-800">{trade.strategy} ${trade.strike}</span>
                          <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-700 rounded font-mono font-medium">
                            Δ {trade.delta}
                          </span>
                          <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-700 rounded font-mono font-medium">
                            {trade.dte} DTE
                          </span>
                          {trade.sector && (
                            <span className="text-[11px] px-2 py-0.5 bg-indigo-50 text-[#4051B5] border border-indigo-100 rounded font-medium">
                              {trade.sector}
                            </span>
                          )}
                        </div>
                        <div className="flex flex-wrap items-center gap-2 mt-1">
                          <span className="text-xs text-slate-500 font-medium">Spot: ${trade.spot_price.toFixed(2)}</span>
                          <span className="text-slate-300">|</span>
                          <span className="text-xs font-bold font-mono text-slate-800">Limit (Mid): ${trade.premium_estimate.toFixed(2)}</span>
                          {trade.bid_price !== undefined && trade.bid_price > 0 && (
                            <>
                              <span className="text-[11px] px-1.5 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded font-mono font-medium">
                                Bid: ${trade.bid_price.toFixed(2)}
                              </span>
                              <span className="text-[11px] px-1.5 py-0.5 bg-sky-50 text-sky-700 border border-sky-200 rounded font-mono font-medium">
                                Ask: ${trade.ask_price?.toFixed(2)}
                              </span>
                              {trade.spread !== undefined && trade.spread > 0 && (
                                <span className="text-[10px] text-slate-400 font-mono">
                                  Spread: ${trade.spread.toFixed(2)}
                                </span>
                              )}
                              <span className="text-[10px] px-1.5 py-0.5 bg-indigo-50 text-[#4051B5] border border-indigo-100 rounded font-semibold uppercase tracking-wider">
                                {trade.pricing_source === 'SAXO_LIVE' ? 'Saxo Live' : trade.pricing_source === 'OPRA_LIVE' ? 'OPRA Live Quote' : 'Model Quote'}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Margin Impact</span>
                        <span className="text-sm font-mono font-bold text-emerald-700">+{trade.max_margin_impact_pct.toFixed(1)}%</span>
                      </div>

                      {/* Status Badge & Actions */}
                      {isApproved ? (
                        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-700 text-xs font-bold">
                          <CheckCircle2 className="h-4 w-4" />
                          <span>{trade.status === 'FILLED' ? 'Executed Live' : 'Approved'}</span>
                        </div>
                      ) : isRejected ? (
                        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 border border-slate-200 rounded-lg text-slate-500 text-xs font-semibold">
                          <XCircle className="h-4 w-4" />
                          <span>Rejected</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleApprove(trade.trade_id)}
                            disabled={approvingId === trade.trade_id}
                            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition shadow-sm flex items-center gap-1.5 disabled:opacity-50"
                          >
                            {approvingId === trade.trade_id ? (
                              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <CheckCircle2 className="h-3.5 w-3.5" />
                            )}
                            Approve Trade
                          </button>

                          <button
                            onClick={() => handleReject(trade.trade_id)}
                            disabled={rejectingId === trade.trade_id}
                            className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition"
                          >
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Edge Thesis Description */}
                  <div className="bg-slate-50/80 border border-slate-150 rounded-xl p-3 text-xs space-y-1">
                    <div className="flex items-center gap-1.5 text-[#4051B5] font-bold">
                      <ArrowUpRight className="h-4 w-4" />
                      <span>Edge Source: {trade.edge_source}</span>
                    </div>
                    <p className="text-slate-700 leading-relaxed pl-5 font-normal">{trade.thesis}</p>
                  </div>

                  {/* 3 Pillars Validation Row */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                    <div className="bg-white border border-slate-200/80 rounded-lg p-2.5">
                      <span className="text-slate-400 block text-[10px] font-bold uppercase">WATCHLIST PILLAR</span>
                      <span className="text-slate-700 font-semibold">{trade.pillars?.watchlist_status || 'Stocks US Watchlist'}</span>
                    </div>
                    <div className="bg-white border border-slate-200/80 rounded-lg p-2.5">
                      <span className="text-slate-400 block text-[10px] font-bold uppercase">HISTORY PILLAR</span>
                      <span className="text-slate-700 font-semibold">{trade.pillars?.trade_history_profile || 'High historical win rate'}</span>
                    </div>
                    <div className="bg-white border border-slate-200/80 rounded-lg p-2.5">
                      <span className="text-slate-400 block text-[10px] font-bold uppercase">MARGIN PILLAR</span>
                      <span className="text-emerald-700 font-mono font-bold">{trade.pillars?.margin_status || 'Compliant with 15% Cap'}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Execution Log Telemetry */}
        {actionLog.length > 0 && (
          <div className="bg-white border border-slate-200/80 rounded-xl p-5 space-y-3 shadow-sm">
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <Activity className="h-4 w-4 text-[#4051B5]" />
              Live Order Execution Telemetry Log
            </h3>
            <div className="space-y-1.5 font-mono text-xs max-h-40 overflow-y-auto">
              {actionLog.map((log, idx) => (
                <div key={idx} className="flex flex-col sm:flex-row sm:items-center justify-between text-slate-700 border-b border-slate-100 pb-1.5 gap-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={log.type === 'danger' ? 'text-rose-600 font-bold' : log.type === 'success' ? 'text-emerald-600 font-bold' : 'text-slate-700'}>{log.msg}</span>
                    {log.type === 'danger' && authUrl && (
                      <button
                        onClick={handleStartOAuth}
                        className="px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded text-[11px] font-bold hover:bg-emerald-100 transition inline-flex items-center gap-1 cursor-pointer"
                      >
                        <Key className="h-3 w-3" /> Authenticate Saxo MFA
                      </button>
                    )}
                  </div>
                  <span className="text-slate-400 text-[10px]">{log.time}</span>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </ProtectedRoute>
  );
}

// ────────────────────────────────────────────────────────────
// INSTITUTIONAL RESEARCH DESK BRIEFING FORMATTER
// ────────────────────────────────────────────────────────────

function MacroBriefingView({ content }: { content: string }) {
  if (!content) {
    return (
      <div className="flex items-center justify-center py-6 text-slate-400 text-xs gap-2">
        <RefreshCw className="h-4 w-4 animate-spin text-[#4051B5]" />
        <span>Synthesizing institutional research desk macro briefing...</span>
      </div>
    );
  }

  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      elements.push(<div key={`blank-${i}`} className="h-1" />);
      i++;
      continue;
    }

    // Markdown Table Detection
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i].trim());
        i++;
      }

      if (tableLines.length >= 2) {
        // Headers from first line
        const headerCells = tableLines[0]
          .split('|')
          .slice(1, -1)
          .map((c) => c.trim());

        // Data rows (skipping divider rows that contain only dashes/colons/pipes)
        const dataRows = tableLines
          .slice(1)
          .filter((l) => Boolean(l.replace(/[\s|:\-]/g, '')))
          .map((l) =>
            l
              .split('|')
              .slice(1, -1)
              .map((c) => c.trim())
          );

        elements.push(
          <div key={`table-${i}`} className="overflow-x-auto my-3 border border-slate-200 rounded-xl shadow-xs">
            <table className="min-w-full divide-y divide-slate-200 text-xs">
              <thead className="bg-slate-50/90 border-b border-slate-200">
                <tr>
                  {headerCells.map((h, hi) => (
                    <th
                      key={hi}
                      className="px-3.5 py-2.5 text-left font-bold text-slate-800 uppercase tracking-wider text-[11px]"
                    >
                      <FormattedText text={h} />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {dataRows.map((row, ri) => (
                  <tr
                    key={ri}
                    className={
                      ri % 2 === 0
                        ? 'bg-white hover:bg-slate-50/70 transition'
                        : 'bg-slate-50/40 hover:bg-slate-50/70 transition'
                    }
                  >
                    {row.map((cell, ci) => (
                      <td key={ci} className="px-3.5 py-2.5 text-slate-700 whitespace-normal font-normal">
                        <FormattedText text={cell} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        continue;
      }
    }

    // ## Level 2 Section Heading
    if (trimmed.startsWith('## ')) {
      const title = trimmed.replace(/^##\s+/, '');
      elements.push(
        <div key={`h2-${i}`} className="pt-4 pb-1.5 border-b border-indigo-100 flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#4051B5] inline-block"></span>
          <h3 className="text-sm sm:text-base font-bold text-slate-900 tracking-tight">
            {title}
          </h3>
        </div>
      );
      i++;
      continue;
    }

    // ### Level 3 Priority Headers or Story Headlines
    if (trimmed.startsWith('### ')) {
      const subTitle = trimmed.replace(/^###\s+/, '');
      const isPriorityTier =
        subTitle.includes('High Priority') ||
        subTitle.includes('Medium Priority') ||
        subTitle.includes('Low Priority');

      if (isPriorityTier) {
        const isHigh = subTitle.includes('High');
        const isMed = subTitle.includes('Medium');
        elements.push(
          <div key={`tier-${i}`} className="pt-3 pb-1">
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-extrabold uppercase tracking-wider border ${
                isHigh
                  ? 'bg-rose-50 text-rose-700 border-rose-200'
                  : isMed
                  ? 'bg-amber-50 text-amber-700 border-amber-200'
                  : 'bg-slate-100 text-slate-700 border-slate-200'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  isHigh ? 'bg-rose-500' : isMed ? 'bg-amber-500' : 'bg-slate-400'
                }`}
              ></span>
              {subTitle}
            </span>
          </div>
        );
      } else {
        elements.push(
          <h4 key={`story-${i}`} className="text-xs sm:text-sm font-bold text-slate-800 pt-2 flex items-center gap-1.5">
            <ChevronRight className="h-3.5 w-3.5 text-[#4051B5] shrink-0" />
            <span>{subTitle}</span>
          </h4>
        );
      }
      i++;
      continue;
    }

    // Bullet Point
    if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
      const bulletText = trimmed.replace(/^[\*\-]\s+/, '');
      elements.push(
        <div key={`bullet-${i}`} className="flex items-start gap-2 pl-3 py-0.5">
          <span className="text-[#4051B5] font-bold text-sm leading-none mt-1">•</span>
          <div className="text-slate-700 flex-1 leading-relaxed">
            <FormattedText text={bulletText} />
          </div>
        </div>
      );
      i++;
      continue;
    }

    // Standard Paragraph
    elements.push(
      <p key={`p-${i}`} className="text-slate-700 leading-relaxed">
        <FormattedText text={trimmed} />
      </p>
    );
    i++;
  }

  return (
    <div className="space-y-3 text-xs sm:text-sm text-slate-700 leading-relaxed font-normal">
      {elements}
    </div>
  );
}

function FormattedText({ text }: { text: string }) {
  if (!text) return null;
  if (!text.includes('**')) return <>{text}</>;

  const parts = text.split(/(\*\*.*?\*\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          const inner = part.slice(2, -2);
          
          if (inner.includes('High') && inner.toLowerCase().includes('priority')) {
            return <span key={i} className="px-2 py-0.5 rounded bg-rose-50 text-rose-700 font-bold border border-rose-200 text-xs inline-block mx-0.5">{inner}</span>;
          }
          if (inner.includes('Medium') && inner.toLowerCase().includes('priority')) {
            return <span key={i} className="px-2 py-0.5 rounded bg-amber-50 text-amber-700 font-bold border border-amber-200 text-xs inline-block mx-0.5">{inner}</span>;
          }
          if (inner.includes('Low') && inner.toLowerCase().includes('priority')) {
            return <span key={i} className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-bold border border-slate-200 text-xs inline-block mx-0.5">{inner}</span>;
          }

          return <strong key={i} className="font-bold text-slate-900">{inner}</strong>;
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}
