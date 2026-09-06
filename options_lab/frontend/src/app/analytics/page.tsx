'use client';

import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  ShieldCheck, 
  Award, 
  Layers, 
  Activity, 
  Sliders, 
  RefreshCw, 
  Calendar, 
  FileText, 
  ExternalLink, 
  X, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles, 
  ArrowUpRight,
  ChevronRight,
  DollarSign
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';
import { optionsApi } from '@/lib/api';
import ProtectedRoute from '@/components/ProtectedRoute';

interface SummaryMetrics {
  total_return_pct?: number;
  cagr_pct?: number;
  sharpe?: number;
  smart_sharpe?: number;
  sortino?: number;
  smart_sortino?: number;
  calmar?: number;
  max_drawdown_pct?: number;
  volatility_pct?: number;
  alpha_pct?: number;
  beta?: number;
  r_squared?: number;
  information_ratio?: number;
  treynor_ratio?: number;
  var_95_pct?: number;
  cvar_95_pct?: number;
  tail_ratio?: number;
  win_rate_pct?: number;
  profit_factor?: number;
  payoff_ratio?: number;
  kelly_criterion?: number;
  benchmark_total_return_pct?: number;
  benchmark_cagr_pct?: number;
  benchmark_sharpe?: number;
  benchmark_max_drawdown_pct?: number;
  [key: string]: any;
}

interface EquityCurvePoint {
  date: string;
  strategy: number;
  underlying: number;
  benchmark: number;
  strategy_drawdown: number;
  benchmark_drawdown: number;
}

interface MonthlyRow {
  year: string;
  Jan?: number;
  Feb?: number;
  Mar?: number;
  Apr?: number;
  May?: number;
  Jun?: number;
  Jul?: number;
  Aug?: number;
  Sep?: number;
  Oct?: number;
  Nov?: number;
  Dec?: number;
  YTD?: number;
}

interface TradeLogItem {
  id: string;
  strategy: string;
  symbol: string;
  entry_date: string;
  exit_date: string;
  strike: number;
  entry_premium: number;
  exit_premium: number;
  contracts: number;
  net_pnl: number;
  return_pct: number;
  outcome: string;
  days_held: number;
}

interface BacktestResponse {
  symbol: string;
  benchmark: string;
  lookback_years: number;
  initial_capital: number;
  final_equity: number;
  summary_metrics: SummaryMetrics;
  underlying_metrics: SummaryMetrics;
  benchmark_metrics: SummaryMetrics;
  equity_curves: EquityCurvePoint[];
  monthly_matrix: MonthlyRow[];
  trade_log: TradeLogItem[];
  report_id: string;
  generated_at: string;
}

const PRESET_TICKERS = ['AAPL', 'COIN', 'NVDA', 'IBM', 'INTC', 'MSFT', 'TSLA', 'SPY'];
const BENCHMARKS = [
  { id: 'SPY', name: 'S&P 500 (SPY)' },
  { id: 'QQQ', name: 'Nasdaq 100 (QQQ)' },
  { id: 'DIA', name: 'Dow Jones (DIA)' },
  { id: 'URTH', name: 'MSCI World (URTH)' }
];

