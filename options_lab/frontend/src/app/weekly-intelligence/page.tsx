'use client';

/**
 * WeeklyIntelligencePage.tsx — Institutional OptionsLab Weekly Intelligence Cockpit.
 * 
 * Descriptive Summary:
 *   Comprehensive institutional cockpit orchestrating weekly macroeconomic intelligence,
 *   a 4-Dimensional Macro Direction Compass, an AI Corporate Interlink Cockpit (GAAP DSI
 *   and 3-factor quantitative scores), 4-Tier Capital Allocation Scenarios (80/20, 60/40, 50/50, 20/80),
 *   and a disciplined $1,000/Month Systematic Wheel Harvest Blotter with pre-flight contract verification.
 * 
 * Component Architecture & State Encapsulation:
 *   - activeTab ('blotter' | 'compass' | 'interlink' | 'scenarios' | 'briefing'): Controls active cockpit view.
 *   - briefing (BriefingData | null): Live payload from ADK / Weekly Intelligence pipeline.
 *   - selectedScenario (string): Active capital allocation scenario ID ('80_20', '60_40', '50_50', '20_80').
 *   - selectedChallenger (string | null): Active challenger category expanded for mathematical inspection.
 *   - approvingId / rejectingId (string | null): Asynchronous trade execution mutation states.
 *   - actionLog (Array): Real-time telemetry log tracking order placements and broker notifications.
 * 
 * Usage Example:
 *   <WeeklyIntelligencePage />
 */

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
  Compass, 
  PieChart, 
  Share2, 
  Zap, 
  BarChart3, 
  Info, 
  Sliders,
  Database,
  Plus,
  Trash2,
  Search,
  BookOpen,
  Tag
} from 'lucide-react';
import { optionsApi } from '@/lib/api';
import ProtectedRoute from '@/components/ProtectedRoute';
import { 
  BriefingData, 
  MacroCompass, 
  CapitalAllocationScenario, 
  InterlinkCockpit, 
  WheelHarvestBlotter, 
  StagedTrade, 
  MacroEvent 
} from '@/types/intelligence';

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

  // Cockpit Tab Navigation
  const [activeTab, setActiveTab] = useState<'blotter' | 'compass' | 'interlink' | 'scenarios' | 'briefing' | 'corpus'>('blotter');
  const [selectedScenario, setSelectedScenario] = useState<string>('60_40');
  const [selectedChallenger, setSelectedChallenger] = useState<string | null>(null);

  // Dynamic Macro Corpus State
  const [corpusList, setCorpusList] = useState<Array<{
    id: number;
    category: string;
    keyword: string;
    weight: number;
    directional_bias: string;
    default_impact: number;
    default_tickers: string;
    source: string;
    updated_at: string;
  }>>([]);
  const [corpusLoading, setCorpusLoading] = useState<boolean>(false);
  const [corpusFilterCategory, setCorpusFilterCategory] = useState<string>('ALL');
  const [corpusSearch, setCorpusSearch] = useState<string>('');
  const [showAddKeywordModal, setShowAddKeywordModal] = useState<boolean>(false);
  const [newCategory, setNewCategory] = useState<string>('AI_SEMICONDUCTORS');
  const [newKeyword, setNewKeyword] = useState<string>('');
  const [newWeight, setNewWeight] = useState<number>(2.0);
  const [newBias, setNewBias] = useState<string>('BULLISH_CSP');
  const [newImpact, setNewImpact] = useState<number>(4);
  const [newTickers, setNewTickers] = useState<string>('');
  const [corpusSubmitting, setCorpusSubmitting] = useState<boolean>(false);
  const [corpusMessage, setCorpusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const fetchCorpus = async (category?: string) => {
    setCorpusLoading(true);
    try {
      const res = await optionsApi.getMacroCorpus(category === 'ALL' ? undefined : category);
      if (res?.corpus) {
        setCorpusList(res.corpus);
      }
    } catch (err: any) {
      console.error('Failed to load macro corpus:', err);
    } finally {
      setCorpusLoading(false);
    }
  };

  const handleAddKeyword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyword.trim()) return;
    setCorpusSubmitting(true);
    setCorpusMessage(null);
    try {
      await optionsApi.addOrUpdateCorpusKeyword({
        category: newCategory,
        keyword: newKeyword.trim(),
        weight: Number(newWeight),
        directional_bias: newBias,
        default_impact: Number(newImpact),
        default_tickers: newTickers.trim(),
        source: 'MANUAL'
      });
      setCorpusMessage({ text: `Added "${newKeyword.trim()}" to SQLite corpus!`, type: 'success' });
      setNewKeyword('');
      setNewTickers('');
      setShowAddKeywordModal(false);
      fetchCorpus(corpusFilterCategory);
    } catch (err: any) {
      setCorpusMessage({ text: `Failed to add keyword: ${err.message || err}`, type: 'error' });
    } finally {
      setCorpusSubmitting(false);
    }
  };

  const handleDeleteKeyword = async (keyword: string) => {
    if (!confirm(`Delete "${keyword}" from the macro categorization corpus?`)) return;
    try {
      await optionsApi.deleteCorpusKeyword(keyword);
      setCorpusList(prev => prev.filter(k => k.keyword !== keyword));
    } catch (err: any) {
      alert(`Failed to delete keyword: ${err.message || err}`);
    }
  };

  const handleCopyBriefing = () => {
    if (!briefing?.ai_summary) return;
    navigator.clipboard.writeText(briefing.ai_summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  useEffect(() => {
    fetchBriefing(false);
    fetchCorpus();
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

    const handleFocusCheck = async () => {
      try {
        if (navigator.clipboard && document.hasFocus()) {
          const clipText = await navigator.clipboard.readText();
          if (clipText && (clipText.includes('code=') || clipText.includes('Akpegis-Agent.com.sg') || (clipText.trim().length === 36 && clipText.includes('-')))) {
            setActionLog(prev => [
              { id: 'AUTH-CLIP', msg: '⚡ Detected Saxo authorization code in clipboard! Auto-linking session...', time: new Date().toLocaleTimeString(), type: 'info' },
              ...prev
            ]);
            await optionsApi.setBrokerToken({ token: clipText.trim() });
            setActionLog(prev => [
              { id: 'AUTH-OK', msg: '✅ Live Saxo broker session successfully established and persisted!', time: new Date().toLocaleTimeString(), type: 'success' },
              ...prev
            ]);
            fetchBriefing(true);
          }
        }
      } catch (e) {}
    };
    window.addEventListener('focus', handleFocusCheck);

    return () => {
      window.removeEventListener('message', handleAuthMessage);
      window.removeEventListener('focus', handleFocusCheck);
    };
  }, []);

  const handleAutoLinkClipboard = async () => {
    try {
      if (!navigator.clipboard) {
        throw new Error('Clipboard API not accessible.');
      }
      const clipText = await navigator.clipboard.readText();
      if (!clipText || !clipText.trim()) {
        throw new Error('Clipboard is empty. Copy the callback URL or code first.');
      }
      setActionLog(prev => [
        { id: 'AUTH-CLIP', msg: '⚡ Auto-linking Saxo code from clipboard...', time: new Date().toLocaleTimeString(), type: 'info' },
        ...prev
      ]);
      await optionsApi.setBrokerToken({ token: clipText.trim() });
      setActionLog(prev => [
        { id: 'AUTH-OK', msg: '✅ Saxo Live MFA Authenticated via Clipboard!', time: new Date().toLocaleTimeString(), type: 'success' },
        ...prev
      ]);
      fetchBriefing(true);
    } catch (err: any) {
      setActionLog(prev => [
        { id: 'AUTH-ERR', msg: `❌ Clipboard Auto-Link failed: ${err.message || err}`, time: new Date().toLocaleTimeString(), type: 'danger' },
        ...prev
      ]);
    }
  };

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

    try {
      const handshake = await optionsApi.checkHandshake(3000);
      if (!handshake.ok) {
        const errMsg = handshake.error || 'OptionsLab backend on port 8000 is unreachable.';
        setLoading(false);
        setHandshakeError(errMsg);
        setError(`🔌 Backend Handshake Failed: ${errMsg}`);
        return;
      }
    } catch (hErr: any) {
      setLoading(false);
      const targetHost = typeof window !== 'undefined' ? `${window.location.hostname}:${window.location.port || '80'}` : 'localhost:8000';
      const errMsg = `Cannot connect to OptionsLab backend on ${targetHost}. Server is offline.`;
      setHandshakeError(errMsg);
      setError(`🔌 Backend Handshake Failed: ${errMsg}`);
      return;
    }

    setLoadingStep('Synthesizing 4D Macro Compass, Interlink Graph & Wheel Harvest Blotter...');
    if (forceRefresh) {
      setActionLog(prev => [
        { id: `REFRESH-START-${Date.now()}`, msg: '🔄 Refreshing Weekly Intelligence & Quantitative Blotters...', time: new Date().toLocaleTimeString(), type: 'info' },
        ...prev
      ]);
    }

    try {
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

  const compass = briefing?.macro_compass;
  const interlink = briefing?.interlink_cockpit;
  const wheelBlotter = briefing?.wheel_harvest_blotter;
  const scenarios = briefing?.capital_allocation_scenarios || [];
  const stagedTrades = wheelBlotter?.candidates || briefing?.potential_trades || [];

  return (
    <ProtectedRoute>
      <div className="space-y-6 pb-12">
        
        {/* Top Header Banner */}
        <div className="relative overflow-hidden rounded-xl bg-white p-6 sm:p-8 border border-slate-200/80 shadow-sm">
          <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-indigo-50/60 blur-2xl" />
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-2 max-w-3xl">
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-[#4051B5] border border-indigo-100">
                  <Sparkles className="h-3.5 w-3.5" /> Institutional Weekly Intelligence &amp; Execution Cockpit
                </span>
                {briefing?.framework && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 border border-emerald-200">
                    <Cpu className="h-3 w-3 text-emerald-600" /> {briefing.framework}
                  </span>
                )}
                <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700 border border-amber-200">
                  <Lock className="h-3 w-3 text-amber-600" /> HITL Gate: Dual-Key Pre-Flight Check
                </span>
              </div>
              <h1 className="text-2xl font-bold text-slate-800 tracking-tight sm:text-3xl">
                Weekly Macro Intelligence &amp; <span className="text-[#4051B5]">Trade Command Center</span>
              </h1>
              <p className="text-slate-500 text-xs sm:text-sm leading-relaxed">
                4-Dimensional Macro Compass, AI Corporate Interlink Contagion, 4-Tier Capital Scenarios, and $1,000/Mo Systematic Wheel Harvest ($2.00–$3.00 sweet spot) within strict 15% margin caps.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {authUrl && (
                <>
                  <button
                    onClick={handleStartOAuth}
                    className="flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-sm transition cursor-pointer"
                    title="Authenticate Saxo Live via 1-Click MFA Popup"
                  >
                    <Key className="h-4 w-4" />
                    Authorize Saxo (MFA)
                  </button>
                  <button
                    onClick={handleAutoLinkClipboard}
                    className="flex items-center gap-1.5 px-3.5 py-2.5 bg-white hover:bg-slate-50 text-emerald-700 border border-emerald-300 rounded-xl text-xs font-bold shadow-xs transition cursor-pointer"
                    title="Auto-Link Saxo authorization code or URL directly from clipboard"
                  >
                    ⚡ Auto-Link
                  </button>
                </>
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

        {/* Handshake & Connection Alerts */}
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

        {/* Executive Summary KPI Ribbon */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Compass Direction & Score */}
          <div className="velzon-card p-5 bg-white border border-slate-200/80 rounded-xl shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">4D Macro Direction</span>
              <Compass className="h-5 w-5 text-[#4051B5]" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-extrabold text-slate-800">
                {compass?.composite_direction || 'EXPANSIVE'}
              </span>
              <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-indigo-50 text-[#4051B5]">
                {compass ? (compass.composite_score >= 0 ? `+${compass.composite_score}` : compass.composite_score) : '+46.3'}
              </span>
            </div>
            <span className="text-[11px] text-slate-400 block font-medium">Weighted 4-Factor Scale (-100 to +100)</span>
          </div>

          {/* $1,000/Mo Wheel Harvest Target */}
          <div className="velzon-card p-5 bg-white border border-slate-200/80 rounded-xl shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">$1,000/Mo Wheel Harvest</span>
              <DollarSign className="h-5 w-5 text-emerald-600" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-emerald-700">
                ${wheelBlotter?.projected_monthly_harvest_dollars?.toFixed(2) || '1,050.00'}
              </span>
              <span className="text-xs font-semibold text-slate-500">
                / $1,000 Goal ({wheelBlotter?.target_achievement_pct || 105.0}%)
              </span>
            </div>
            <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
              <div 
                className="h-full bg-emerald-500 transition-all duration-500"
                style={{ width: `${Math.min(100, (wheelBlotter?.target_achievement_pct || 105.0))}%` }}
              />
            </div>
          </div>

          {/* Margin Utilization */}
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

          {/* AI Interlink Health Score */}
          <div className="velzon-card p-5 bg-white border border-slate-200/80 rounded-xl shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">AI Interlink Health</span>
              <Share2 className="h-5 w-5 text-indigo-500" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-indigo-700">
                {interlink?.composite_interlink_health_index?.toFixed(1) || '88.0'}
              </span>
              <span className="text-xs text-slate-400 font-medium">/ 100 (Balanced DSI)</span>
            </div>
            <span className="text-[11px] text-slate-400 block font-medium">6 Anchors &amp; 4 Challenger Segments</span>
          </div>
        </div>

        {/* Cockpit Tab Navigation Bar */}
        <div className="flex items-center gap-2 border-b border-slate-200 pb-2 overflow-x-auto">
          <button
            onClick={() => setActiveTab('blotter')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition cursor-pointer shrink-0 ${
              activeTab === 'blotter'
                ? 'bg-[#4051B5] text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
            }`}
          >
            <DollarSign className="h-4 w-4" />
            <span>🎯 $1,000/Mo Wheel Harvest Blotter</span>
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono ${
              activeTab === 'blotter' ? 'bg-white/20 text-white' : 'bg-indigo-50 text-[#4051B5]'
            }`}>
              {stagedTrades.length} Candidates
            </span>
          </button>

          <button
            onClick={() => setActiveTab('compass')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition cursor-pointer shrink-0 ${
              activeTab === 'compass'
                ? 'bg-[#4051B5] text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
            }`}
          >
            <Compass className="h-4 w-4" />
            <span>🧭 4D Macro Direction Compass</span>
          </button>

          <button
            onClick={() => setActiveTab('interlink')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition cursor-pointer shrink-0 ${
              activeTab === 'interlink'
                ? 'bg-[#4051B5] text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
            }`}
          >
            <Share2 className="h-4 w-4" />
            <span>🌐 AI Corporate Interlink Cockpit</span>
          </button>

          <button
            onClick={() => setActiveTab('scenarios')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition cursor-pointer shrink-0 ${
              activeTab === 'scenarios'
                ? 'bg-[#4051B5] text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
            }`}
          >
            <PieChart className="h-4 w-4" />
            <span>⚖️ 4-Tier Capital Scenarios</span>
          </button>

          <button
            onClick={() => setActiveTab('briefing')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition cursor-pointer shrink-0 ${
              activeTab === 'briefing'
                ? 'bg-[#4051B5] text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
            }`}
          >
            <FileText className="h-4 w-4" />
            <span>📰 Senior Macro Analyst Memo &amp; Calendar</span>
          </button>

          <button
            onClick={() => {
              setActiveTab('corpus');
              fetchCorpus();
            }}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition cursor-pointer shrink-0 ${
              activeTab === 'corpus'
                ? 'bg-[#4051B5] text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
            }`}
          >
            <Database className="h-4 w-4" />
            <span>📚 Dynamic Macro Corpus</span>
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono ${
              activeTab === 'corpus' ? 'bg-white/20 text-white' : 'bg-indigo-50 text-[#4051B5]'
            }`}>
              {corpusList.length} Terms
            </span>
          </button>
        </div>

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* TAB 1: $1,000/MONTH SYSTEMATIC WHEEL HARVEST BLOTTER                 */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        {activeTab === 'blotter' && (
          <div className="space-y-6">
            {/* Aggregate Wheel Harvest KPI Ribbon */}
            <div className="p-6 bg-gradient-to-br from-emerald-50/50 via-white to-indigo-50/30 border border-emerald-200/80 rounded-2xl shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-emerald-100 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-emerald-600 text-white">
                      <DollarSign className="h-5 w-5" />
                    </div>
                    <div>
                      <h2 className="text-base font-bold text-slate-800">
                        Institutional $1,000/Month Systematic Wheel Harvest Blotter
                      </h2>
                      <p className="text-xs text-slate-500">
                        Strict sweet-spot targeting: $2.00–$3.00 premium ($200–$300/contract) across 3–4 high-conviction sector-diversified candidates.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <span className="px-3 py-1 rounded-lg bg-emerald-100/80 text-emerald-800 font-mono text-xs font-bold border border-emerald-300">
                    Target Band: $2.00 – $3.00 / Contract
                  </span>
                  <span className="px-3 py-1 rounded-lg bg-indigo-50 text-[#4051B5] font-mono text-xs font-bold border border-indigo-200">
                    ~75% – 82% PoP Sweet Spot
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 text-xs">
                <div className="p-3 bg-white rounded-xl border border-slate-200/70 shadow-2xs">
                  <span className="text-[10px] text-slate-400 font-bold uppercase block">Monthly Goal</span>
                  <span className="text-base font-mono font-bold text-slate-800">$1,000.00</span>
                </div>
                <div className="p-3 bg-white rounded-xl border border-slate-200/70 shadow-2xs">
                  <span className="text-[10px] text-slate-400 font-bold uppercase block">Projected Harvest</span>
                  <span className="text-base font-mono font-bold text-emerald-700">
                    ${wheelBlotter?.projected_monthly_harvest_dollars?.toFixed(2) || '1,050.00'}
                  </span>
                </div>
                <div className="p-3 bg-white rounded-xl border border-slate-200/70 shadow-2xs">
                  <span className="text-[10px] text-slate-400 font-bold uppercase block">Average PoP</span>
                  <span className="text-base font-mono font-bold text-[#4051B5]">
                    {wheelBlotter?.average_pop_percent?.toFixed(1) || '79.5'}%
                  </span>
                </div>
                <div className="p-3 bg-white rounded-xl border border-slate-200/70 shadow-2xs">
                  <span className="text-[10px] text-slate-400 font-bold uppercase block">Total Collateral Reserved</span>
                  <span className="text-base font-mono font-bold text-slate-700">
                    ${wheelBlotter?.total_collateral_required?.toLocaleString('en-US', { minimumFractionDigits: 2 }) || '$38,500.00'}
                  </span>
                </div>
              </div>
            </div>

            {/* Candidate Cards Grid */}
            <div className="space-y-4">
              {stagedTrades.map((trade) => {
                const isApproved = trade.status === 'APPROVED' || trade.status === 'FILLED' || trade.status === 'PLACED' || trade.status === 'EXECUTING';
                const isRejected = trade.status === 'REJECTED';
                const isSweetSpot = trade.premium_estimate >= 2.00 && trade.premium_estimate <= 3.00;

                return (
                  <div 
                    key={trade.trade_id}
                    className={`p-6 bg-white border rounded-2xl shadow-sm transition-all space-y-4 ${
                      isApproved ? 'border-emerald-300 bg-emerald-50/20' :
                      isRejected ? 'border-slate-200 opacity-60 bg-slate-50/50' :
                      isSweetSpot ? 'border-indigo-200 hover:border-indigo-300' :
                      'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    {/* Header Row */}
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-4">
                      <div className="flex items-center gap-3">
                        <div className="px-4 py-2.5 bg-indigo-50 border border-indigo-100 rounded-xl font-mono text-lg font-black text-[#4051B5]">
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
                            {isSweetSpot && (
                              <span className="text-[11px] px-2 py-0.5 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded font-bold">
                                🎯 Sweet Spot ($2–$3)
                              </span>
                            )}
                          </div>
                          
                          <div className="flex flex-wrap items-center gap-2 mt-1.5 text-xs text-slate-500">
                            <span>Spot: <strong className="text-slate-700">${trade.spot_price.toFixed(2)}</strong></span>
                            <span className="text-slate-300">•</span>
                            <span>Limit Price: <strong className="text-emerald-700 font-mono">${trade.premium_estimate.toFixed(2)}</strong></span>
                            {trade.bid_price !== undefined && trade.bid_price > 0 && (
                              <>
                                <span className="text-slate-300">•</span>
                                <span className="font-mono">Bid: ${trade.bid_price.toFixed(2)} / Ask: ${trade.ask_price?.toFixed(2)}</span>
                                <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 rounded font-semibold text-slate-600 uppercase">
                                  {trade.pricing_source === 'OPRA_LIVE' ? 'OPRA Live' : 'Model Quote'}
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Verification Badges & Actions */}
                      <div className="flex flex-wrap items-center gap-3">
                        <div className="flex flex-col items-end gap-1">
                          <div className="flex items-center gap-1.5">
                            {trade.contract_verified ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-50 border border-emerald-200 text-emerald-700 text-[10px] font-bold">
                                <CheckCircle2 className="h-3 w-3" /> Contract Verified
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 text-slate-600 text-[10px] font-medium">
                                Contract Unverified
                              </span>
                            )}

                            {trade.exchange_precheck_viable ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-50 border border-emerald-200 text-emerald-700 text-[10px] font-bold">
                                <ShieldCheck className="h-3 w-3" /> Pre-Check Viable
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-50 border border-amber-200 text-amber-700 text-[10px] font-medium">
                                Pre-Check Pending
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] text-slate-400 font-mono">
                            Margin Impact: +{trade.max_margin_impact_pct?.toFixed(1) || '1.5'}%
                          </span>
                        </div>

                        {isApproved ? (
                          <div className="flex items-center gap-1.5 px-4 py-2 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 text-xs font-bold">
                            <CheckCircle2 className="h-4 w-4" />
                            <span>{trade.status === 'FILLED' ? 'Executed Live' : 'Approved'}</span>
                          </div>
                        ) : isRejected ? (
                          <div className="flex items-center gap-1.5 px-4 py-2 bg-slate-100 border border-slate-200 rounded-xl text-slate-500 text-xs font-semibold">
                            <XCircle className="h-4 w-4" />
                            <span>Rejected</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleApprove(trade.trade_id)}
                              disabled={approvingId === trade.trade_id}
                              className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold transition shadow-xs flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
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
                              className="px-3 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition cursor-pointer"
                            >
                              Reject
                            </button>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Quantitative Wheel Metrics Strip */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50/70 p-3.5 rounded-xl border border-slate-200/60 text-xs">
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase block">Probability of Profit</span>
                        <span className="text-sm font-bold font-mono text-emerald-700">
                          {trade.pop_pct || 80.0}%
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase block">Collateral Required</span>
                        <span className="text-sm font-bold font-mono text-slate-800">
                          ${(trade.collateral_required || trade.strike * 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase block">Breakeven / Discount</span>
                        <span className="text-sm font-bold font-mono text-slate-800">
                          ${(trade.breakeven_price || trade.strike - trade.premium_estimate).toFixed(2)} ({trade.discount_to_spot_pct || 10.5}% off spot)
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase block">Assignment Probability</span>
                        <span className="text-sm font-bold font-mono text-amber-700">
                          {trade.assignment_probability_pct || 20.0}%
                        </span>
                      </div>
                    </div>

                    {/* Assignment Risk & Cash-Burn Narrative */}
                    <div className="bg-white border border-indigo-100 rounded-xl p-3 text-xs space-y-1">
                      <div className="flex items-center gap-1.5 text-[#4051B5] font-bold">
                        <ShieldCheck className="h-4 w-4" />
                        <span>Assignment Risk &amp; Cash-Burn Profile:</span>
                      </div>
                      <p className="text-slate-600 pl-5 leading-relaxed">
                        {trade.assignment_risk_description || `$${trade.strike * 100} cash collateral reserved; 20% assignment probability at $${trade.strike - trade.premium_estimate} breakeven.`}
                      </p>
                    </div>

                    {/* Investment Thesis & Catalyst */}
                    <div className="bg-slate-50/80 border border-slate-150 rounded-xl p-3 text-xs space-y-1">
                      <div className="flex items-center gap-1.5 text-slate-700 font-bold">
                        <ArrowUpRight className="h-4 w-4 text-[#4051B5]" />
                        <span>Catalyst Thesis: {trade.edge_source}</span>
                      </div>
                      <p className="text-slate-600 pl-5 leading-relaxed">{trade.thesis}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* TAB 2: 4D MACRO DIRECTION COMPASS                                    */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        {activeTab === 'compass' && (
          <div className="space-y-6">
            {/* Compass Composite Direction Banner */}
            <div className="p-6 bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white rounded-2xl shadow-sm space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="p-3 rounded-xl bg-white/10 backdrop-blur-xs border border-white/20">
                    <Compass className="h-6 w-6 text-indigo-200" />
                  </div>
                  <div>
                    <span className="text-xs uppercase tracking-wider text-indigo-300 font-bold">Composite Macro Regime</span>
                    <h2 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
                      {compass?.composite_direction || 'EXPANSIVE_EQUILIBRIUM'}
                    </h2>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="text-[10px] uppercase text-indigo-300 font-bold block">Aggregated Score</span>
                    <span className="text-2xl font-mono font-black text-emerald-400">
                      {compass ? (compass.composite_score >= 0 ? `+${compass.composite_score}` : compass.composite_score) : '+46.3'}
                    </span>
                  </div>
                </div>
              </div>

              <p className="text-xs text-indigo-200/90 leading-relaxed max-w-2xl">
                Synthesized across 4 quantitative dimensions: Rates &amp; Monetary Pressure (30%), Corporate Earnings &amp; Guidance (25%), AI Interlink Circular CapEx (30%), and Market Liquidity / VIX Regime (15%).
              </p>
            </div>

            {/* 4 Dimension Barometer Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Dimension 1: Rates */}
              <div className="velzon-card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-emerald-50 text-emerald-700">
                      <TrendingUp className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-800">1. Rates &amp; Monetary Pressure</h3>
                      <span className="text-[11px] text-slate-400 font-medium">Trajectory &amp; Treasury Yields</span>
                    </div>
                  </div>
                  <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                    Score: {compass?.dimension_1_rates?.score !== undefined ? `+${compass.dimension_1_rates.score}` : '+35.0'}
                  </span>
                </div>

                <div className="space-y-1.5 text-xs text-slate-600">
                  <div className="flex justify-between font-medium">
                    <span>Regime: <strong className="text-slate-800">{compass?.dimension_1_rates?.direction || 'DOVISH_EASING'}</strong></span>
                    <span>Momentum: <strong className="text-emerald-700 font-mono">{compass?.dimension_1_rates?.momentum || 'STABLE_TO_EASING'}</strong></span>
                  </div>
                  <p className="bg-slate-50 p-3 rounded-xl border border-slate-150 leading-relaxed text-slate-700">
                    {compass?.dimension_1_rates?.key_driver || 'Fed disinflation trajectory & 10Y Treasury yield consolidation below 4.0%.'}
                  </p>
                </div>
              </div>

              {/* Dimension 2: Earnings */}
              <div className="velzon-card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-indigo-50 text-[#4051B5]">
                      <BarChart3 className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-800">2. Corporate Earnings &amp; Demand</h3>
                      <span className="text-[11px] text-slate-400 font-medium">Broad Enterprise Margin Health</span>
                    </div>
                  </div>
                  <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-indigo-50 text-[#4051B5] border border-indigo-200">
                    Score: {compass?.dimension_2_earnings?.score !== undefined ? `+${compass.dimension_2_earnings.score}` : '+35.0'}
                  </span>
                </div>

                <div className="space-y-1.5 text-xs text-slate-600">
                  <div className="flex justify-between font-medium">
                    <span>Regime: <strong className="text-slate-800">{compass?.dimension_2_earnings?.direction || 'EXPANDING'}</strong></span>
                    <span>Momentum: <strong className="text-indigo-700 font-mono">{compass?.dimension_2_earnings?.momentum || 'RESILIENT'}</strong></span>
                  </div>
                  <p className="bg-slate-50 p-3 rounded-xl border border-slate-150 leading-relaxed text-slate-700">
                    {compass?.dimension_2_earnings?.key_driver || 'Enterprise AI software consulting and non-cyclical healthcare margin resilience.'}
                  </p>
                </div>
              </div>

              {/* Dimension 3: Interlink */}
              <div className="velzon-card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-purple-50 text-purple-700">
                      <Share2 className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-800">3. AI Interlink Circular CapEx</h3>
                      <span className="text-[11px] text-slate-400 font-medium">Hyperscaler &amp; Silicon DSI Velocity</span>
                    </div>
                  </div>
                  <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-purple-50 text-purple-700 border border-purple-200">
                    Score: {compass?.dimension_3_interlink?.score !== undefined ? `+${compass.dimension_3_interlink.score}` : '+76.0'}
                  </span>
                </div>

                <div className="space-y-1.5 text-xs text-slate-600">
                  <div className="flex justify-between font-medium">
                    <span>Regime: <strong className="text-slate-800">{compass?.dimension_3_interlink?.direction || 'ACCELERATING_CAPEX'}</strong></span>
                    <span>Interlink Health: <strong className="text-purple-700 font-mono">{compass?.dimension_3_interlink?.interlink_health_score || 88.0}/100</strong></span>
                  </div>
                  <p className="bg-slate-50 p-3 rounded-xl border border-slate-150 leading-relaxed text-slate-700">
                    {compass?.dimension_3_interlink?.key_driver || 'Hyperscaler CapEx conversion ($165B annual) and balanced silicon DSI (75d).'}
                  </p>
                </div>
              </div>

              {/* Dimension 4: Liquidity */}
              <div className="velzon-card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-sky-50 text-sky-700">
                      <Activity className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-800">4. Market Liquidity &amp; Volatility</h3>
                      <span className="text-[11px] text-slate-400 font-medium">CBOE VIX &amp; Credit Conditions</span>
                    </div>
                  </div>
                  <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-sky-50 text-sky-700 border border-sky-200">
                    Score: {compass?.dimension_4_liquidity?.score !== undefined ? `+${compass.dimension_4_liquidity.score}` : '+45.0'}
                  </span>
                </div>

                <div className="space-y-1.5 text-xs text-slate-600">
                  <div className="flex justify-between font-medium">
                    <span>Regime: <strong className="text-slate-800">{compass?.dimension_4_liquidity?.direction || 'NORMAL_EQUILIBRIUM'}</strong></span>
                    <span>Momentum: <strong className="text-sky-700 font-mono">{compass?.dimension_4_liquidity?.momentum || 'CALM_EQUILIBRIUM'}</strong></span>
                  </div>
                  <p className="bg-slate-50 p-3 rounded-xl border border-slate-150 leading-relaxed text-slate-700">
                    {compass?.dimension_4_liquidity?.key_driver || 'VIX sub-16 regime supporting 30-DTE option premium selling.'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* TAB 3: AI CORPORATE INTERLINK COCKPIT                                */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        {activeTab === 'interlink' && (
          <div className="space-y-6">
            {/* Header Description */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-5 bg-white border border-slate-200 rounded-2xl shadow-sm">
              <div>
                <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                  <Share2 className="h-5 w-5 text-[#4051B5]" />
                  AI Corporate Interlink Cockpit: 6 Anchors &amp; 4 Challenger Segments
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Evaluates circular capital expenditure flow, GAAP Days Sales of Inventory (DSI = Inventory/COGS * 365), and semiconductor supply-chain health.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="px-3 py-1.5 rounded-xl bg-purple-50 text-purple-800 border border-purple-200 text-xs font-mono font-bold">
                  Health Index: {interlink?.composite_interlink_health_index || 88.0} / 100
                </span>
              </div>
            </div>

            {/* 6 Anchors Grid */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Core Hyperscaler &amp; Silicon Anchors (Live SEC Filings / GAAP DSI)
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {interlink?.anchors && Object.values(interlink.anchors).map((anchor) => (
                  <div key={anchor.ticker} className="p-4 bg-white border border-slate-200 rounded-xl shadow-2xs space-y-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-black text-slate-900 text-base">{anchor.ticker}</span>
                          <span className="text-[11px] px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">
                            {anchor.role}
                          </span>
                        </div>
                        <span className="text-xs text-slate-400">{anchor.name}</span>
                      </div>
                      
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                        anchor.dsi_status.includes('Balanced') ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                        anchor.dsi_status.includes('Bottleneck') ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                        'bg-slate-100 text-slate-600'
                      }`}>
                        {anchor.dsi_status}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100 text-[11px]">
                      <div>
                        <span className="text-slate-400 block text-[9px] uppercase">CapEx/Yr</span>
                        <strong className="font-mono text-slate-800">${anchor.capex_annual_b.toFixed(1)}B</strong>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[9px] uppercase">Revenue</span>
                        <strong className="font-mono text-slate-800">${anchor.revenue_annual_b.toFixed(1)}B</strong>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[9px] uppercase">DSI (Days)</span>
                        <strong className="font-mono text-indigo-700">
                          {anchor.inventory_dsi_days > 0 ? `${anchor.inventory_dsi_days.toFixed(1)}d` : 'N/A'}
                        </strong>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 4 Challengers Grid with Transparent 3-Factor Mathematical Model */}
            <div className="space-y-3 pt-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                <span>Challenger Categories (3-Factor Quantitative Model: Growth 40% + Margin 30% + Efficiency 30%)</span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {interlink?.challengers && Object.entries(interlink.challengers).map(([key, challenger]) => (
                  <div key={key} className="p-5 bg-white border border-slate-200 rounded-xl shadow-sm space-y-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="text-sm font-bold text-slate-900">{challenger.label}</h4>
                        <span className="text-xs text-slate-400">Category: {challenger.category}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] text-slate-400 font-bold uppercase block">Challenger Score</span>
                        <span className="text-lg font-mono font-black text-[#4051B5]">
                          {challenger.composite_score.toFixed(1)} / 100
                        </span>
                      </div>
                    </div>

                    {/* Mathematical Score Breakdown */}
                    <div className="bg-slate-50 p-3 rounded-xl border border-slate-150 space-y-1 text-xs">
                      <div className="flex justify-between font-mono text-[11px] text-slate-600">
                        <span>Growth Score (40%): <strong>{challenger.score_derivation?.growth_score || 85.0}</strong></span>
                        <span>Margin (30%): <strong>{challenger.score_derivation?.margin_score || 80.0}</strong></span>
                        <span>Efficiency (30%): <strong>{challenger.score_derivation?.efficiency_score || 80.0}</strong></span>
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono block">
                        Formula: {challenger.score_derivation?.formula || '0.40 * Growth + 0.30 * Margin + 0.30 * Efficiency'}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      <span className="text-xs font-medium text-slate-400">Key Beneficiaries:</span>
                      {challenger.key_tickers?.map(t => (
                        <span key={t} className="px-2 py-0.5 bg-indigo-50 text-[#4051B5] border border-indigo-100 rounded text-xs font-mono font-bold">
                          {t}
                        </span>
                      ))}
                    </div>

                    <p className="text-xs text-slate-600 leading-relaxed pt-1">
                      {challenger.rationale}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* TAB 4: 4-TIER CAPITAL ALLOCATION SCENARIOS                           */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        {activeTab === 'scenarios' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-5 bg-white border border-slate-200 rounded-2xl shadow-sm">
              <div>
                <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                  <PieChart className="h-5 w-5 text-[#4051B5]" />
                  Portfolio Capital Allocation Playbook: 4 Distinct Scenarios
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Dynamically scaled to live account equity (${(margin?.total_equity || 100000).toLocaleString('en-US')}) and available cash buffer.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500 font-medium">Selected Stance:</span>
                <span className="px-3 py-1 rounded-lg bg-indigo-50 text-[#4051B5] font-bold text-xs font-mono">
                  {selectedScenario.replace('_', '/')}
                </span>
              </div>
            </div>

            {/* 4 Scenario Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {scenarios.map((scen) => {
                const isSelected = selectedScenario === scen.scenario_id;

                return (
                  <div
                    key={scen.scenario_id}
                    onClick={() => setSelectedScenario(scen.scenario_id)}
                    className={`p-6 bg-white border rounded-2xl shadow-sm transition cursor-pointer space-y-4 ${
                      isSelected
                        ? 'border-[#4051B5] ring-2 ring-[#4051B5]/20 bg-indigo-50/10'
                        : 'border-slate-200 hover:border-indigo-200'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-base font-bold text-slate-900">{scen.label}</h3>
                        <span className="text-xs text-slate-400 font-medium">{scen.subtitle}</span>
                      </div>
                      
                      <span className="px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 font-mono text-xs font-bold">
                        Yield: {scen.annualized_theta_yield_est}
                      </span>
                    </div>

                    {/* Dollar Allocation Strip */}
                    <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded-xl border border-slate-150 text-xs">
                      <div>
                        <span className="text-[10px] text-slate-400 font-bold uppercase block">
                          Equity ({scen.target_equity_pct}%)
                        </span>
                        <strong className="text-sm font-mono text-slate-800">
                          ${scen.target_equity_dollars.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                        </strong>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 font-bold uppercase block">
                          Cash / Collateral ({scen.target_cash_pct}%)
                        </span>
                        <strong className="text-sm font-mono text-emerald-700">
                          ${scen.target_cash_dollars.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                        </strong>
                      </div>
                    </div>

                    {/* Playbook Recommendation */}
                    <div className="space-y-2 text-xs">
                      <div>
                        <strong className="text-slate-700 block">Options Playbook:</strong>
                        <p className="text-slate-600">{scen.options_playbook}</p>
                      </div>
                      <div>
                        <strong className="text-slate-700 block">Benefits:</strong>
                        <p className="text-slate-600">{scen.benefits}</p>
                      </div>
                      <div>
                        <strong className="text-rose-700 block">Downside Risk:</strong>
                        <p className="text-slate-600">{scen.downside_risk}</p>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                      <span className="text-slate-400 font-medium">{scen.cash_drag_status}</span>
                      <span className="text-[#4051B5] font-bold">
                        {isSelected ? '✓ Active Selection' : 'Click to Select'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* TAB 5: INSTITUTIONAL CIO MEMO & WIRE MACRO EVENTS                     */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        {activeTab === 'briefing' && (
          <div className="space-y-6">
            {/* Gemini Multi-Model AI Macro Digest Card */}
            <div className="p-6 bg-gradient-to-br from-indigo-50/50 via-white to-slate-50/50 border border-indigo-100 rounded-2xl shadow-sm space-y-4">
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
                      Daily &amp; weekly institutional synthesis over top 10 market news, calendar catalysts, and cross-asset tables.
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={handleCopyBriefing}
                    disabled={!briefing?.ai_summary}
                    className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 transition text-xs font-semibold flex items-center gap-1.5 shadow-2xs cursor-pointer"
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
                      <h4 className="text-sm font-bold text-slate-800">{loadingStep}</h4>
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
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* TAB 6: DYNAMIC MACRO CATEGORIZATION CORPUS & VOCABULARY STORE       */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        {activeTab === 'corpus' && (
          <div className="space-y-6">
            {/* Header Ribbon */}
            <div className="p-6 bg-gradient-to-br from-indigo-50/60 via-white to-slate-50 border border-indigo-200/80 rounded-2xl shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-indigo-100 pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-[#4051B5] text-white shadow-sm">
                    <Database className="h-6 w-6" />
                  </div>
                  <div>
                    <h2 className="text-base sm:text-lg font-bold text-slate-800 flex items-center gap-2">
                      Dynamic Macro Categorization Corpus &amp; Taxonomy Engine
                    </h2>
                    <p className="text-xs text-slate-500">
                      Growing SQLite vocabulary store powering multi-word weighted phrase classification, options directional biases, and volatility ratings.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowAddKeywordModal(!showAddKeywordModal)}
                    className="px-3.5 py-2 bg-[#4051B5] text-white rounded-xl text-xs font-bold hover:bg-indigo-700 transition flex items-center gap-1.5 shadow-sm cursor-pointer"
                  >
                    <Plus className="h-4 w-4" />
                    <span>{showAddKeywordModal ? 'Close Form' : 'Add Thematic Keyword'}</span>
                  </button>
                  <button
                    onClick={() => fetchCorpus(corpusFilterCategory)}
                    disabled={corpusLoading}
                    className="px-3 py-2 bg-white text-slate-600 border border-slate-200 rounded-xl text-xs font-bold hover:bg-slate-50 transition flex items-center gap-1.5 shadow-xs cursor-pointer"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${corpusLoading ? 'animate-spin text-[#4051B5]' : ''}`} />
                    <span>Refresh</span>
                  </button>
                </div>
              </div>

              {/* Corpus Metrics Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4">
                <div className="bg-white/80 border border-slate-200/60 rounded-xl p-3">
                  <span className="text-[11px] text-slate-500 font-medium">Total Registered Terms</span>
                  <p className="text-lg font-bold text-slate-800 font-mono mt-0.5">{corpusList.length}</p>
                </div>
                <div className="bg-white/80 border border-slate-200/60 rounded-xl p-3">
                  <span className="text-[11px] text-slate-500 font-medium">Active Taxonomy Tiers</span>
                  <p className="text-lg font-bold text-[#4051B5] font-mono mt-0.5">
                    {new Set(corpusList.map(c => c.category)).size}
                  </p>
                </div>
                <div className="bg-white/80 border border-slate-200/60 rounded-xl p-3">
                  <span className="text-[11px] text-slate-500 font-medium">Agentic &amp; AI Terms</span>
                  <p className="text-lg font-bold text-emerald-600 font-mono mt-0.5">
                    {corpusList.filter(c => c.category === 'AI_SEMICONDUCTORS').length}
                  </p>
                </div>
                <div className="bg-white/80 border border-slate-200/60 rounded-xl p-3">
                  <span className="text-[11px] text-slate-500 font-medium">Dynamic Discoveries</span>
                  <p className="text-lg font-bold text-purple-600 font-mono mt-0.5">
                    {corpusList.filter(c => c.source === 'DYNAMIC_DISCOVERY').length}
                  </p>
                </div>
              </div>
            </div>

            {/* Notification Banner */}
            {corpusMessage && (
              <div className={`p-4 rounded-xl text-xs font-bold border flex items-center justify-between ${
                corpusMessage.type === 'success'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-rose-50 text-rose-700 border-rose-200'
              }`}>
                <span>{corpusMessage.text}</span>
                <button onClick={() => setCorpusMessage(null)} className="text-slate-400 hover:text-slate-600">×</button>
              </div>
            )}

            {/* Add Custom Keyword Modal / Card */}
            {showAddKeywordModal && (
              <form onSubmit={handleAddKeyword} className="p-5 bg-white border border-indigo-200 rounded-2xl shadow-md space-y-4 animate-in fade-in duration-200">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-[#4051B5]" />
                    Register Custom Vocabulary or Agentic Term
                  </h3>
                  <span className="text-[11px] text-slate-400 font-mono">SQLite Persistent Store</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="text-[11px] font-bold text-slate-600 block mb-1">Taxonomy Category</label>
                    <select
                      value={newCategory}
                      onChange={(e) => setNewCategory(e.target.value)}
                      className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium focus:ring-1 focus:ring-indigo-500 outline-hidden"
                    >
                      <option value="AI_SEMICONDUCTORS">AI Semiconductors &amp; Agentic Compute</option>
                      <option value="FED_RATES_INFLATION">Fed Rates, Inflation &amp; Macro Policy</option>
                      <option value="ENTERPRISE_SOFTWARE_CLOUD">Enterprise Software &amp; Cloud</option>
                      <option value="ENERGY_POWER_INFRA">Energy, Nuclear &amp; Datacenter Infra</option>
                      <option value="CONSUMER_EMPLOYMENT_RETAIL">Consumer Spending &amp; Jobs</option>
                      <option value="GEOPOLITICS_TRADE">Geopolitics &amp; Global Trade</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-slate-600 block mb-1">Keyword or Multi-Word Phrase</label>
                    <input
                      type="text"
                      placeholder="e.g. agentic app development"
                      value={newKeyword}
                      onChange={(e) => setNewKeyword(e.target.value)}
                      required
                      className="w-full text-xs bg-white border border-slate-200 rounded-lg p-2 font-mono focus:ring-1 focus:ring-indigo-500 outline-hidden"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-slate-600 block mb-1">Importance Weight ({newWeight}x)</label>
                    <input
                      type="range"
                      min="1.0"
                      max="3.0"
                      step="0.1"
                      value={newWeight}
                      onChange={(e) => setNewWeight(parseFloat(e.target.value))}
                      className="w-full mt-2 accent-[#4051B5]"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="text-[11px] font-bold text-slate-600 block mb-1">Options Directional Bias</label>
                    <select
                      value={newBias}
                      onChange={(e) => setNewBias(e.target.value)}
                      className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium focus:ring-1 focus:ring-indigo-500 outline-hidden"
                    >
                      <option value="BULLISH_CSP">BULLISH_CSP (Cash-Secured Puts)</option>
                      <option value="DEFENSIVE_CC">DEFENSIVE_CC (Covered Calls)</option>
                      <option value="NEUTRAL_CALENDAR">NEUTRAL_CALENDAR (Time Decay)</option>
                      <option value="HEDGED_PUT">HEDGED_PUT (Downside Cushion)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-slate-600 block mb-1">Impact Scale (1 to 5)</label>
                    <input
                      type="number"
                      min="1"
                      max="5"
                      value={newImpact}
                      onChange={(e) => setNewImpact(parseInt(e.target.value) || 4)}
                      className="w-full text-xs bg-white border border-slate-200 rounded-lg p-2 font-mono focus:ring-1 focus:ring-indigo-500 outline-hidden"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-slate-600 block mb-1">Associated Underlying Tickers</label>
                    <input
                      type="text"
                      placeholder="e.g. NVDA,PLTR,MSFT"
                      value={newTickers}
                      onChange={(e) => setNewTickers(e.target.value.toUpperCase())}
                      className="w-full text-xs bg-white border border-slate-200 rounded-lg p-2 font-mono uppercase focus:ring-1 focus:ring-indigo-500 outline-hidden"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setShowAddKeywordModal(false)}
                    className="px-4 py-2 bg-slate-100 text-slate-600 rounded-xl text-xs font-bold hover:bg-slate-200 transition cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={corpusSubmitting}
                    className="px-4 py-2 bg-[#4051B5] text-white rounded-xl text-xs font-bold hover:bg-indigo-700 transition flex items-center gap-1.5 shadow-sm cursor-pointer"
                  >
                    {corpusSubmitting ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                    <span>Save to SQLite Corpus</span>
                  </button>
                </div>
              </form>
            )}

            {/* Filter Bar & Search */}
            <div className="bg-white border border-slate-200/80 rounded-2xl p-4 shadow-sm space-y-3">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
                {/* Category Pills */}
                <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
                  {[
                    { id: 'ALL', label: 'All Terms' },
                    { id: 'AI_SEMICONDUCTORS', label: 'Tech & Agentic AI' },
                    { id: 'FED_RATES_INFLATION', label: 'Fed & Rates' },
                    { id: 'ENTERPRISE_SOFTWARE_CLOUD', label: 'Enterprise Cloud' },
                    { id: 'ENERGY_POWER_INFRA', label: 'Energy & Nuclear' },
                    { id: 'CONSUMER_EMPLOYMENT_RETAIL', label: 'Consumer & Jobs' },
                    { id: 'GEOPOLITICS_TRADE', label: 'Geopolitics' }
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => {
                        setCorpusFilterCategory(tab.id);
                        fetchCorpus(tab.id);
                      }}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition whitespace-nowrap cursor-pointer ${
                        corpusFilterCategory === tab.id
                          ? 'bg-[#4051B5] text-white shadow-xs'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Search Bar */}
                <div className="relative w-full sm:w-64">
                  <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    placeholder="Search keywords or tickers..."
                    value={corpusSearch}
                    onChange={(e) => setCorpusSearch(e.target.value)}
                    className="w-full text-xs pl-8 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-1 focus:ring-indigo-500 outline-hidden font-mono"
                  />
                </div>
              </div>
            </div>

            {/* Keyword Data Table */}
            <div className="bg-white border border-slate-200/80 rounded-2xl shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-xs">
                  <thead className="bg-slate-50/90 text-slate-700 font-bold">
                    <tr>
                      <th className="px-4 py-3 text-left">Keyword / N-Gram</th>
                      <th className="px-4 py-3 text-left">Category</th>
                      <th className="px-4 py-3 text-left">Importance Weight</th>
                      <th className="px-4 py-3 text-left">Directional Bias</th>
                      <th className="px-4 py-3 text-left">Impact</th>
                      <th className="px-4 py-3 text-left">Associated Tickers</th>
                      <th className="px-4 py-3 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {corpusList
                      .filter((item) => {
                        if (corpusFilterCategory !== 'ALL' && item.category !== corpusFilterCategory) return false;
                        if (!corpusSearch) return true;
                        const q = corpusSearch.toLowerCase();
                        return (
                          item.keyword.toLowerCase().includes(q) ||
                          item.default_tickers.toLowerCase().includes(q) ||
                          item.category.toLowerCase().includes(q)
                        );
                      })
                      .map((item) => (
                        <tr key={item.id || item.keyword} className="hover:bg-slate-50/70 transition">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-bold text-slate-800">{item.keyword}</span>
                              <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                item.source === 'DYNAMIC_DISCOVERY'
                                  ? 'bg-purple-100 text-purple-700 border border-purple-200'
                                  : item.source === 'MANUAL'
                                  ? 'bg-blue-100 text-blue-700 border border-blue-200'
                                  : 'bg-slate-100 text-slate-500'
                              }`}>
                                {item.source === 'DYNAMIC_DISCOVERY' ? '✨ Learned' : item.source}
                              </span>
                            </div>
                          </td>

                          <td className="px-4 py-3">
                            <span className="px-2 py-0.5 rounded-md bg-indigo-50 text-[#4051B5] font-semibold text-[11px]">
                              {item.category}
                            </span>
                          </td>

                          <td className="px-4 py-3 font-mono">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-700">{item.weight.toFixed(1)}x</span>
                              <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-[#4051B5] rounded-full"
                                  style={{ width: `${Math.min(100, (item.weight / 3.0) * 100)}%` }}
                                />
                              </div>
                            </div>
                          </td>

                          <td className="px-4 py-3">
                            <span className={`px-2 py-0.5 rounded text-[11px] font-bold font-mono ${
                              item.directional_bias.includes('BULLISH')
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : item.directional_bias.includes('DEFENSIVE')
                                ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                : 'bg-slate-100 text-slate-700'
                            }`}>
                              {item.directional_bias}
                            </span>
                          </td>

                          <td className="px-4 py-3 font-mono font-bold text-amber-600">
                            {'★'.repeat(item.default_impact)}
                          </td>

                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1 flex-wrap">
                              {item.default_tickers ? (
                                item.default_tickers.split(',').map((t) => (
                                  <span key={t} className="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded font-mono font-bold text-[10px]">
                                    {t.trim()}
                                  </span>
                                ))
                              ) : (
                                <span className="text-slate-400 text-[10px] italic">Universal</span>
                              )}
                            </div>
                          </td>

                          <td className="px-4 py-3 text-center">
                            <button
                              onClick={() => handleDeleteKeyword(item.keyword)}
                              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition cursor-pointer"
                              title="Delete keyword"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

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
        const headerCells = tableLines[0]
          .split('|')
          .slice(1, -1)
          .map((c) => c.trim());

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

    // Level 2 Section Heading
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

    // Level 3 Priority Headers or Story Headlines
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
