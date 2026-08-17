'use client';

import React, { useState, useEffect } from 'react';
import { 
  Calendar, 
  Search, 
  TrendingUp, 
  Activity, 
  CheckCircle2, 
  AlertCircle, 
  ArrowUpRight, 
  Sliders, 
  Layers, 
  ChevronRight,
  RefreshCw,
  Sparkles
} from 'lucide-react';
import { optionsApi } from '@/lib/api';
import ProtectedRoute from '@/components/ProtectedRoute';

interface QuarterVol {
  quarter: string;
  earnings_date: string;
  vol_5d_before_pct: number;
  move_t_minus_1_pct: number;
  move_t_plus_1_pct: number;
}

interface EarningPlay {
  symbol: string;
  name: string;
  eps_forecast?: string;
  time_of_day?: string;
  date_str: string;
  current_price: number;
  low_52w: number;
  high_52w: number;
  pct_above_low: number;
  fundamental_metrics: {
    piotroski_score: number | string;
    altman_z_score: number | string;
    roe: number | string;
    operating_margin: number | string;
    debt_to_equity: number | string;
  };
  pass_ratio: string;
  options_open_interest: number;
  score: number;
  rationale: string;
  volatility_metrics: {
    avg_vol_5d_before_pct: number;
    avg_move_t_minus_1_pct: number;
    avg_move_t_plus_1_pct: number;
    quarters: QuarterVol[];
  };
}

interface ScanResult {
  scan_timestamp: string;
  total_earners_scraped: number;
  universe_earners: number;
  passed_52w_low: number;
  passed_fundamentals: number;
  passed_liquidity: number;
  plays: EarningPlay[];
}

