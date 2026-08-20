'use client';

import React, { useState } from 'react';
import { Bot, Play, Loader, AlertCircle } from 'lucide-react';
import { optionsApi } from '@/lib/api';
import ProtectedRoute from '@/components/ProtectedRoute';

export default function MarketAgentsPage() {
  const [tickersInput, setTickersInput] = useState('AAPL, NVDA, TSLA, PANW, MSFT');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunAnalysis = async () => {
    const tickers = tickersInput
      .split(',')
      .map(t => t.trim().toUpperCase())
      .filter(t => t.length > 0);

    if (tickers.length === 0) {
      setError('Please enter at least one ticker symbol.');
      return;
    }

    setRunning(true);
    setError(null);
    setResult(null);

    try {
      const data = await optionsApi.runAnalysis(tickers);
      setResult(data);
    } catch (err: any) {
      console.error('Analysis failed:', err);
      setError(err.message || 'Analysis pipeline failed. Please try again.');
    } finally {
      setRunning(false);
    }
  };

  return (
    <ProtectedRoute>
      <div className="space-y-6 pb-12">
        {/* Banner Header - Velzon Light Theme */}
        <div className="relative overflow-hidden rounded-xl bg-white p-6 sm:p-8 border border-slate-200/80 shadow-sm">
          <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-indigo-50/60 blur-2xl" />
          <div className="relative z-10 max-w-3xl space-y-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-[#4051B5] border border-indigo-100">
              <Bot className="h-3.5 w-3.5" /> Hierarchical Multi-Agent System
            </span>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight sm:text-3xl">
              Market Intelligence <span className="text-[#4051B5]">Agents</span>
            </h1>
            <p className="text-slate-500 text-xs sm:text-sm leading-relaxed">
              Run the multi-agent pipeline (Macro, Fundamental, Technical, Correlation, and News Sentiment agents) across candidate tickers or custom stock universes.
            </p>
          </div>
        </div>

        {/* Input Section */}
        <div className="p-6 bg-white border border-slate-200/80 rounded-xl shadow-sm space-y-4">
          <h3 className="text-base font-bold text-slate-800">Analysis Configuration</h3>
          <div>
            <label className="text-[11px] text-slate-400 font-bold block mb-2 uppercase tracking-wider">
              Ticker Symbols (comma-separated)
            </label>
            <input
              type="text"
              value={tickersInput}
              onChange={(e) => setTickersInput(e.target.value)}
              placeholder="AAPL, NVDA, TSLA, PANW..."
              className="w-full rounded-lg px-4 py-3 text-xs bg-slate-50 border border-slate-200 text-slate-800 font-mono font-medium placeholder:text-slate-400 focus:ring-2 focus:ring-indigo-500 focus:outline-none transition"
            />
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={handleRunAnalysis}
              disabled={running}
              className="flex items-center gap-2 rounded-lg bg-[#4051B5] hover:bg-[#34449a] px-6 py-2.5 text-xs font-semibold text-white shadow-sm transition disabled:opacity-50"
            >
              {running ? (
                <Loader className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {running ? 'Running Analysis...' : 'Run Analysis'}
            </button>

            {running && (
              <span className="text-xs text-slate-500 animate-pulse font-medium">
                Multi-agent pipeline in progress — processing technicals, macro, and news sentiment...
              </span>
            )}
          </div>

          {error && (
            <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 flex items-start gap-3 text-rose-700 text-xs font-medium">
              <AlertCircle className="h-4 w-4 text-rose-500 flex-shrink-0 mt-0.5" />
              <p>{error}</p>
            </div>
          )}
        </div>

        {/* Results Section */}
        {running && (
          <div className="p-12 text-center bg-white border border-slate-200/80 rounded-xl shadow-sm space-y-3">
            <Loader className="h-8 w-8 text-[#4051B5] animate-spin mx-auto" />
            <h3 className="text-base font-bold text-slate-800">Agents Analyzing Universe...</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Fundamental, Technical, Macro, Correlation, and Sentiment agents are generating institutional conviction metrics.
            </p>
          </div>
        )}

        {result && !running && (
          <div className="space-y-6">
            <h3 className="text-base font-bold text-slate-800">Analysis Results</h3>

            {/* If result has structured data, render cards */}
            {typeof result === 'object' && !Array.isArray(result) && result.report ? (
              <div className="p-6 bg-white border border-slate-200/80 rounded-xl shadow-sm space-y-3">
                <h4 className="text-sm font-bold text-slate-800">Composite Institutional Report</h4>
                <div className="text-xs text-slate-600 leading-relaxed whitespace-pre-line font-sans">
                  {typeof result.report === 'string' ? result.report : JSON.stringify(result.report, null, 2)}
                </div>
              </div>
            ) : null}

            {/* Individual agent results if available */}
            {result.agents && typeof result.agents === 'object' && (
              <div className="grid gap-6 md:grid-cols-2">
                {Object.entries(result.agents).map(([agentName, agentResult]: [string, any]) => (
                  <div key={agentName} className="p-5 bg-white border border-slate-200/80 rounded-xl shadow-sm space-y-3">
                    <div className="flex items-center gap-2 border-b border-slate-100 pb-2">
                      <Bot className="h-4 w-4 text-[#4051B5]" />
                      <h4 className="text-sm font-bold text-slate-800 capitalize">{agentName} Agent</h4>
                    </div>
                    <pre className="text-[11px] text-slate-600 font-mono overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap bg-slate-50 p-3 rounded-lg border border-slate-200/60">
                      {typeof agentResult === 'string' ? agentResult : JSON.stringify(agentResult, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            )}

            {/* Fallback: raw JSON */}
            {!result.report && !result.agents && (
              <div className="p-6 bg-white border border-slate-200/80 rounded-xl shadow-sm">
                <pre className="text-xs text-slate-600 font-mono overflow-x-auto max-h-96 overflow-y-auto whitespace-pre-wrap bg-slate-50 p-4 rounded-lg border border-slate-200/60">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
