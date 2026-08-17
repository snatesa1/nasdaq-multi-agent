'use client';

import React, { useState, useEffect } from 'react';
import { Briefcase, RefreshCw, Trash2, TrendingUp, TrendingDown, CloudDownload, Award, Layers, Activity, Info } from 'lucide-react';
import { optionsApi } from '@/lib/api';
import ProtectedRoute from '@/components/ProtectedRoute';

interface TickerData {
  symbol: string;
  price: number;
  change: number;
  high: number;
  low: number;
  volume: number;
}

interface Portfolio {
  id: string;
  name: string;
  source: string;
  tickers: TickerData[];
}

export default function PortfolioPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [customSheetId, setCustomSheetId] = useState('');
  
  // Analysis States
  const [analysisData, setAnalysisData] = useState<Record<string, any>>({});
  const [analyzing, setAnalyzing] = useState<Record<string, boolean>>({});

  const fetchPortfolios = async () => {
    setLoading(true);
    try {
      const data = await optionsApi.listPortfolios();
      setPortfolios(Array.isArray(data) ? data : data.portfolios || []);
    } catch (err) {
      console.error('Failed to load portfolios:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolios();
  }, []);

  const extractSheetId = (input: string) => {
    if (!input) return '';
    const match = input.match(/\/d\/([a-zA-Z0-9-_]+)/);
    return match ? match[1] : input.trim();
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const targetId = extractSheetId(customSheetId);
      await optionsApi.syncPortfolio(targetId || undefined);
      setCustomSheetId('');
      await fetchPortfolios();
    } catch (err) {
      console.error('Sync failed:', err);
    } finally {
      setSyncing(false);
    }
  };

  const handleAnalyze = async (portfolioId: string) => {
    setAnalyzing(prev => ({ ...prev, [portfolioId]: true }));
    try {
      const data = await optionsApi.analyzePortfolio(portfolioId);
      setAnalysisData(prev => ({ ...prev, [portfolioId]: data }));
    } catch (err) {
      console.error('Analysis failed:', err);
    } finally {
      setAnalyzing(prev => ({ ...prev, [portfolioId]: false }));
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await optionsApi.deletePortfolio(id);
      setPortfolios(prev => prev.filter(p => p.id !== id));
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  return (
    <ProtectedRoute>
      <div className="space-y-6 pb-12">
        {/* Banner Header - Velzon Light Theme */}
        <div className="relative overflow-hidden rounded-xl bg-white p-6 sm:p-8 border border-slate-200/80 shadow-sm flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-[#4051B5] border border-indigo-100">
              <Briefcase className="h-3.5 w-3.5" /> Saxo Account & Portfolio Sync
            </span>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight sm:text-3xl">
              Portfolio & <span className="text-[#4051B5]">Diversification Radar</span>
            </h1>
            <p className="text-slate-500 text-xs sm:text-sm leading-relaxed">
              Sync your active Saxo Bank holdings and Google Sheets spreadsheets. Perform cross-asset log return correlation analysis and Ray Dalio Holy Grail diversification scoring.
            </p>
          </div>
          
          <div className="flex items-center gap-3 flex-shrink-0">
            <input
              type="text"
              placeholder="Paste Google Sheet URL or ID..."
              value={customSheetId}
              onChange={(e) => setCustomSheetId(e.target.value)}
              className="rounded-lg bg-slate-50 border border-slate-200 px-3.5 py-2 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 w-60 font-medium"
            />
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-2 rounded-lg bg-[#4051B5] hover:bg-[#34449a] px-4 py-2 text-xs font-semibold text-white shadow-sm transition disabled:opacity-50 flex-shrink-0"
            >
              {syncing ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <CloudDownload className="h-4 w-4" />
              )}
              {syncing ? 'Syncing...' : customSheetId ? 'Sync Sheet' : 'Auto-Sync Drive'}
            </button>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="grid gap-6 md:grid-cols-2">
            {Array.from({ length: 2 }).map((_, idx) => (
              <div key={idx} className="p-6 h-48 animate-pulse bg-white border border-slate-200/80 rounded-xl" />
            ))}
          </div>
        ) : portfolios.length === 0 ? (
          <div className="p-12 text-center bg-white border border-slate-200/80 rounded-xl shadow-sm">
            <Briefcase className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h3 className="text-base font-bold text-slate-800">No Portfolios Found</h3>
            <p className="text-xs text-slate-500 mt-2 max-w-md mx-auto">
              Click &ldquo;Auto-Sync Drive&rdquo; to import your portfolio spreadsheets or link your active Saxo Bank OpenAPI account.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {portfolios.map((portfolio) => (
              <div key={portfolio.id} className="p-6 bg-white border border-slate-200/80 rounded-xl shadow-sm space-y-5">
                {/* Portfolio Header */}
                <div className="flex justify-between items-center border-b border-slate-100 pb-3">
                  <div>
                    <h3 className="text-base font-bold text-slate-800">{portfolio.name}</h3>
                    <span className="text-[11px] text-slate-400 font-mono">{portfolio.source}</span>
                  </div>
                  <button
                    onClick={() => handleDelete(portfolio.id)}
                    className="text-slate-400 hover:text-rose-600 transition p-1.5 rounded-lg hover:bg-rose-50"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                {/* Tickers Table */}
                {portfolio.tickers && portfolio.tickers.length > 0 ? (
                  <div className="space-y-4">
                    <div className="overflow-x-auto border border-slate-200 rounded-lg">
                      <table className="w-full text-left text-xs font-mono">
                        <thead className="bg-slate-50 text-slate-500 font-bold uppercase border-b border-slate-200 sticky top-0">
                          <tr>
                            <th className="p-3">Symbol</th>
                            <th className="p-3">Price</th>
                            <th className="p-3">Change</th>
                            <th className="p-3">High</th>
                            <th className="p-3">Low</th>
                            <th className="p-3">Volume</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {portfolio.tickers.map((ticker) => (
                            <tr key={ticker.symbol} className="hover:bg-slate-50">
                              <td className="p-3 text-slate-800 font-bold">{ticker.symbol}</td>
                              <td className="p-3 text-slate-700">${ticker.price?.toFixed(2) ?? '—'}</td>
                              <td className={`p-3 font-bold flex items-center gap-1 ${
                                (ticker.change ?? 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'
                              }`}>
                                {(ticker.change ?? 0) >= 0 ? (
                                  <TrendingUp className="h-3.5 w-3.5" />
                                ) : (
                                  <TrendingDown className="h-3.5 w-3.5" />
                                )}
                                {(ticker.change ?? 0) >= 0 ? '+' : ''}{ticker.change?.toFixed(2) ?? '0.00'}%
                              </td>
                              <td className="p-3 text-slate-500">${ticker.high?.toFixed(2) ?? '—'}</td>
                              <td className="p-3 text-slate-500">${ticker.low?.toFixed(2) ?? '—'}</td>
                              <td className="p-3 text-slate-500">{ticker.volume?.toLocaleString() ?? '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Action Bar */}
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-indigo-50/40 p-4 rounded-xl border border-indigo-100">
                      <div className="flex items-center gap-2 text-xs text-slate-600">
                        <Info className="h-4 w-4 text-[#4051B5] flex-shrink-0" />
                        <span>Perform sector diversification & cross-asset correlation analysis.</span>
                      </div>
                      <button
                        onClick={() => handleAnalyze(portfolio.id)}
                        disabled={analyzing[portfolio.id]}
                        className="flex items-center gap-2 rounded-lg bg-[#4051B5] hover:bg-[#34449a] px-4 py-2 text-xs font-semibold text-white shadow-sm transition disabled:opacity-50 flex-shrink-0"
                      >
                        {analyzing[portfolio.id] ? (
                          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Activity className="h-3.5 w-3.5" />
                        )}
                        {analyzing[portfolio.id] ? 'Analyzing...' : 'Run Diversification Analysis'}
                      </button>
                    </div>

                    {/* Analysis Report Section */}
                    {analysisData[portfolio.id] && (
                      <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-6 mt-4 shadow-sm">
                        <div className="flex justify-between items-center border-b border-slate-100 pb-3">
                          <h4 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                            <Award className="h-4 w-4 text-emerald-600" /> Diversification & Validation Report
                          </h4>
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Score:</span>
                            <span className={`text-xs font-extrabold px-2.5 py-0.5 rounded-full border ${
                              analysisData[portfolio.id].diversification_score >= 80 ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                              analysisData[portfolio.id].diversification_score >= 60 ? 'bg-amber-50 text-amber-700 border-amber-200' :
                              'bg-rose-50 text-rose-700 border-rose-200'
                            }`}>
                              {analysisData[portfolio.id].diversification_score}/100
                            </span>
                          </div>
                        </div>

                        {/* Allocations & Metrics Grid */}
                        <div className="grid gap-6 md:grid-cols-2">
                          {/* Sector Allocation */}
                          <div className="space-y-3">
                            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                              <Layers className="h-3.5 w-3.5 text-[#4051B5]" /> Sector Exposure
                            </span>
                            <div className="space-y-2.5">
                              {analysisData[portfolio.id].sector_allocations.map((alloc: any, idx: number) => (
                                <div key={idx} className="space-y-1">
                                  <div className="flex justify-between text-[11px] font-mono">
                                    <span className="text-slate-700 font-medium">{alloc.sector}</span>
                                    <span className="text-slate-500 font-semibold">{alloc.count} ({alloc.percentage}%)</span>
                                  </div>
                                  <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                                    <div 
                                      className="h-full bg-[#4051B5]"
                                      style={{ width: `${alloc.percentage}%` }}
                                    />
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Asset Class Allocation & Correlation metrics */}
                          <div className="space-y-6">
                            <div className="space-y-3">
                              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                                <Briefcase className="h-3.5 w-3.5 text-[#4051B5]" /> Asset Class Exposure
                              </span>
                              <div className="grid grid-cols-2 gap-3">
                                {analysisData[portfolio.id].asset_class_allocations.map((alloc: any, idx: number) => (
                                  <div key={idx} className="bg-slate-50 p-3 rounded-lg border border-slate-200/60 flex flex-col justify-between">
                                    <span className="text-[10px] text-slate-400 font-mono truncate">{alloc.asset_class}</span>
                                    <span className="text-xs font-bold text-slate-800 mt-1">{alloc.count} ({alloc.percentage}%)</span>
                                  </div>
                                ))}
                              </div>
                            </div>

                            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200/60 space-y-2">
                              <div className="flex justify-between items-center text-xs">
                                <span className="text-slate-600 font-semibold">Average Asset Correlation:</span>
                                <span className={`font-mono font-bold ${
                                  analysisData[portfolio.id].average_correlation < 0.2 ? 'text-emerald-600' :
                                  analysisData[portfolio.id].average_correlation < 0.4 ? 'text-slate-800' :
                                  'text-rose-600'
                                }`}>
                                  {analysisData[portfolio.id].average_correlation}
                                </span>
                              </div>
                              <p className="text-[11px] text-slate-500 leading-normal">
                                Ray Dalio’s Holy Grail diversification targets an average correlation of &lt; 0.20 to maximize risk reduction.
                              </p>
                            </div>
                          </div>
                        </div>

                        {/* Recommendations & Correlation Warnings */}
                        <div className="grid gap-6 md:grid-cols-2 border-t border-slate-100 pt-4">
                          <div className="space-y-2">
                            <span className="text-[10px] text-amber-700 font-bold uppercase tracking-wider block">Correlation Warnings</span>
                            <ul className="space-y-1.5">
                              {analysisData[portfolio.id].correlation_warnings.map((w: string, idx: number) => (
                                <li key={idx} className="text-[11px] text-slate-600 leading-normal flex items-start gap-1.5">
                                  <span className="text-amber-500 font-bold mt-0.5">•</span>
                                  <span>{w}</span>
                                </li>
                              ))}
                            </ul>
                          </div>

                          <div className="space-y-2">
                            <span className="text-[10px] text-[#4051B5] font-bold uppercase tracking-wider block">Strategic Recommendations</span>
                            <ul className="space-y-1.5">
                              {analysisData[portfolio.id].recommendations.map((r: string, idx: number) => (
                                <li key={idx} className="text-[11px] text-slate-600 leading-normal flex items-start gap-1.5">
                                  <span className="text-[#4051B5] font-bold mt-0.5">•</span>
                                  <span>{r}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 text-center py-4">No tickers in this portfolio.</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
