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
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <Briefcase className="h-6 w-6 text-[#5ba4b5]" /> Portfolio Tracker
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Sync your portfolios from Google Sheets and track live market data.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="text"
              placeholder="Paste Google Sheet URL or ID..."
              value={customSheetId}
              onChange={(e) => setCustomSheetId(e.target.value)}
              className="rounded-lg bg-slate-950 border border-slate-800 px-4 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-[#5ba4b5] w-64 transition duration-200"
            />
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-2 rounded-lg bg-[#5ba4b5] hover:bg-[#4a91a2] px-5 py-2 text-sm font-semibold text-slate-900 transition duration-200 disabled:opacity-50 flex-shrink-0"
            >
              {syncing ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <CloudDownload className="h-4 w-4" />
              )}
              {syncing ? 'Syncing...' : customSheetId ? 'Sync Specific Sheet' : 'Auto-Sync Drive'}
            </button>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="grid gap-6 md:grid-cols-2">
            {Array.from({ length: 2 }).map((_, idx) => (
              <div key={idx} className="glass-card p-6 h-48 animate-pulse bg-slate-900/30 border border-slate-800 rounded-lg" />
            ))}
          </div>
        ) : portfolios.length === 0 ? (
          <div className="glass-card p-12 text-center">
            <Briefcase className="h-12 w-12 text-slate-700 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-300">No Portfolios Found</h3>
            <p className="text-sm text-slate-500 mt-2 max-w-md mx-auto">
              Click &ldquo;Sync from Google Drive&rdquo; to import your portfolio spreadsheets, or create a portfolio manually.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {portfolios.map((portfolio) => (
              <div key={portfolio.id} className="glass-card p-6 space-y-4">
                {/* Portfolio Header */}
                <div className="flex justify-between items-center border-b border-slate-800 pb-3">
                  <div>
                    <h3 className="text-md font-bold text-slate-200">{portfolio.name}</h3>
                    <span className="text-[10px] text-slate-500 font-mono">{portfolio.source}</span>
                  </div>
                  <button
                    onClick={() => handleDelete(portfolio.id)}
                    className="text-slate-600 hover:text-red-400 transition p-1.5 rounded hover:bg-red-500/10"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                {/* Tickers Table */}
                {portfolio.tickers && portfolio.tickers.length > 0 ? (
                  <div className="space-y-4">
                    <div className="overflow-x-auto border border-slate-800 rounded-lg">
                      <table className="w-full text-left text-xs font-mono">
                        <thead className="bg-[#12141a]/90 text-slate-400 sticky top-0">
                          <tr>
                            <th className="p-3">Symbol</th>
                            <th className="p-3">Price</th>
                            <th className="p-3">Change</th>
                            <th className="p-3">High</th>
                            <th className="p-3">Low</th>
                            <th className="p-3">Volume</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50 bg-[#161924]/30">
                          {portfolio.tickers.map((ticker) => (
                            <tr key={ticker.symbol} className="hover:bg-slate-800/30">
                              <td className="p-3 text-slate-200 font-semibold">{ticker.symbol}</td>
                              <td className="p-3 text-slate-200">${ticker.price?.toFixed(2) ?? '—'}</td>
                              <td className={`p-3 font-semibold flex items-center gap-1 ${
                                (ticker.change ?? 0) >= 0 ? 'text-[#7ec8a0]' : 'text-[#dc3545]'
                              }`}>
                                {(ticker.change ?? 0) >= 0 ? (
                                  <TrendingUp className="h-3 w-3" />
                                ) : (
                                  <TrendingDown className="h-3 w-3" />
                                )}
                                {(ticker.change ?? 0) >= 0 ? '+' : ''}{ticker.change?.toFixed(2) ?? '0.00'}%
                              </td>
                              <td className="p-3 text-slate-400">${ticker.high?.toFixed(2) ?? '—'}</td>
                              <td className="p-3 text-slate-400">${ticker.low?.toFixed(2) ?? '—'}</td>
                              <td className="p-3 text-slate-400">{ticker.volume?.toLocaleString() ?? '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Action Bar */}
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-[#12141a]/40 p-4 rounded-xl border border-slate-800/60">
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <Info className="h-4 w-4 text-[#5ba4b5] flex-shrink-0" />
                        <span>Perform sector diversification & rolling correlation analysis.</span>
                      </div>
                      <button
                        onClick={() => handleAnalyze(portfolio.id)}
                        disabled={analyzing[portfolio.id]}
                        className="flex items-center gap-2 rounded-lg bg-[#5ba4b5]/15 border border-[#5ba4b5]/30 hover:bg-[#5ba4b5]/25 px-4 py-2 text-xs font-semibold text-[#5ba4b5] transition disabled:opacity-50 flex-shrink-0"
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
                      <div className="rounded-xl border border-slate-800 bg-[#12141a]/60 p-6 space-y-6 mt-4">
                        <div className="flex justify-between items-center border-b border-slate-800 pb-3">
                          <h4 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                            <Award className="h-4 w-4 text-[#7ec8a0]" /> Diversification & Validation Report
                          </h4>
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Score:</span>
                            <span className={`text-sm font-bold px-2 py-0.5 rounded-full ${
                              analysisData[portfolio.id].diversification_score >= 80 ? 'bg-[#7ec8a0]/15 text-[#7ec8a0]' :
                              analysisData[portfolio.id].diversification_score >= 60 ? 'bg-[#ffc107]/15 text-[#ffc107]' :
                              'bg-[#dc3545]/15 text-[#dc3545]'
                            }`}>
                              {analysisData[portfolio.id].diversification_score}/100
                            </span>
                          </div>
                        </div>

                        {/* Allocations & Metrics Grid */}
                        <div className="grid gap-6 md:grid-cols-2">
                          {/* Sector Allocation */}
                          <div className="space-y-3">
                            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider flex items-center gap-1.5">
                              <Layers className="h-3.5 w-3.5" /> Sector Exposure
                            </span>
                            <div className="space-y-2.5">
                              {analysisData[portfolio.id].sector_allocations.map((alloc: any, idx: number) => (
                                <div key={idx} className="space-y-1">
                                  <div className="flex justify-between text-[11px] font-mono">
                                    <span className="text-slate-300">{alloc.sector}</span>
                                    <span className="text-slate-400 font-semibold">{alloc.count} ({alloc.percentage}%)</span>
                                  </div>
                                  <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden">
                                    <div 
                                      className="h-full bg-gradient-to-r from-[#5ba4b5] to-[#7ec8a0]"
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
                              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider flex items-center gap-1.5">
                                <Briefcase className="h-3.5 w-3.5" /> Asset Class Exposure
                              </span>
                              <div className="grid grid-cols-2 gap-3">
                                {analysisData[portfolio.id].asset_class_allocations.map((alloc: any, idx: number) => (
                                  <div key={idx} className="bg-slate-950/40 p-3 rounded-lg border border-slate-900 flex flex-col justify-between">
                                    <span className="text-[10px] text-slate-500 font-mono truncate">{alloc.asset_class}</span>
                                    <span className="text-xs font-bold text-slate-200 mt-1">{alloc.count} ({alloc.percentage}%)</span>
                                  </div>
                                ))}
                              </div>
                            </div>

                            <div className="bg-slate-950/40 p-4 rounded-lg border border-slate-900 space-y-2">
                              <div className="flex justify-between items-center text-xs">
                                <span className="text-slate-400 font-mono">Average Asset Correlation:</span>
                                <span className={`font-bold ${
                                  analysisData[portfolio.id].average_correlation < 0.2 ? 'text-[#7ec8a0]' :
                                  analysisData[portfolio.id].average_correlation < 0.4 ? 'text-slate-300' :
                                  'text-[#dc3545]'
                                }`}>
                                  {analysisData[portfolio.id].average_correlation}
                                </span>
                              </div>
                              <p className="text-[10px] text-slate-500 leading-normal">
                                Ray Dalio’s Holy Grail diversification targets an average correlation of &lt; 0.20 to maximize risk reduction.
                              </p>
                            </div>
                          </div>
                        </div>

                        {/* Recommendations & Correlation Warnings */}
                        <div className="grid gap-6 md:grid-cols-2 border-t border-slate-800 pt-4">
                          {/* Warnings */}
                          <div className="space-y-2">
                            <span className="text-[10px] text-[#ffc107] font-bold uppercase tracking-wider block">Correlation Warnings</span>
                            <ul className="space-y-1.5">
                              {analysisData[portfolio.id].correlation_warnings.map((w: string, idx: number) => (
                                <li key={idx} className="text-[11px] text-slate-400 leading-normal flex items-start gap-1.5">
                                  <span className="text-[#ffc107] mt-0.5">•</span>
                                  <span>{w}</span>
                                </li>
                              ))}
                            </ul>
                          </div>

                          {/* Recommendations */}
                          <div className="space-y-2">
                            <span className="text-[10px] text-[#5ba4b5] font-bold uppercase tracking-wider block">Strategic Recommendations</span>
                            <ul className="space-y-1.5">
                              {analysisData[portfolio.id].recommendations.map((r: string, idx: number) => (
                                <li key={idx} className="text-[11px] text-slate-400 leading-normal flex items-start gap-1.5">
                                  <span className="text-[#5ba4b5] mt-0.5">•</span>
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
                  <p className="text-xs text-slate-500 text-center py-4">No tickers in this portfolio.</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