export default function AnalyticsPage() {
  const [symbol, setSymbol] = useState('AAPL');
  const [customSymbol, setCustomSymbol] = useState('');
  const [benchmark, setBenchmark] = useState('SPY');
  const [lookbackYears, setLookbackYears] = useState(2);
  const [initialCapital, setInitialCapital] = useState(100000);
  const [holdToExpiration, setHoldToExpiration] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Strategy Parameters
  const [targetDte, setTargetDte] = useState(30);
  const [otmPct, setOtmPct] = useState(0.08);
  const [profitTargetPct, setProfitTargetPct] = useState(0.50);
  const [gammaRollDte, setGammaRollDte] = useState(21);

  // State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<BacktestResponse | null>(null);
  const [showTearsheetModal, setShowTearsheetModal] = useState(false);
  const [tradeFilter, setTradeFilter] = useState<'ALL' | 'CSP' | 'CC'>('ALL');

  const runBacktest = async (targetSym?: string, targetBench?: string, targetYears?: number, targetHold?: boolean) => {
    const sym = (targetSym || (customSymbol.trim() ? customSymbol.trim() : symbol)).toUpperCase();
    const bench = (targetBench || benchmark).toUpperCase();
    const yrs = targetYears !== undefined ? targetYears : lookbackYears;
    const hold = targetHold !== undefined ? targetHold : holdToExpiration;

    setLoading(true);
    setError(null);

    try {
      const result: BacktestResponse = await optionsApi.runWheelBacktest({
        symbol: sym,
        benchmark: bench,
        lookback_years: yrs,
        initial_capital: initialCapital,
        target_dte: targetDte,
        otm_pct: otmPct,
        profit_target_pct: profitTargetPct,
        gamma_roll_dte: gammaRollDte,
        hold_to_expiration: hold
      });
      setData(result);
    } catch (err: any) {
      console.error('Backtest error:', err);
      setError(err.message || 'Error running QuantStats backtest.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runBacktest();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTickerPreset = (t: string) => {
    setSymbol(t);
    setCustomSymbol('');
    runBacktest(t, benchmark, lookbackYears, holdToExpiration);
  };

  const filteredTrades = data?.trade_log.filter(t => {
    if (tradeFilter === 'ALL') return true;
    return t.strategy === tradeFilter;
  }) || [];

  const getHeatmapCellStyle = (val: number | undefined) => {
    if (val === undefined || val === 0) {
      return 'bg-slate-50/60 text-slate-400 border border-slate-100 font-normal';
    }
    if (val >= 4.0) {
      return 'bg-emerald-600 text-white font-bold shadow-xs';
    }
    if (val >= 2.0) {
      return 'bg-emerald-100 text-emerald-800 font-semibold border border-emerald-200/80';
    }
    if (val > 0) {
      return 'bg-emerald-50 text-emerald-700 font-medium border border-emerald-100';
    }
    if (val <= -4.0) {
      return 'bg-rose-600 text-white font-bold shadow-xs';
    }
    if (val <= -2.0) {
      return 'bg-rose-100 text-rose-800 font-semibold border border-rose-200/80';
    }
    return 'bg-rose-50 text-rose-700 font-medium border border-rose-100';
  };

  return (
    <ProtectedRoute>
      <div className="space-y-6 pb-12">
        {/* ── Banner Header - Velzon Light Theme ──────────────────────────── */}
        <div className="relative overflow-hidden rounded-xl bg-white p-6 sm:p-8 border border-slate-200/80 shadow-sm">
          <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-indigo-50/60 blur-2xl" />
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-2 max-w-3xl">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-[#4051B5] border border-indigo-100">
                <BarChart3 className="h-3.5 w-3.5" /> QuantStats Institutional Analytics &amp; Strategy Benchmarking
              </span>
              <h1 className="text-2xl font-bold text-slate-800 tracking-tight sm:text-3xl">
                QuantStats Analytics &amp; <span className="text-[#4051B5]">Strategy Benchmarking</span>
              </h1>
              <p className="text-slate-500 text-xs sm:text-sm leading-relaxed">
                Benchmark systematic 30-DTE Cash-Secured Put &amp; Covered Call harvesting against S&amp;P 500 (SPY), Nasdaq 100 (QQQ), and underlying equities with 50+ institutional risk metrics.
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center gap-3">
              {data?.report_id && (
                <button
                  onClick={() => setShowTearsheetModal(true)}
                  className="flex items-center gap-2 px-4 py-2.5 bg-[#4051B5] hover:bg-[#344299] text-white rounded-xl text-xs font-semibold shadow-sm transition cursor-pointer"
                  title="View full standalone QuantStats HTML Tear Sheet"
                >
                  <FileText className="h-4 w-4" />
                  View Full Tear Sheet (HTML)
                </button>
              )}
            </div>
          </div>
        </div>

        {/* ── Configuration & Control Toolbar ─────────────────────────────── */}
        <div className="p-6 bg-white border border-slate-200/80 rounded-xl shadow-sm space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            {/* Tickers Selection */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mr-1">
                Underlying:
              </span>
              {PRESET_TICKERS.map(t => (
                <button
                  key={t}
                  onClick={() => handleTickerPreset(t)}
                  className={`px-3 py-1.5 text-xs font-bold rounded-lg border transition-all cursor-pointer ${
                    symbol === t && !customSymbol
                      ? 'bg-[#4051B5] text-white border-[#4051B5] shadow-xs'
                      : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {t}
                </button>
              ))}

              {/* Custom Search Input */}
              <div className="relative inline-flex items-center ml-2">
                <input
                  type="text"
                  placeholder="Custom (e.g. GOOG)"
                  value={customSymbol}
                  onChange={e => setCustomSymbol(e.target.value.toUpperCase())}
                  onKeyDown={e => { if (e.key === 'Enter') runBacktest(); }}
                  className="w-32 px-3 py-1.5 text-xs font-bold rounded-lg border border-slate-300 bg-white text-slate-800 uppercase focus:outline-hidden focus:ring-2 focus:ring-[#4051B5]"
                />
              </div>
            </div>

            {/* Benchmark, Horizon & Execution Mode Pickers */}
            <div className="flex flex-wrap items-center gap-3">
              {/* Execution Mode Selector */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Mode:
                </span>
                <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-50">
                  <button
                    onClick={() => { setHoldToExpiration(true); runBacktest(symbol, benchmark, lookbackYears, true); }}
                    className={`px-3 py-1 text-xs font-bold rounded-md transition-all cursor-pointer ${
                      holdToExpiration
                        ? 'bg-[#4051B5] text-white shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                    title="10-12 Monthly Cycles/Year, 30-Day Hold to Expiration"
                  >
                    Monthly Harvest (~30d)
                  </button>
                  <button
                    onClick={() => { setHoldToExpiration(false); runBacktest(symbol, benchmark, lookbackYears, false); }}
                    className={`px-3 py-1 text-xs font-bold rounded-md transition-all cursor-pointer ${
                      !holdToExpiration
                        ? 'bg-[#4051B5] text-white shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                    title="Active Scalping with 50% Early Profit Exit"
                  >
                    50% Early Exit
                  </button>
                </div>
              </div>

              {/* Benchmark Dropdown */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Benchmark:
                </span>
                <select
                  value={benchmark}
                  onChange={e => { setBenchmark(e.target.value); runBacktest(symbol, e.target.value, lookbackYears, holdToExpiration); }}
                  className="px-3 py-1.5 text-xs font-bold rounded-lg border border-slate-300 bg-white text-slate-800 cursor-pointer focus:outline-hidden focus:ring-2 focus:ring-[#4051B5]"
                >
                  {BENCHMARKS.map(b => (
                    <option key={b.id} value={b.id}>{b.name}</option>
                  ))}
                </select>
              </div>

              {/* Horizon Selector */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Horizon:
                </span>
                <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-50">
                  {[1, 2, 3].map(yr => (
                    <button
                      key={yr}
                      onClick={() => { setLookbackYears(yr); runBacktest(symbol, benchmark, yr, holdToExpiration); }}
                      className={`px-2.5 py-1 text-xs font-bold rounded-md transition-all cursor-pointer ${
                        lookbackYears === yr
                          ? 'bg-[#4051B5] text-white shadow-xs'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      {yr}Y
                    </button>
                  ))}
                </div>
              </div>

              {/* Strategy Rules Toggle */}
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 transition-all cursor-pointer"
              >
                <Sliders className="w-3.5 h-3.5 text-[#4051B5]" />
                {showAdvanced ? 'Hide Rules' : 'Strategy Rules'}
              </button>

              {/* Run Backtest Button */}
              <button
                onClick={() => runBacktest(symbol, benchmark, lookbackYears, holdToExpiration)}
                disabled={loading}
                className="inline-flex items-center gap-2 px-4 py-1.5 text-xs font-bold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs transition-all disabled:opacity-50 cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                {loading ? 'Simulating...' : 'Run Backtest'}
              </button>
            </div>
          </div>

          {/* Strategy Rules Drawer */}
          {showAdvanced && (
            <div className="pt-4 border-t border-slate-100 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
              <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-100">
                <label className="font-bold text-slate-700 block mb-1">Target Entry DTE</label>
                <input
                  type="number"
                  value={targetDte}
                  onChange={e => setTargetDte(parseInt(e.target.value) || 30)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-800 font-semibold"
                />
                <span className="text-[10px] text-slate-500 mt-1 block">Strict 30-32 DTE sweet spot</span>
              </div>
              <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-100">
                <label className="font-bold text-slate-700 block mb-1">OTM Strike Distance</label>
                <input
                  type="number"
                  step="0.01"
                  value={otmPct}
                  onChange={e => setOtmPct(parseFloat(e.target.value) || 0.08)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-800 font-semibold"
                />
                <span className="text-[10px] text-slate-500 mt-1 block">0.08 = ~8% OTM (Delta ~0.22)</span>
              </div>
              <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-100">
                <label className="font-bold text-slate-700 block mb-1">Early Profit Target</label>
                <input
                  type="number"
                  step="0.05"
                  value={profitTargetPct}
                  onChange={e => setProfitTargetPct(parseFloat(e.target.value) || 0.50)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-800 font-semibold"
                />
                <span className="text-[10px] text-slate-500 mt-1 block">0.50 = 50% max profit exit</span>
              </div>
              <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-100">
                <label className="font-bold text-slate-700 block mb-1">Gamma Roll Avoidance</label>
                <input
                  type="number"
                  value={gammaRollDte}
                  onChange={e => setGammaRollDte(parseInt(e.target.value) || 21)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-800 font-semibold"
                />
                <span className="text-[10px] text-slate-500 mt-1 block">Roll at 21 DTE if OTM</span>
              </div>
            </div>
          )}
        </div>

        {/* Error Notification */}
        {error && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-3 text-rose-700 text-sm shadow-xs">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* ── Executive Comparative KPI Ribbon (Velzon Theme) ─────────────── */}
        {data && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Card 1: Risk-Adjusted Quality */}
            <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Risk-Adjusted Quality
                </span>
                <div className="p-1.5 bg-emerald-50 rounded-lg border border-emerald-100 text-emerald-600">
                  <Award className="w-4 h-4" />
                </div>
              </div>
              <div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-slate-800">
                    {data.summary_metrics.sharpe?.toFixed(2) ?? '—'}
                  </span>
                  <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-100">
                    Sharpe Ratio
                  </span>
                </div>
                <div className="text-xs text-slate-500 mt-2 flex items-center justify-between">
                  <span>Sortino: <strong className="text-slate-700">{data.summary_metrics.sortino?.toFixed(2) ?? '—'}</strong></span>
                  <span>Calmar: <strong className="text-slate-700">{data.summary_metrics.calmar?.toFixed(2) ?? '—'}</strong></span>
                </div>
              </div>
              <div className="pt-2.5 border-t border-slate-100 flex justify-between text-[11px] text-slate-500">
                <span>{data.benchmark} Sharpe: {data.benchmark_metrics.sharpe?.toFixed(2) ?? '—'}</span>
                <span>{data.symbol} Sharpe: {data.underlying_metrics.sharpe?.toFixed(2) ?? '—'}</span>
              </div>
            </div>

            {/* Card 2: Benchmark Sensitivity */}
            <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Benchmark Sensitivity
                </span>
                <div className="p-1.5 bg-indigo-50 rounded-lg border border-indigo-100 text-[#4051B5]">
                  <TrendingUp className="w-4 h-4" />
                </div>
              </div>
              <div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-[#4051B5]">
                    {data.summary_metrics.alpha_pct ? `${data.summary_metrics.alpha_pct > 0 ? '+' : ''}${data.summary_metrics.alpha_pct.toFixed(1)}%` : '0.0%'}
                  </span>
                  <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-md border border-indigo-100">
                    α vs {data.benchmark}
                  </span>
                </div>
                <div className="text-xs text-slate-500 mt-2 flex items-center justify-between">
                  <span>Beta (β): <strong className="text-slate-700">{data.summary_metrics.beta?.toFixed(2) ?? '1.00'}</strong></span>
                  <span>R²: <strong className="text-slate-700">{data.summary_metrics.r_squared ? `${(data.summary_metrics.r_squared * 100).toFixed(0)}%` : '—'}</strong></span>
                </div>
              </div>
              <div className="pt-2.5 border-t border-slate-100 flex justify-between text-[11px] text-slate-500">
                <span>Vol: {data.summary_metrics.volatility_pct?.toFixed(1)}%</span>
                <span>{data.benchmark} Vol: {data.benchmark_metrics.volatility_pct?.toFixed(1)}%</span>
              </div>
            </div>

            {/* Card 3: Downside Protection */}
            <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Downside Protection
                </span>
                <div className="p-1.5 bg-rose-50 rounded-lg border border-rose-100 text-rose-600">
                  <ShieldCheck className="w-4 h-4" />
                </div>
              </div>
              <div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-rose-600">
                    {data.summary_metrics.max_drawdown_pct ? `${data.summary_metrics.max_drawdown_pct.toFixed(1)}%` : '0.0%'}
                  </span>
                  <span className="text-xs font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-md border border-rose-100">
                    Max Drawdown
                  </span>
                </div>
                <div className="text-xs text-slate-500 mt-2 flex items-center justify-between">
                  <span>VaR 95%: <strong className="text-slate-700">{data.summary_metrics.var_95_pct?.toFixed(1)}%</strong></span>
                  <span>CVaR 95%: <strong className="text-slate-700">{data.summary_metrics.cvar_95_pct?.toFixed(1)}%</strong></span>
                </div>
              </div>
              <div className="pt-2.5 border-t border-slate-100 flex justify-between text-[11px] text-slate-500">
                <span>{data.benchmark} MaxDD: {data.benchmark_metrics.max_drawdown_pct?.toFixed(1)}%</span>
                <span>{data.symbol} MaxDD: {data.underlying_metrics.max_drawdown_pct?.toFixed(1)}%</span>
              </div>
            </div>

            {/* Card 4: Harvest Efficiency */}
            <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Harvest Efficiency
                </span>
                <div className="p-1.5 bg-emerald-50 rounded-lg border border-emerald-100 text-emerald-600">
                  <Activity className="w-4 h-4" />
                </div>
              </div>
              <div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-emerald-700">
                    {data.summary_metrics.win_rate_pct ? `${data.summary_metrics.win_rate_pct.toFixed(1)}%` : '—'}
                  </span>
                  <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-100">
                    Win Rate ({data.trade_log.length} cycles)
                  </span>
                </div>
                <div className="text-xs text-slate-500 mt-2 flex items-center justify-between">
                  <span>Profit Factor: <strong className="text-slate-700">{data.summary_metrics.profit_factor?.toFixed(2) ?? '—'}</strong></span>
                  <span>Kelly: <strong className="text-slate-700">{data.summary_metrics.kelly_criterion ? `${(data.summary_metrics.kelly_criterion * 100).toFixed(0)}%` : '—'}</strong></span>
                </div>
              </div>
              <div className="pt-2.5 border-t border-slate-100 flex justify-between text-[11px] text-slate-500">
                <span>Final: ${data.final_equity.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                <span>CAGR: {data.summary_metrics.cagr_pct?.toFixed(1)}%</span>
              </div>
            </div>
          </div>
        )}

        {/* ── Main Performance Charts Grid ────────────────────────────────── */}
        {data && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Cumulative Return (%) Chart */}
            <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div>
                  <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-emerald-600" />
                    Cumulative Return (%) Comparison
                  </h3>
                  <p className="text-xs text-slate-500">
                    30-DTE Systematic Wheel Strategy vs {data.benchmark} vs {data.symbol} Buy-and-Hold
                  </p>
                </div>
                <div className="flex items-center gap-3 text-xs font-semibold">
                  <span className="flex items-center gap-1.5 text-emerald-700">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span>
                    Strategy ({data.summary_metrics.total_return_pct?.toFixed(1)}%)
                  </span>
                  <span className="flex items-center gap-1.5 text-[#4051B5]">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#4051B5] inline-block"></span>
                    {data.benchmark} ({data.benchmark_metrics.total_return_pct?.toFixed(1)}%)
                  </span>
                  <span className="flex items-center gap-1.5 text-slate-500">
                    <span className="w-2.5 h-2.5 rounded-full bg-slate-400 inline-block"></span>
                    {data.symbol} ({data.underlying_metrics.total_return_pct?.toFixed(1)}%)
                  </span>
                </div>
              </div>

              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.equity_curves} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis 
                      dataKey="date" 
                      tick={{ fontSize: 11, fill: '#64748b' }} 
                      minTickGap={40}
                    />
                    <YAxis 
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickFormatter={v => `${v}%`}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '10px', fontSize: '12px', color: '#1e293b', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                      formatter={(val: any, name: string) => [`${val}%`, name === 'strategy' ? '30-DTE Wheel Strategy' : name.toUpperCase()]}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="strategy" 
                      stroke="#10b981" 
                      strokeWidth={2.5} 
                      dot={false}
                      name="strategy"
                    />
                    <Line 
                      type="monotone" 
                      dataKey="benchmark" 
                      stroke="#4051B5" 
                      strokeWidth={1.75} 
                      strokeDasharray="4 4"
                      dot={false}
                      name={data.benchmark}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="underlying" 
                      stroke="#94a3b8" 
                      strokeWidth={1.5} 
                      dot={false}
                      name={data.symbol}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Underwater Drawdown Chart */}
            <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
              <div>
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-rose-600" />
                  Underwater Drawdown (%)
                </h3>
                <p className="text-xs text-slate-500">
                  Peak-to-trough equity preservation
                </p>
              </div>

              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.equity_curves} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis 
                      dataKey="date" 
                      tick={{ fontSize: 11, fill: '#64748b' }} 
                      minTickGap={30}
                    />
                    <YAxis 
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickFormatter={v => `${v}%`}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '10px', fontSize: '12px', color: '#1e293b', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                      formatter={(val: any, name: string) => [`${val}%`, name === 'strategy_drawdown' ? 'Strategy Drawdown' : 'Benchmark Drawdown']}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="strategy_drawdown" 
                      stroke="#ef4444" 
                      fill="#ef4444" 
                      fillOpacity={0.20}
                      strokeWidth={2}
                      name="strategy_drawdown"
                    />
                    <Area 
                      type="monotone" 
                      dataKey="benchmark_drawdown" 
                      stroke="#94a3b8" 
                      fill="#94a3b8" 
                      fillOpacity={0.06}
                      strokeWidth={1}
                      strokeDasharray="3 3"
                      name="benchmark_drawdown"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {/* ── Monthly Returns Heatmap Matrix (Velzon Clean Table) ──────────── */}
        {data && data.monthly_matrix && data.monthly_matrix.length > 0 && (
          <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-[#4051B5]" />
                  Monthly Return Heatmap Matrix (%)
                </h3>
                <p className="text-xs text-slate-500">
                  Detailed breakdown of systematic 30-DTE option harvest performance across calendar months
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-indigo-50 text-[#4051B5] border border-indigo-100">
                  {data.lookback_years}Y Lookback ({data.monthly_matrix.length} Years Active)
                </span>
                <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-emerald-50 text-emerald-700 border border-emerald-100">
                  {holdToExpiration ? 'Monthly Harvest (~30d Hold)' : '50% Early Exit'}
                </span>
              </div>
            </div>

            <div className="overflow-x-auto rounded-lg border border-slate-200/80">
              <table className="w-full text-xs text-center border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold text-[11px] uppercase tracking-wider">
                    <th className="py-3 px-4 text-left font-bold text-slate-800">Year</th>
                    {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map(m => (
                      <th key={m} className="py-3 px-2.5 font-semibold text-slate-600">{m}</th>
                    ))}
                    <th className="py-3 px-4 font-bold text-slate-900 bg-slate-100/70 border-l border-slate-200">YTD</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.monthly_matrix.map(row => (
                    <tr key={row.year} className="hover:bg-slate-50/50 transition">
                      <td className="py-3 px-4 text-left font-bold text-slate-800">{row.year}</td>
                      {(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'] as const).map(m => {
                        const val = row[m];
                        return (
                          <td key={m} className="py-2.5 px-1.5">
                            <div className={`py-1 px-1.5 rounded-md transition-all text-center ${getHeatmapCellStyle(val)}`}>
                              {val !== undefined && val !== 0 ? `${val > 0 ? '+' : ''}${val.toFixed(1)}%` : '—'}
                            </div>
                          </td>
                        );
                      })}
                      <td className="py-3 px-4 font-bold bg-slate-50/80 border-l border-slate-200">
                        <span className={row.YTD && row.YTD >= 0 ? 'text-emerald-700' : 'text-rose-700'}>
                          {row.YTD ? `${row.YTD > 0 ? '+' : ''}${row.YTD.toFixed(1)}%` : '0.0%'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Simulated 30-DTE Option Harvest Blotter (Velzon Theme) ────────── */}
        {data && (
          <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-emerald-600" />
                  Simulated 30-DTE Harvest Cycles ({data.trade_log.length})
                </h3>
                <p className="text-xs text-slate-500">
                  Executed Cash-Secured Puts and Covered Calls under strict quantitative risk governance
                </p>
              </div>

              {/* Filter Tabs */}
              <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-50">
                {(['ALL', 'CSP', 'CC'] as const).map(tab => (
                  <button
                    key={tab}
                    onClick={() => setTradeFilter(tab)}
                    className={`px-3 py-1 text-xs font-bold rounded-md transition-all cursor-pointer ${
                      tradeFilter === tab
                        ? 'bg-[#4051B5] text-white shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            </div>

            <div className="overflow-x-auto rounded-lg border border-slate-200/80">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold text-[11px] uppercase tracking-wider">
                    <th className="py-3 px-3">ID</th>
                    <th className="py-3 px-3">Strategy</th>
                    <th className="py-3 px-3">Execution Dates</th>
                    <th className="py-3 px-3">Strike</th>
                    <th className="py-3 px-3">Entry Prem</th>
                    <th className="py-3 px-3">Exit Prem</th>
                    <th className="py-3 px-3">Net PnL ($)</th>
                    <th className="py-3 px-3">Outcome</th>
                    <th className="py-3 px-3 text-right">Days Held</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-medium">
                  {filteredTrades.slice(0, 15).map(trade => (
                    <tr key={trade.id} className="hover:bg-slate-50/60 transition">
                      <td className="py-3 px-3 font-bold text-slate-500">{trade.id}</td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-0.5 rounded-md font-bold text-[11px] border ${
                          trade.strategy === 'CSP'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200/70'
                            : 'bg-indigo-50 text-[#4051B5] border-indigo-200/70'
                        }`}>
                          {trade.strategy}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-slate-600">
                        {trade.entry_date} <span className="text-slate-400">→</span> {trade.exit_date}
                      </td>
                      <td className="py-3 px-3 font-bold text-slate-800">
                        ${trade.strike.toFixed(2)}
                      </td>
                      <td className="py-3 px-3 text-slate-600">${trade.entry_premium.toFixed(2)}</td>
                      <td className="py-3 px-3 text-slate-600">${trade.exit_premium.toFixed(2)}</td>
                      <td className="py-3 px-3">
                        <span className={`font-bold ${trade.net_pnl >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                          {trade.net_pnl >= 0 ? '+' : ''}${trade.net_pnl.toLocaleString()} ({trade.return_pct > 0 ? '+' : ''}{trade.return_pct}%)
                        </span>
                      </td>
                      <td className="py-3 px-3 text-slate-700">
                        <span className="flex items-center gap-1.5">
                          {trade.outcome.includes('Profit') ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 inline shrink-0" />
                          ) : trade.outcome.includes('Assigned') ? (
                            <AlertCircle className="w-3.5 h-3.5 text-amber-500 inline shrink-0" />
                          ) : (
                            <ShieldCheck className="w-3.5 h-3.5 text-[#4051B5] inline shrink-0" />
                          )}
                          {trade.outcome}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right font-bold text-slate-500">{trade.days_held}d</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Full Institutional Tear Sheet Modal ─────────────────────────── */}
        {showTearsheetModal && data?.report_id && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
            <div className="bg-white rounded-2xl w-full max-w-5xl h-[88vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden">
              {/* Modal Header */}
              <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
                <div className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-[#4051B5]" />
                  <h3 className="font-bold text-slate-800 text-sm">
                    QuantStats Institutional Tear Sheet ({data.symbol} vs {data.benchmark})
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <a
                    href={`/api/analytics/tearsheet/${data.report_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 transition cursor-pointer"
                    title="Open standalone report in new window"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                  <button
                    onClick={() => setShowTearsheetModal(false)}
                    className="p-2 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 transition cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Modal Body: Embedded iframe */}
              <div className="flex-1 w-full bg-white">
                <iframe
                  src={`/api/analytics/tearsheet/${data.report_id}`}
                  title="QuantStats Tear Sheet"
                  className="w-full h-full border-0"
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
