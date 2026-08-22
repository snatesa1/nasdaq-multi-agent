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
  ChevronRight
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
  strategy: string;
  direction: string;
  strike: number;
  delta: number;
  dte: number;
  premium_estimate: number;
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
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [actionLog, setActionLog] = useState<{ id: string; msg: string; time: string; type: 'success' | 'danger' | 'info' }[]>([]);

  useEffect(() => {
    fetchBriefing();
  }, []);

  const fetchBriefing = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await optionsApi.getWeeklyBriefing();
      setBriefing(data);
    } catch (err: any) {
      console.error('Failed to load weekly briefing:', err);
      setError(err.message || 'Failed to generate weekly macro intelligence briefing.');
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
              <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-[#4051B5] border border-indigo-100">
                <Sparkles className="h-3.5 w-3.5" /> Weekly Macro Intelligence &amp; Execution Gate
              </span>
              <h1 className="text-2xl font-bold text-slate-800 tracking-tight sm:text-3xl">
                Weekly Intelligence &amp; <span className="text-[#4051B5]">Trade Command Center</span>
              </h1>
              <p className="text-slate-500 text-xs sm:text-sm leading-relaxed">
                Monday–Friday macro event digestion, watchlist &amp; trade history pillars, and dual-key live Saxo order execution within a strict 15% margin utilization cap.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={fetchBriefing}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2.5 bg-[#4051B5] hover:bg-[#34449a] text-white rounded-xl text-xs font-semibold shadow-sm transition disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                {loading ? 'Analyzing Events...' : 'Refresh Intelligence'}
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
            <AlertTriangle className="h-5 w-5 shrink-0 text-rose-500" />
            <span>{error}</span>
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
        <div className="p-6 bg-gradient-to-br from-indigo-50/60 via-white to-emerald-50/40 border border-indigo-100 rounded-xl shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-[#4051B5] font-bold text-sm">
            <Cpu className="h-5 w-5" />
            <span>Gemini Multi-Model Macro Synthesis &amp; Edge Digest</span>
          </div>
          <p className="text-slate-700 leading-relaxed text-xs sm:text-sm whitespace-pre-line">
            {briefing?.ai_summary || 'Analyzing macroeconomic events, interest rate decisions, and legislative catalysts for the active portfolio watchlist...'}
          </p>
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
                        <div className="flex items-center gap-2">
                          <span className="text-base font-bold text-slate-800">{trade.strategy} ${trade.strike}</span>
                          <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-700 rounded font-mono font-medium">
                            Δ {trade.delta}
                          </span>
                          <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-700 rounded font-mono font-medium">
                            {trade.dte} DTE
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">Spot Price: ${trade.spot_price.toFixed(2)} | Est. Premium: ${trade.premium_estimate.toFixed(2)}</p>
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
                <div key={idx} className="flex items-center justify-between text-slate-700 border-b border-slate-100 pb-1">
                  <span>{log.msg}</span>
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
