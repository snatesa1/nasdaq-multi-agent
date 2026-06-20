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
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <Bot className="h-6 w-6 text-[#5ba4b5]" /> Market Intelligence Agents
          </h1>
          <p className="text-slate-400 text-sm mt-1 max-w-2xl">
            Run the hierarchical multi-agent analysis pipeline on your portfolio tickers or custom stock universe.
          </p>
        </div>

        {/* Input Section */}
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-md font-bold text-slate-200">Analysis Configuration</h3>
          <div>
            <label className="text-[10px] text-slate-500 font-bold block mb-2 uppercase tracking-wider">
              Ticker Symbols (comma-separated)
            </label>
            <input
              type="text"
              value={tickersInput}
              onChange={(e) => setTickersInput(e.target.value)}
              placeholder="AAPL, NVDA, TSLA, PANW..."
              className="w-full rounded-lg px-4 py-3 text-sm bg-[#12141c] border border-slate-800 text-slate-200 font-mono placeholder:text-slate-600 focus:border-[#5ba4b5] focus:outline-none transition"
            />
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={handleRunAnalysis}
              disabled={running}
              className="flex items-center gap-2 rounded-lg bg-[#5ba4b5] hover:bg-[#4a91a2] px-6 py-2.5 text-sm font-semibold text-slate-900 transition disabled:opacity-50"
            >
              {running ? (
                <Loader className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {running ? 'Running Analysis...' : 'Run Analysis'}
            </button>

            {running && (
              <span className="text-xs text-slate-500 animate-pulse">
                Multi-agent pipeline in progress — this may take a moment...
              </span>
            )}
          </div>

          {error && (
            <div className="rounded-lg bg-red-500/5 border border-red-500/10 p-4 flex items-start gap-3">
              <AlertCircle className="h-4 w-4 text-[#dc3545] flex-shrink-0 mt-0.5" />
              <p className="text-xs text-slate-400">{error}</p>
            </div>
          )}
        </div>

        {/* Results Section */}
        {running && (
          <div className="glass-card p-12 text-center">
            <Loader className="h-10 w-10 text-[#5ba4b5] animate-spin mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-300">Agents Analyzing...</h3>
            <p className="text-sm text-slate-500 mt-2">
              Fundamental, Technical, Macro, Correlation, and Sentiment agents are processing your universe.
            </p>
          </div>
        )}

        {result && !running && (
          <div className="space-y-6">
            <h3 className="text-lg font-bold text-slate-200">Analysis Results</h3>

            {/* If result has structured data, render cards */}
            {typeof result === 'object' && !Array.isArray(result) && result.report ? (
              <div className="glass-card p-6 space-y-4">
                <h4 className="text-md font-bold text-slate-200">Composite Report</h4>
                <div className="text-xs text-slate-400 leading-relaxed whitespace-pre-line font-sans">
                  {typeof result.report === 'string' ? result.report : JSON.stringify(result.report, null, 2)}
                </div>
              </div>
            ) : null}

            {/* Individual agent results if available */}
            {result.agents && typeof result.agents === 'object' && (
              <div className="grid gap-6 md:grid-cols-2">
                {Object.entries(result.agents).map(([agentName, agentResult]: [string, any]) => (
                  <div key={agentName} className="glass-card p-5 space-y-3">
                    <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
                      <Bot className="h-4 w-4 text-[#5ba4b5]" />
                      <h4 className="text-sm font-bold text-slate-200 capitalize">{agentName} Agent</h4>
                    </div>
                    <pre className="text-[11px] text-slate-400 font-mono overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap">
                      {typeof agentResult === 'string' ? agentResult : JSON.stringify(agentResult, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            )}

            {/* Fallback: raw JSON */}
            {!result.report && !result.agents && (
              <div className="glass-card p-6">
                <pre className="text-xs text-slate-400 font-mono overflow-x-auto max-h-96 overflow-y-auto whitespace-pre-wrap">
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