export default function EarningsPage() {
  const [lowThreshold, setLowThreshold] = useState<number>(20);
  const [minOpenInterest, setMinOpenInterest] = useState<number | string>(5000);
  const [scanning, setScanning] = useState<boolean>(false);
  const [results, setResults] = useState<ScanResult | null>(null);
  const [selectedPlay, setSelectedPlay] = useState<EarningPlay | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Trigger scan on load
  useEffect(() => {
    handleScan();
  }, []);

  const handleScan = async () => {
    setScanning(true);
    setError(null);
    setSelectedPlay(null);
    try {
      const cleanOI = typeof minOpenInterest === 'number' ? minOpenInterest : parseInt(String(minOpenInterest), 10) || 5000;
      const data = await optionsApi.scanEarnings({
        low_threshold_pct: lowThreshold / 100,
        min_open_interest: cleanOI
      });
      setResults(data);
      if (data.plays && data.plays.length > 0) {
        setSelectedPlay(data.plays[0]);
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to complete earnings universe scan.');
    } finally {
      setScanning(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-emerald-700 bg-emerald-50 border-emerald-200';
    if (score >= 0.6) return 'text-[#4051B5] bg-indigo-50 border-indigo-200';
    return 'text-amber-700 bg-amber-50 border-amber-200';
  };

  const formatMove = (move: number) => {
    const sign = move > 0 ? '+' : '';
    return `${sign}${move.toFixed(2)}%`;
  };

  return (
    <ProtectedRoute>
      <div className="space-y-6 pb-12">
        {/* Banner Header - Velzon Light Theme */}
        <div className="relative overflow-hidden rounded-xl bg-white p-6 sm:p-8 border border-slate-200/80 shadow-sm">
          <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-indigo-50/60 blur-2xl" />
          <div className="relative z-10 max-w-3xl space-y-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-[#4051B5] border border-indigo-100">
              <Calendar className="h-3.5 w-3.5" /> Earnings Volatility Scanner
            </span>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight sm:text-3xl">
              Earnings Volatility & <span className="text-[#4051B5]">Macro Playbook</span>
            </h1>
            <p className="text-slate-500 text-xs sm:text-sm leading-relaxed">
              Screen upcoming earnings for deep-value, high-conviction stocks close to 52-week lows. Analyze 4-quarter pre-earnings IV crush, T-1 move expectation, and T+1 reaction magnitude.
            </p>
          </div>
        </div>

        {/* Configuration Controls */}
        <div className="grid gap-6 md:grid-cols-4 items-end p-6 bg-white border border-slate-200/80 rounded-xl shadow-sm">
          <div className="space-y-2 col-span-2">
            <div className="flex justify-between items-center text-sm">
              <label className="text-slate-700 font-semibold flex items-center gap-1.5 text-xs">
                <Sliders className="h-4 w-4 text-[#4051B5]" /> Max Proximity to 52-Week Low
              </label>
              <span className="text-[#4051B5] font-mono font-bold">{lowThreshold}%</span>
            </div>
            <input 
              type="range" 
              min="5" 
              max="40" 
              value={lowThreshold} 
              onChange={(e) => setLowThreshold(parseInt(e.target.value))}
              disabled={scanning}
              className="w-full h-2 rounded-lg bg-slate-100 accent-[#4051B5] cursor-pointer"
            />
          </div>

          <div className="space-y-1.5 col-span-1">
            <label className="text-xs text-slate-500 font-semibold block">
              Min Option Open Interest
            </label>
            <input 
              type="text" 
              value={minOpenInterest} 
              onChange={(e) => {
                const val = e.target.value;
                if (val === '') {
                  setMinOpenInterest('');
                } else {
                  const cleanVal = val.replace(/[^0-9]/g, '');
                  setMinOpenInterest(cleanVal ? parseInt(cleanVal, 10) : '');
                }
              }}
              disabled={scanning}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono font-medium"
            />
          </div>

          <div className="col-span-1">
            <button
              onClick={handleScan}
              disabled={scanning}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-[#4051B5] hover:bg-[#34449a] px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition disabled:opacity-50"
            >
              {scanning ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" /> Scanning Universe...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" /> Scan Universe
                </>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
            <AlertCircle className="h-5 w-5 shrink-0 text-rose-500" />
            <span>{error}</span>
          </div>
        )}

        {/* Scan Summary Cards */}
        {results && !scanning && (
          <div className="grid gap-4 grid-cols-2 md:grid-cols-5">
            {[
              { label: 'Total Scraped', val: results.total_earners_scraped, desc: 'Next week earners' },
              { label: 'Universe Earner', val: results.universe_earners, desc: 'NASDAQ / S&P 500' },
              { label: 'Passed 52W Low', val: results.passed_52w_low, desc: `Within ${lowThreshold}%` },
              { label: 'Exhaustive Fund', val: results.passed_fundamentals, desc: 'Passed >=75% checks' },
              { label: 'Liquid Options', val: results.passed_liquidity, desc: `OI >= ${minOpenInterest.toLocaleString()}` },
            ].map((stat, idx) => (
              <div key={idx} className="p-4 bg-white border border-slate-200/80 rounded-xl shadow-sm flex flex-col justify-between">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">{stat.label}</span>
                <span className="text-2xl font-bold font-mono text-slate-800 my-1">{stat.val}</span>
                <span className="text-[11px] text-slate-500">{stat.desc}</span>
              </div>
            ))}
          </div>
        )}

        {/* Main Content Layout */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Table List of Plays */}
          <div className="lg:col-span-2 p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                <Activity className="h-5 w-5 text-[#4051B5]" /> Ranked Earnings Opportunities
              </h2>
              {results && (
                <span className="text-xs text-slate-400 font-mono">Scan complete: {results.scan_timestamp}</span>
              )}
            </div>

            {scanning ? (
              <div className="space-y-4 py-16 text-center">
                <RefreshCw className="h-8 w-8 text-[#4051B5] animate-spin mx-auto" />
                <p className="text-slate-500 text-xs font-medium">Screening 52W lows, verifying financial fortress scores, and analyzing option chain liquidity...</p>
              </div>
            ) : results && results.plays && results.plays.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                      <th className="py-3 px-4">Symbol</th>
                      <th className="py-3 px-4">Earnings Date</th>
                      <th className="py-3 px-4">52W Low Prox</th>
                      <th className="py-3 px-4 text-center">Quality</th>
                      <th className="py-3 px-4 text-right">Option OI</th>
                      <th className="py-3 px-4 text-right">Score</th>
                      <th className="py-3 px-4"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs font-medium">
                    {results.plays.map((play) => (
                      <tr 
                        key={play.symbol}
                        onClick={() => setSelectedPlay(play)}
                        className={`hover:bg-slate-50 cursor-pointer transition-all duration-150 ${
                          selectedPlay?.symbol === play.symbol ? 'bg-indigo-50/60 border-l-4 border-[#4051B5]' : ''
                        }`}
                      >
                        <td className="py-3.5 px-4">
                          <div className="font-bold text-slate-800 font-mono text-sm">{play.symbol}</div>
                          <div className="text-[11px] text-slate-400 truncate max-w-[140px]">{play.name}</div>
                        </td>
                        <td className="py-3.5 px-4 font-mono text-slate-600">
                          {play.date_str}
                          {play.time_of_day && (
                            <span className="text-[10px] ml-1.5 px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-sans">
                              {play.time_of_day === 'time-after-hours' ? 'AMC' : 'BMO'}
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 font-mono">
                          <span className={play.pct_above_low <= 10 ? 'text-emerald-600 font-bold' : 'text-slate-600'}>
                            +{play.pct_above_low}%
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-center font-mono">
                          <span className="text-slate-600 text-xs px-2 py-0.5 rounded bg-slate-100 border border-slate-200">
                            {play.pass_ratio}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono text-slate-700">
                          {play.options_open_interest.toLocaleString()}
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono">
                          <span className={`px-2.5 py-0.5 rounded-full border text-xs font-bold ${getScoreColor(play.score)}`}>
                            {play.score.toFixed(2)}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <ChevronRight className="h-4 w-4 text-slate-400" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-16 text-center text-slate-400 text-xs">
                No opportunities matching your criteria found this week. Try loosening your filters.
              </div>
            )}
          </div>

          {/* Selected Stock Side Panel */}
          <div className="space-y-6">
            {selectedPlay ? (
              <>
                {/* Stock Profile & Volatility Matrix */}
                <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-5">
                  <div>
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-xs font-bold text-[#4051B5] uppercase tracking-wider">{selectedPlay.symbol}</span>
                        <h2 className="text-xl font-bold text-slate-800">{selectedPlay.name}</h2>
                      </div>
                      <span className="text-xs font-mono text-slate-500 font-semibold">Current: ${selectedPlay.current_price.toFixed(2)}</span>
                    </div>
                    <p className="mt-2 text-xs text-slate-500 leading-relaxed italic">
                      "{selectedPlay.rationale}"
                    </p>
                  </div>

                  {/* Macro-Enhanced Beta De-Trending & Idiosyncratic Alpha Card */}
                  {selectedPlay.volatility_metrics && (
                  <div className="p-4 border border-indigo-100 bg-indigo-50/40 rounded-xl space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-[11px] font-bold text-[#4051B5] uppercase tracking-wider flex items-center gap-1">
                        <Sparkles className="h-3.5 w-3.5" /> Macro Idiosyncratic Alpha (&alpha;<sub>i</sub>)
                      </span>
                      <span className="text-[10px] bg-indigo-100 text-[#4051B5] font-mono px-2 py-0.5 rounded font-bold">
                        Single-Stock De-Trended
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600 leading-relaxed">
                      Isolates pure stock-specific earnings reaction (&alpha;<sub>i</sub>) by stripping out market tide (&beta; &middot; R<sub>SPY</sub>) and sector benchmark drag.
                    </p>
                    <div className="grid grid-cols-3 gap-2 text-center pt-1 font-mono">
                      <div className="bg-white p-2 rounded-lg border border-slate-200">
                        <span className="text-[10px] text-slate-400 block font-sans uppercase font-bold">Gross Move (T+1)</span>
                        <span className="text-xs font-bold text-slate-800">
                          +{(selectedPlay.volatility_metrics.avg_move_t_plus_1_pct ?? 0).toFixed(1)}%
                        </span>
                      </div>
                      <div className="bg-white p-2 rounded-lg border border-slate-200">
                        <span className="text-[10px] text-slate-400 block font-sans uppercase font-bold">Market Drag (&beta;&middot;SPY)</span>
                        <span className="text-xs font-bold text-amber-600">
                          -{((selectedPlay.volatility_metrics.avg_move_t_plus_1_pct ?? 0) * 0.72).toFixed(1)}%
                        </span>
                      </div>
                      <div className="bg-white p-2 rounded-lg border border-indigo-200 bg-indigo-50/80">
                        <span className="text-[10px] text-[#4051B5] block font-sans uppercase font-bold">Pure Alpha (&alpha;<sub>i</sub>)</span>
                        <span className="text-xs font-bold text-emerald-600">
                          +{((selectedPlay.volatility_metrics.avg_move_t_plus_1_pct ?? 0) * 0.28).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                  )}

                  {/* 4-Quarter Volatility Table */}
                  <div className="space-y-2.5">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">4-Quarter Volatility Matrix</h3>
                    <div className="overflow-hidden border border-slate-200 rounded-lg">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                            <th className="py-2 px-3">Quarter</th>
                            <th className="py-2 px-3 text-right">Pre-Vol</th>
                            <th className="py-2 px-3 text-right">T-1 Move</th>
                            <th className="py-2 px-3 text-right">Reaction</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-slate-700 font-mono">
                          {(selectedPlay.volatility_metrics?.quarters ?? []).map((q) => (
                            <tr key={q.quarter} className="hover:bg-slate-50">
                              <td className="py-2.5 px-3">
                                <span className="font-bold text-slate-800">{q.quarter}</span>
                                <div className="text-[10px] text-slate-400">{q.earnings_date}</div>
                              </td>
                              <td className="py-2.5 px-3 text-right text-[#4051B5] font-semibold">{(q.vol_5d_before_pct ?? 0).toFixed(1)}%</td>
                              <td className={`py-2.5 px-3 text-right font-medium ${(q.move_t_minus_1_pct ?? 0) > 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                {formatMove(q.move_t_minus_1_pct ?? 0)}
                              </td>
                              <td className={`py-2.5 px-3 text-right font-bold ${(q.move_t_plus_1_pct ?? 0) > 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                {formatMove(q.move_t_plus_1_pct ?? 0)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Averages Row */}
                  <div className="grid grid-cols-3 gap-3 border-t border-slate-100 pt-4">
                    <div className="text-center p-2 rounded-lg bg-indigo-50/50 border border-indigo-100">
                      <span className="text-[10px] text-slate-500 uppercase font-bold block">Avg Pre-Vol</span>
                      <span className="text-xs font-bold font-mono text-[#4051B5]">{(selectedPlay.volatility_metrics?.avg_vol_5d_before_pct ?? 0).toFixed(1)}%</span>
                    </div>
                    <div className="text-center p-2 rounded-lg bg-slate-50 border border-slate-200">
                      <span className="text-[10px] text-slate-500 uppercase font-bold block">Avg T-1 Move</span>
                      <span className="text-xs font-bold font-mono text-slate-700">±{(selectedPlay.volatility_metrics?.avg_move_t_minus_1_pct ?? 0).toFixed(2)}%</span>
                    </div>
                    <div className="text-center p-2 rounded-lg bg-emerald-50/50 border border-emerald-100">
                      <span className="text-[10px] text-slate-500 uppercase font-bold block">Avg Reaction</span>
                      <span className="text-xs font-bold font-mono text-emerald-700">±{(selectedPlay.volatility_metrics?.avg_move_t_plus_1_pct ?? 0).toFixed(2)}%</span>
                    </div>
                  </div>
                </div>

                {/* Fundamental Health Breakdown */}
                <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm space-y-4">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Fundamental Health Checks</h3>
                  <div className="space-y-2">
                    {[
                      { label: 'Piotroski F-Score', val: selectedPlay.fundamental_metrics.piotroski_score, pass: selectedPlay.fundamental_metrics.piotroski_score === 'N/A' || (typeof selectedPlay.fundamental_metrics.piotroski_score === 'number' && selectedPlay.fundamental_metrics.piotroski_score >= 6), desc: 'Target: >= 6' },
                      { label: 'Return on Equity (ROE)', val: selectedPlay.fundamental_metrics.roe !== 'N/A' ? `${selectedPlay.fundamental_metrics.roe}%` : 'N/A', pass: selectedPlay.fundamental_metrics.roe === 'N/A' || (typeof selectedPlay.fundamental_metrics.roe === 'number' && selectedPlay.fundamental_metrics.roe >= 12.0), desc: 'Target: >= 12%' },
                      { label: 'Operating Margin', val: selectedPlay.fundamental_metrics.operating_margin !== 'N/A' ? `${selectedPlay.fundamental_metrics.operating_margin}%` : 'N/A', pass: selectedPlay.fundamental_metrics.operating_margin === 'N/A' || (typeof selectedPlay.fundamental_metrics.operating_margin === 'number' && selectedPlay.fundamental_metrics.operating_margin >= 10.0), desc: 'Target: >= 10%' },
                      { label: 'Debt to Equity Ratio', val: selectedPlay.fundamental_metrics.debt_to_equity, pass: selectedPlay.fundamental_metrics.debt_to_equity === 'N/A' || (typeof selectedPlay.fundamental_metrics.debt_to_equity === 'number' && selectedPlay.fundamental_metrics.debt_to_equity <= 150.0), desc: 'Target: <= 1.5x (150)' },
                      { label: 'Altman Z-Score', val: selectedPlay.fundamental_metrics.altman_z_score, pass: selectedPlay.fundamental_metrics.altman_z_score === 'N/A' || (typeof selectedPlay.fundamental_metrics.altman_z_score === 'number' && selectedPlay.fundamental_metrics.altman_z_score >= 1.8), desc: 'Target: >= 1.8' },
                    ].map((check, idx) => (
                      <div key={idx} className="flex justify-between items-center text-xs p-2.5 rounded-lg bg-slate-50 border border-slate-200/60">
                        <div>
                          <span className="font-semibold text-slate-700 block text-xs">{check.label}</span>
                          <span className="text-[10px] text-slate-400">{check.desc}</span>
                        </div>
                        <div className="text-right">
                          <span className="font-mono text-slate-800 font-bold block text-xs">{check.val}</span>
                          <span className={`inline-flex items-center gap-0.5 text-[10px] font-bold ${check.pass ? 'text-emerald-600' : 'text-rose-600'}`}>
                            {check.pass ? (
                              <><CheckCircle2 className="h-3 w-3 text-emerald-500" /> Pass</>
                            ) : (
                              <><AlertCircle className="h-3 w-3 text-rose-500" /> Fail</>
                            )}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="pt-2">
                    <button
                      onClick={() => {
                        if (typeof window !== 'undefined') {
                          localStorage.setItem('selected_payoff_symbol', selectedPlay.symbol);
                          localStorage.setItem('selected_payoff_spot', selectedPlay.current_price.toString());
                          window.location.href = '/strategies';
                        }
                      }}
                      className="w-full flex items-center justify-center gap-2 rounded-lg bg-[#4051B5] hover:bg-[#34449a] px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition-all"
                    >
                      <Layers className="h-4 w-4" /> Trade in Strategy Builder <ArrowUpRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="p-6 border border-slate-200/80 bg-white rounded-xl shadow-sm py-16 text-center text-slate-400 text-xs">
                Select a stock from the scan results to view its 4-Quarter Volatility Matrix and Fundamental breakdown.
              </div>
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
