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
  RefreshCw
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
    if (score >= 0.8) return 'text-emerald-400 bg-emerald-950/40 border-emerald-800';
    if (score >= 0.6) return 'text-[#5ba4b5] bg-[#5ba4b5]/10 border-[#5ba4b5]/30';
    return 'text-amber-400 bg-amber-950/40 border-amber-900';
  };

  const formatMove = (move: number) => {
    const sign = move > 0 ? '+' : '';
    return `${sign}${move.toFixed(2)}%`;
  };

  return (
    <ProtectedRoute>
      <div className="space-y-8 pb-12">
        {/* Banner Header */}
        <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-[#1e2538] to-[#141824] p-8 border border-slate-800">
          <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-[#5ba4b5]/5 blur-3xl" />
          <div className="relative z-10 max-w-3xl space-y-4">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-[#5ba4b5]/10 px-3 py-1 text-xs font-semibold text-[#5ba4b5]">
              <Calendar className="h-3 w-3" /> Q2 Earnings Volatility Playbook
            </span>
            <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight sm:text-4xl">
              Earnings Volatility <span className="text-[#5ba4b5]">Scanner</span>
            </h1>
            <p className="text-slate-400 text-sm sm:text-base leading-relaxed">
              Screen upcoming earnings for deep-value, high-quality stocks that are currently close to their 52-week lows and have liquid options chains. Review historical pre-earnings and post-earnings volatility profiles to design high-probability option buying strategies.
            </p>
          </div>
        </div>

        {/* Configuration Controls */}
        <div className="grid gap-6 md:grid-cols-4 items-end glass-card p-6 bg-[#161924]/60 border border-slate-800 rounded-xl">
          <div className="space-y-2 col-span-2">
            <div className="flex justify-between items-center text-sm">
              <label className="text-slate-300 font-medium flex items-center gap-1.5">
                <Sliders className="h-4 w-4 text-[#5ba4b5]" /> Max Proximity to 52-Week Low
              </label>
              <span className="text-slate-100 font-mono font-semibold">{lowThreshold}%</span>
            </div>
            <input 
              type="range" 
              min="5" 
              max="40" 
              value={lowThreshold} 
              onChange={(e) => setLowThreshold(parseInt(e.target.value))}
              disabled={scanning}
              className="w-full h-1.5 rounded bg-slate-800 accent-[#5ba4b5] cursor-pointer"
            />
          </div>

          <div className="space-y-2 col-span-1">
            <label className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">
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
                  // Only allow digits
                  const cleanVal = val.replace(/[^0-9]/g, '');
                  setMinOpenInterest(cleanVal ? parseInt(cleanVal, 10) : '');
                }
              }}
              disabled={scanning}
              className="w-full bg-[#0e1017] border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-[#5ba4b5] font-mono"
            />
          </div>

          <div className="col-span-1">
            <button
              onClick={handleScan}
              disabled={scanning}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-[#5ba4b5] px-4 py-2.5 text-sm font-semibold text-slate-900 transition hover:bg-[#4a91a2] disabled:opacity-50"
            >
              {scanning ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" /> Scanning...
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
          <div className="flex items-center gap-3 p-4 rounded-lg bg-rose-950/20 border border-rose-900/40 text-rose-300 text-sm">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Scan Summary Cards */}
        {results && !scanning && (
          <div className="grid gap-6 grid-cols-2 md:grid-cols-5">
            {[
              { label: 'Total Scraped', val: results.total_earners_scraped, desc: 'Next week earners' },
              { label: 'Universe Earner', val: results.universe_earners, desc: 'NASDAQ / S&P 500' },
              { label: 'Passed 52W Low', val: results.passed_52w_low, desc: `Within ${lowThreshold}%` },
              { label: 'Exhaustive Fund', val: results.passed_fundamentals, desc: 'Passed >=75% checks' },
              { label: 'Liquid Options', val: results.passed_liquidity, desc: `OI >= ${minOpenInterest.toLocaleString()}` },
            ].map((stat, idx) => (
              <div key={idx} className="glass-card p-4 bg-[#161924]/40 border border-slate-800 rounded-lg flex flex-col justify-between">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{stat.label}</span>
                <span className="text-2xl font-bold font-mono text-slate-100 my-1">{stat.val}</span>
                <span className="text-[10px] text-slate-400">{stat.desc}</span>
              </div>
            ))}
          </div>
        )}

        {/* Main Content Layout */}
        <div className="grid gap-8 lg:grid-cols-3">
          {/* Table List of Plays */}
          <div className="glass-card lg:col-span-2 p-6 border border-slate-800 bg-[#161924]/30 rounded-xl space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-bold text-slate-200 flex items-center gap-2">
                <Activity className="h-5 w-5 text-[#5ba4b5]" /> Ranked Earnings Opportunities
              </h2>
              {results && (
                <span className="text-xs text-slate-500 font-mono">Scan complete: {results.scan_timestamp}</span>
              )}
            </div>

            {scanning ? (
              <div className="space-y-4 py-12">
                <div className="flex justify-center items-center">
                  <RefreshCw className="h-8 w-8 text-[#5ba4b5] animate-spin" />
                </div>
                <p className="text-center text-slate-400 text-sm">Querying upcoming calendar, screening 52W lows, verifying balance sheets and checking option chain liquidity...</p>
              </div>
            ) : results && results.plays && results.plays.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-xs font-bold text-slate-400 tracking-wider">
                      <th className="py-3 px-4">Symbol</th>
                      <th className="py-3 px-4">Earnings Date</th>
                      <th className="py-3 px-4">52W Low Prox</th>
                      <th className="py-3 px-4 text-center">Quality</th>
                      <th className="py-3 px-4 text-right">Option OI</th>
                      <th className="py-3 px-4 text-right">Score</th>
                      <th className="py-3 px-4"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40 text-sm">
                    {results.plays.map((play) => (
                      <tr 
                        key={play.symbol}
                        onClick={() => setSelectedPlay(play)}
                        className={`hover:bg-[#1a1d28]/60 cursor-pointer transition-all duration-200 ${
                          selectedPlay?.symbol === play.symbol ? 'bg-[#5ba4b5]/5 border-l-2 border-[#5ba4b5]' : ''
                        }`}
                      >
                        <td className="py-4 px-4">
                          <div className="font-bold text-slate-200 font-mono">{play.symbol}</div>
                          <div className="text-xs text-slate-400 truncate max-w-[140px]">{play.name}</div>
                        </td>
                        <td className="py-4 px-4 font-mono text-slate-300">
                          {play.date_str}
                          {play.time_of_day && (
                            <span className="text-[10px] ml-1.5 px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                              {play.time_of_day === 'time-after-hours' ? 'AMC' : 'BMO'}
                            </span>
                          )}
                        </td>
                        <td className="py-4 px-4 font-mono">
                          <span className={play.pct_above_low <= 10 ? 'text-[#7ec8a0] font-semibold' : 'text-slate-300'}>
                            +{play.pct_above_low}%
                          </span>
                        </td>
                        <td className="py-4 px-4 text-center font-mono">
                          <span className="text-slate-400 text-xs px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                            {play.pass_ratio}
                          </span>
                        </td>
                        <td className="py-4 px-4 text-right font-mono text-slate-300">
                          {play.options_open_interest.toLocaleString()}
                        </td>
                        <td className="py-4 px-4 text-right font-mono">
                          <span className={`px-2.5 py-0.5 rounded-full border text-xs font-bold ${getScoreColor(play.score)}`}>
                            {play.score.toFixed(2)}
                          </span>
                        </td>
                        <td className="py-4 px-4 text-right">
                          <ChevronRight className="h-4 w-4 text-slate-500" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-16 text-center text-slate-500 text-sm">
                No opportunities matching your criteria found this week. Try loosening your filters.
              </div>
            )}
          </div>

          {/* Selected Stock Side Panel */}
          <div className="space-y-6">
            {selectedPlay ? (
              <>
                {/* Stock Profile & Volatility Matrix */}
                <div className="glass-card p-6 border border-slate-800 bg-[#161924]/30 rounded-xl space-y-6">
                  <div>
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-xs font-bold text-[#5ba4b5] uppercase tracking-wider">{selectedPlay.symbol}</span>
                        <h2 className="text-xl font-bold text-slate-100">{selectedPlay.name}</h2>
                      </div>
                      <span className="text-xs font-mono text-slate-400">Current: ${selectedPlay.current_price.toFixed(2)}</span>
                    </div>
                    <p className="mt-2 text-xs text-slate-400 leading-relaxed italic">
                      "{selectedPlay.rationale}"
                    </p>
                  </div>

                  {/* 4-Quarter Volatility Table */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">4-Quarter Volatility Matrix</h3>
                    <div className="overflow-hidden border border-slate-800/80 rounded-lg">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="bg-slate-900/60 border-b border-slate-800 text-slate-400 font-bold uppercase tracking-wider">
                            <th className="py-2 px-3">Quarter</th>
                            <th className="py-2 px-3 text-right">Pre-Vol</th>
                            <th className="py-2 px-3 text-right">T-1 Move</th>
                            <th className="py-2 px-3 text-right">Reaction</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/40 text-slate-300 font-mono">
                          {selectedPlay.volatility_metrics.quarters.map((q) => (
                            <tr key={q.quarter} className="hover:bg-slate-800/20">
                              <td className="py-2.5 px-3">
                                <span className="font-bold text-slate-300">{q.quarter}</span>
                                <div className="text-[10px] text-slate-500">{q.earnings_date}</div>
                              </td>
                              <td className="py-2.5 px-3 text-right text-[#5ba4b5]">{q.vol_5d_before_pct.toFixed(1)}%</td>
                              <td className={`py-2.5 px-3 text-right ${q.move_t_minus_1_pct > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {formatMove(q.move_t_minus_1_pct)}
                              </td>
                              <td className={`py-2.5 px-3 text-right font-bold ${q.move_t_plus_1_pct > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {formatMove(q.move_t_plus_1_pct)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Averages Row */}
                  <div className="grid grid-cols-3 gap-4 border-t border-slate-800/60 pt-4">
                    <div className="text-center p-2 rounded bg-slate-900/40 border border-slate-800/80">
                      <span className="text-[9px] text-slate-500 uppercase font-bold tracking-wider block">Avg Pre-Vol</span>
                      <span className="text-sm font-bold font-mono text-[#5ba4b5]">{selectedPlay.volatility_metrics.avg_vol_5d_before_pct.toFixed(1)}%</span>
                    </div>
                    <div className="text-center p-2 rounded bg-slate-900/40 border border-slate-800/80">
                      <span className="text-[9px] text-slate-500 uppercase font-bold tracking-wider block">Avg T-1 Move</span>
                      <span className="text-sm font-bold font-mono text-slate-300">±{selectedPlay.volatility_metrics.avg_move_t_minus_1_pct.toFixed(2)}%</span>
                    </div>
                    <div className="text-center p-2 rounded bg-slate-900/40 border border-slate-800/80">
                      <span className="text-[9px] text-slate-500 uppercase font-bold tracking-wider block">Avg Reaction</span>
                      <span className="text-sm font-bold font-mono text-[#7ec8a0]">±{selectedPlay.volatility_metrics.avg_move_t_plus_1_pct.toFixed(2)}%</span>
                    </div>
                  </div>
                </div>

                {/* Fundamental Health Breakdown */}
                <div className="glass-card p-6 border border-slate-800 bg-[#161924]/30 rounded-xl space-y-4">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Fundamental Health Checks</h3>
                  <div className="space-y-2.5">
                    {[
                      { label: 'Piotroski F-Score', val: selectedPlay.fundamental_metrics.piotroski_score, pass: selectedPlay.fundamental_metrics.piotroski_score === 'N/A' || (typeof selectedPlay.fundamental_metrics.piotroski_score === 'number' && selectedPlay.fundamental_metrics.piotroski_score >= 6), desc: 'Target: >= 6' },
                      { label: 'Return on Equity (ROE)', val: selectedPlay.fundamental_metrics.roe !== 'N/A' ? `${selectedPlay.fundamental_metrics.roe}%` : 'N/A', pass: selectedPlay.fundamental_metrics.roe === 'N/A' || (typeof selectedPlay.fundamental_metrics.roe === 'number' && selectedPlay.fundamental_metrics.roe >= 12.0), desc: 'Target: >= 12%' },
                      { label: 'Operating Margin', val: selectedPlay.fundamental_metrics.operating_margin !== 'N/A' ? `${selectedPlay.fundamental_metrics.operating_margin}%` : 'N/A', pass: selectedPlay.fundamental_metrics.operating_margin === 'N/A' || (typeof selectedPlay.fundamental_metrics.operating_margin === 'number' && selectedPlay.fundamental_metrics.operating_margin >= 10.0), desc: 'Target: >= 10%' },
                      { label: 'Debt to Equity Ratio', val: selectedPlay.fundamental_metrics.debt_to_equity, pass: selectedPlay.fundamental_metrics.debt_to_equity === 'N/A' || (typeof selectedPlay.fundamental_metrics.debt_to_equity === 'number' && selectedPlay.fundamental_metrics.debt_to_equity <= 150.0), desc: 'Target: <= 1.5x (150)' },
                      { label: 'Altman Z-Score', val: selectedPlay.fundamental_metrics.altman_z_score, pass: selectedPlay.fundamental_metrics.altman_z_score === 'N/A' || (typeof selectedPlay.fundamental_metrics.altman_z_score === 'number' && selectedPlay.fundamental_metrics.altman_z_score >= 1.8), desc: 'Target: >= 1.8' },
                    ].map((check, idx) => (
                      <div key={idx} className="flex justify-between items-center text-xs p-2 rounded bg-slate-900/20 border border-slate-800/40">
                        <div>
                          <span className="font-semibold text-slate-300 block">{check.label}</span>
                          <span className="text-[10px] text-slate-500">{check.desc}</span>
                        </div>
                        <div className="text-right">
                          <span className="font-mono text-slate-200 font-bold block">{check.val}</span>
                          <span className={`inline-flex items-center gap-0.5 text-[9px] font-bold ${check.pass ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {check.pass ? (
                              <><CheckCircle2 className="h-2.5 w-2.5" /> Pass</>
                            ) : (
                              <><AlertCircle className="h-2.5 w-2.5" /> Fail</>
                            )}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* strategy redirect button */}
                  <div className="pt-2">
                    <button
                      onClick={() => {
                        // Store symbol in localStorage to load in simulation tab
                        if (typeof window !== 'undefined') {
                          localStorage.setItem('selected_payoff_symbol', selectedPlay.symbol);
                          localStorage.setItem('selected_payoff_spot', selectedPlay.current_price.toString());
                          window.location.href = '/strategies';
                        }
                      }}
                      className="w-full flex items-center justify-center gap-2 rounded-lg border border-[#5ba4b5]/30 hover:border-[#5ba4b5] bg-[#5ba4b5]/10 px-4 py-2.5 text-sm font-semibold text-[#5ba4b5] transition-all"
                    >
                      <Layers className="h-4 w-4" /> Trade in Strategy Builder <ArrowUpRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="glass-card p-6 border border-slate-800 bg-[#161924]/30 rounded-xl py-12 text-center text-slate-500 text-sm">
                Select a stock from the scan results to view its 4-Quarter Volatility Matrix and Fundamental breakdown.
              </div>
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
