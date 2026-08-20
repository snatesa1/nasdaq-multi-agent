'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
  Compass, 
  ShieldAlert, 
  ShieldCheck, 
  Upload, 
  FileText, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  CheckCircle, 
  RefreshCw, 
  Zap, 
  Layers, 
  DollarSign, 
  Clock, 
  Sliders, 
  Newspaper,
  ChevronDown,
  ChevronUp,
  Award,
  Activity,
  ArrowRight
} from 'lucide-react';
import { optionsApi } from '@/lib/api';

export default function BehavioralLabPage() {
  const [activeTab, setActiveTab] = useState<'forensics' | 'campaigns' | 'safety_shield' | 'news'>('forensics');
  const [loading, setLoading] = useState<boolean>(true);
  const [uploading, setUploading] = useState<boolean>(false);
  const [auditData, setAuditData] = useState<any>(null);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [newsItems, setNewsItems] = useState<any[]>([]);
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);

  // Safety Shield Interactive Simulator State
  const [testSymbol, setTestSymbol] = useState<string>('PANW');
  const [testAssetType, setTestAssetType] = useState<string>('StockOption');
  const [testBuySell, setTestBuySell] = useState<string>('Sell');
  const [testDelta, setTestDelta] = useState<number>(0.35);
  const [testDte, setTestDte] = useState<number>(14);
  const [testOrderValue, setTestOrderValue] = useState<number>(1200);
  const [testRecentLoss, setTestRecentLoss] = useState<number>(0);
  const [safetyResult, setSafetyResult] = useState<any>(null);
  const [evaluatingSafety, setEvaluatingSafety] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Load baseline audit and news on mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [auditRes, campRes, newsRes] = await Promise.all([
        optionsApi.getBehavioralAudit(),
        optionsApi.getHistoricalCampaigns(),
        optionsApi.getPortfolioNews(15)
      ]);
      setAuditData(auditRes);
      setCampaigns(campRes?.campaigns || []);
      setNewsItems(newsRes?.news || []);
    } catch (err) {
      console.error('Failed to load behavioral audit data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await optionsApi.uploadPdfReport(file);
      await loadData();
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setUploading(false);
    }
  };

  const handleTestSafety = async () => {
    setEvaluatingSafety(true);
    try {
      const res = await optionsApi.checkOrderSafety({
        symbol: testSymbol,
        asset_type: testAssetType,
        buy_sell: testBuySell,
        delta: testDelta,
        dte: testDte,
        order_value: testOrderValue,
        portfolio_equity: 102192.51,
        current_ticker_exposure: testSymbol === 'PANW' ? 14500.0 : 5000.0,
        recent_loss_amount: testRecentLoss
      });
      setSafetyResult(res);
    } catch (err) {
      console.error('Safety check failed:', err);
    } finally {
      setEvaluatingSafety(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* ── Top Header & Actions ────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl">
              <Compass className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                Saxo Behavioral Forensics & Safety Shield
              </h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Multi-year trade campaign lifecycles, psychological bias forensics, and automated execution circuit breakers.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            accept=".pdf" 
            className="hidden" 
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-semibold rounded-xl shadow-sm transition"
          >
            <Upload className="w-4 h-4 text-slate-500" />
            {uploading ? 'Parsing PDF...' : 'Upload Saxo PDF'}
          </button>

          <button
            onClick={loadData}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl shadow-sm transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh Audit
          </button>
        </div>
      </div>

      {/* ── 4-Column Executive Forensic Metric Ribbon ──────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Discipline Score */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Discipline Score</span>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
              (auditData?.discipline_score ?? 0) >= 80 ? 'bg-emerald-100 text-emerald-700' :
              (auditData?.discipline_score ?? 0) >= 60 ? 'bg-amber-100 text-amber-700' : 'bg-rose-100 text-rose-700'
            }`}>
              Grade: {auditData?.grade ?? 'C+'}
            </span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900">{auditData?.discipline_score ?? 53}</span>
            <span className="text-sm font-semibold text-slate-400">/ 100</span>
          </div>
          <div className="w-full bg-slate-100 h-2 rounded-full mt-3 overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all duration-500 ${
                (auditData?.discipline_score ?? 0) >= 80 ? 'bg-emerald-500' :
                (auditData?.discipline_score ?? 0) >= 60 ? 'bg-amber-500' : 'bg-rose-500'
              }`}
              style={{ width: `${auditData?.discipline_score ?? 53}%` }}
            />
          </div>
        </div>

        {/* Metric 2: Net Realized P&L */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Net Realized P&L</span>
            <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-xs font-semibold rounded-full">+12.55% Total</span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-600">+${(auditData?.total_pnl ?? 11599.39).toLocaleString()}</span>
          </div>
          <p className="text-xs text-slate-500 mt-2 flex items-center gap-1">
            <CheckCircle className="w-3.5 h-3.5 text-emerald-500" /> Account Value: $102,192.51
          </p>
        </div>

        {/* Metric 3: Stock Alpha */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Stock Selection Alpha</span>
            <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-xs font-semibold rounded-full">6 Wins</span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-slate-900">+${(auditData?.stock_pnl ?? 13993.98).toLocaleString()}</span>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            PANW +$5.9k · AMZN +$3.7k · COIN +$2k
          </p>
        </div>

        {/* Metric 4: Options Drag */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Options Volatility Drag</span>
            <span className="px-2 py-0.5 bg-rose-50 text-rose-700 text-xs font-semibold rounded-full">Call Capping</span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-rose-600">-${Math.abs(auditData?.option_pnl ?? -4967.35).toLocaleString()}</span>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            PANW Short Calls (-$5.1k) drag vs Visa (+100% win)
          </p>
        </div>
      </div>

      {/* ── Navigation Tabs ────────────────────────────────────────────── */}
      <div className="flex border-b border-slate-200 space-x-8">
        {[
          { id: 'forensics', label: 'Behavioral Forensics & Biases', icon: ShieldAlert },
          { id: 'campaigns', label: 'Trade Campaign Lifecycles', icon: Layers },
          { id: 'safety_shield', label: 'Live Execution Safety Shield', icon: ShieldCheck },
          { id: 'news', label: 'Portfolio News Wire', icon: Newspaper },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 pb-4 text-sm font-semibold border-b-2 transition ${
                isActive
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-600' : 'text-slate-400'}`} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* ── Tab 1: Behavioral Forensics & Diagnoses ────────────────────── */}
      {activeTab === 'forensics' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {auditData?.diagnoses?.map((diag: any) => (
              <div 
                key={diag.id} 
                className={`p-6 rounded-2xl border ${
                  diag.severity === 'CRITICAL' ? 'bg-rose-50/50 border-rose-200' :
                  diag.severity === 'HIGH' ? 'bg-amber-50/50 border-amber-200' : 'bg-emerald-50/50 border-emerald-200'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold tracking-wide ${
                    diag.severity === 'CRITICAL' ? 'bg-rose-100 text-rose-800' :
                    diag.severity === 'HIGH' ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
                  }`}>
                    {diag.severity}
                  </span>
                  <span className={`text-sm font-bold ${
                    diag.severity === 'CRITICAL' ? 'text-rose-600' :
                    diag.severity === 'HIGH' ? 'text-amber-700' : 'text-emerald-700'
                  }`}>
                    {diag.impact}
                  </span>
                </div>
                <h3 className="font-bold text-slate-900 text-base mb-2">{diag.name}</h3>
                <p className="text-sm text-slate-600 mb-4">{diag.description}</p>
                <div className="pt-3 border-t border-slate-200/60 flex items-start gap-2">
                  <Zap className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
                  <p className="text-xs font-medium text-slate-800">
                    <span className="font-bold text-indigo-700">Safety Directive:</span> {diag.remedy}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Quarterly P&L Evolution Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <h2 className="text-lg font-bold text-slate-900 mb-4">Quarterly P&L Development</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-xs font-bold text-slate-400 uppercase">Q1-2026</span>
                <div className="text-2xl font-extrabold text-rose-600 mt-1">-$6,536.45</div>
                <div className="text-xs text-slate-500 mt-1">Return: -6.8% · Costs: -$56.17</div>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-xs font-bold text-slate-400 uppercase">Q2-2026</span>
                <div className="text-2xl font-extrabold text-emerald-600 mt-1">+$13,418.80</div>
                <div className="text-xs text-slate-500 mt-1">Return: +15.2% · Costs: -$118.49</div>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-xs font-bold text-slate-400 uppercase">Q3-2026 (YTD)</span>
                <div className="text-2xl font-extrabold text-emerald-600 mt-1">+$4,717.04</div>
                <div className="text-xs text-slate-500 mt-1">Return: +4.8% · Costs: -$54.58</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab 2: Trade Campaign Lifecycles ───────────────────────────── */}
      {activeTab === 'campaigns' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Stitched Strategy Campaigns</h2>
              <p className="text-xs text-slate-500 mt-0.5">Aggregated multi-leg options and stock lifecycle performance.</p>
            </div>
            <span className="text-xs font-semibold px-3 py-1 bg-slate-100 text-slate-700 rounded-full">
              {campaigns.length} Active & Closed Campaigns
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 uppercase font-semibold text-xs border-b border-slate-200">
                <tr>
                  <th className="py-3.5 px-6">Ticker / Strategy</th>
                  <th className="py-3.5 px-6">Legs Count</th>
                  <th className="py-3.5 px-6">Stock P&L</th>
                  <th className="py-3.5 px-6">Option P&L</th>
                  <th className="py-3.5 px-6">Net Campaign P&L</th>
                  <th className="py-3.5 px-6">Behavioral Classification</th>
                  <th className="py-3.5 px-6 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {campaigns.map((camp) => (
                  <React.Fragment key={camp.ticker}>
                    <tr className="hover:bg-slate-50/80 transition">
                      <td className="py-4 px-6">
                        <div className="font-bold text-slate-900 text-base">{camp.ticker}</div>
                        <div className="text-xs text-slate-500">{camp.strategy}</div>
                      </td>
                      <td className="py-4 px-6 text-slate-600 font-medium">
                        {camp.legs_count} {camp.legs_count === 1 ? 'Leg' : 'Legs'}
                      </td>
                      <td className="py-4 px-6 font-semibold">
                        {camp.stock_pnl > 0 ? (
                          <span className="text-emerald-600">+${camp.stock_pnl.toLocaleString()}</span>
                        ) : camp.stock_pnl < 0 ? (
                          <span className="text-rose-600">-${Math.abs(camp.stock_pnl).toLocaleString()}</span>
                        ) : (
                          <span className="text-slate-400">$0.00</span>
                        )}
                      </td>
                      <td className="py-4 px-6 font-semibold">
                        {camp.option_pnl > 0 ? (
                          <span className="text-emerald-600">+${camp.option_pnl.toLocaleString()}</span>
                        ) : camp.option_pnl < 0 ? (
                          <span className="text-rose-600">-${Math.abs(camp.option_pnl).toLocaleString()}</span>
                        ) : (
                          <span className="text-slate-400">$0.00</span>
                        )}
                      </td>
                      <td className="py-4 px-6">
                        <span className={`text-base font-extrabold ${camp.total_pnl >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                          {camp.total_pnl >= 0 ? '+' : ''}${camp.total_pnl.toLocaleString()}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-semibold ${
                          camp.total_pnl > 1000 ? 'bg-emerald-50 text-emerald-700' :
                          camp.total_pnl < 0 ? 'bg-rose-50 text-rose-700' : 'bg-slate-100 text-slate-700'
                        }`}>
                          {camp.bias_classification}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <button
                          onClick={() => setExpandedTicker(expandedTicker === camp.ticker ? null : camp.ticker)}
                          className="p-1.5 hover:bg-slate-200 text-slate-600 rounded-lg transition"
                        >
                          {expandedTicker === camp.ticker ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </td>
                    </tr>

                    {/* Expanded Option Legs Breakdown */}
                    {expandedTicker === camp.ticker && (
                      <tr className="bg-slate-50/50">
                        <td colSpan={7} className="p-6">
                          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
                            <h4 className="font-bold text-xs uppercase tracking-wider text-slate-500">
                              Granular Option Contracts ({camp.ticker})
                            </h4>
                            {camp.options_legs && camp.options_legs.length > 0 ? (
                              <div className="divide-y divide-slate-100">
                                {camp.options_legs.map((leg: any, idx: number) => (
                                  <div key={idx} className="py-2 flex items-center justify-between text-xs">
                                    <div>
                                      <span className="font-bold text-slate-900">{leg.contract}</span>
                                      <span className="ml-2 text-slate-400">Expiry: {leg.expiry} · Strike: ${leg.strike}</span>
                                    </div>
                                    <div className="flex items-center gap-4">
                                      <span className="text-slate-400">Cost: ${leg.costs}</span>
                                      <span className={`font-bold ${leg.pnl >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                        {leg.pnl >= 0 ? '+' : ''}${leg.pnl.toLocaleString()}
                                      </span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <p className="text-xs text-slate-400 italic">No option contracts associated with this campaign.</p>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Tab 3: Live Execution Safety Shield ─────────────────────────── */}
      {activeTab === 'safety_shield' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Pre-Flight Trade Validator Simulator */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
            <div className="flex items-center gap-3 border-b border-slate-200 pb-4">
              <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                <Sliders className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-base">Pre-Flight Behavioral Safety Check</h3>
                <p className="text-xs text-slate-500">Test any proposed trade against our active behavioral circuit breakers.</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Target Symbol</label>
                <input
                  type="text"
                  value={testSymbol}
                  onChange={(e) => setTestSymbol(e.target.value.toUpperCase())}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm font-semibold text-slate-900 uppercase"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Asset Type</label>
                <select
                  value={testAssetType}
                  onChange={(e) => setTestAssetType(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm text-slate-900 bg-white"
                >
                  <option value="StockOption">Stock Option</option>
                  <option value="Stock">Stock</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Option Delta</label>
                <input
                  type="number"
                  step="0.05"
                  value={testDelta}
                  onChange={(e) => setTestDelta(parseFloat(e.target.value))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm text-slate-900"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Days to Expiry (DTE)</label>
                <input
                  type="number"
                  value={testDte}
                  onChange={(e) => setTestDte(parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm text-slate-900"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Order Value ($)</label>
                <input
                  type="number"
                  value={testOrderValue}
                  onChange={(e) => setTestOrderValue(parseFloat(e.target.value))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm text-slate-900"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Recent Loss in 24h ($)</label>
                <input
                  type="number"
                  value={testRecentLoss}
                  onChange={(e) => setTestRecentLoss(parseFloat(e.target.value))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm text-slate-900"
                />
              </div>
            </div>

            <button
              onClick={handleTestSafety}
              disabled={evaluatingSafety}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm rounded-xl shadow transition flex items-center justify-center gap-2"
            >
              <ShieldCheck className="w-4 h-4" />
              {evaluatingSafety ? 'Evaluating Safety Guardrails...' : 'Run Safety Shield Validation'}
            </button>

            {/* Validation Output */}
            {safetyResult && (
              <div className={`p-4 rounded-xl border ${
                safetyResult.approved ? 'bg-emerald-50 border-emerald-200' : 'bg-rose-50 border-rose-200'
              }`}>
                <div className="flex items-center gap-2 font-bold text-sm">
                  {safetyResult.approved ? (
                    <>
                      <CheckCircle className="w-5 h-5 text-emerald-600" />
                      <span className="text-emerald-800">ORDER APPROVED FOR EXECUTION</span>
                    </>
                  ) : (
                    <>
                      <ShieldAlert className="w-5 h-5 text-rose-600" />
                      <span className="text-rose-800">EXECUTION BLOCKED BY SAFETY SHIELD</span>
                    </>
                  )}
                </div>

                {safetyResult.infractions && safetyResult.infractions.length > 0 && (
                  <div className="mt-3 space-y-1.5">
                    {safetyResult.infractions.map((inf: string, i: number) => (
                      <p key={i} className="text-xs text-rose-700 font-semibold flex items-start gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0 mt-0.5" />
                        {inf}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Active Behavioral Rulebook */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
            <h3 className="font-bold text-slate-900 text-base">Active Behavioral Rulebook</h3>
            <p className="text-xs text-slate-500">Hard constraints enforced across all automated and manual trade dispatches.</p>

            <div className="space-y-3 pt-2">
              {auditData?.rulebook?.map((rule: any) => (
                <div key={rule.rule_id} className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 text-sm">{rule.name}</span>
                      <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-[10px] font-bold rounded-full">
                        {rule.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      <span className="font-semibold text-slate-700">Trigger:</span> {rule.condition}
                    </p>
                    <p className="text-xs text-indigo-700 font-semibold mt-0.5">
                      <span className="text-slate-700">Shield Action:</span> {rule.action}
                    </p>
                  </div>
                  <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0 mt-1" />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Tab 4: Portfolio News Wire ─────────────────────────────────── */}
      {activeTab === 'news' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-center justify-between border-b border-slate-200 pb-4 mb-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Saxo Portfolio News Wire</h2>
              <p className="text-xs text-slate-500">Real-time market flow and institutional headline stream.</p>
            </div>
            <span className="text-xs font-semibold px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full">
              Live Feed
            </span>
          </div>

          <div className="divide-y divide-slate-100">
            {newsItems.map((item, idx) => (
              <div key={idx} className="py-3 flex items-start justify-between gap-4 hover:bg-slate-50/60 p-2 rounded-xl transition">
                <div className="flex items-start gap-3">
                  <div className="px-2 py-1 bg-slate-100 text-slate-700 font-mono text-xs font-bold rounded-lg shrink-0">
                    {item.time || '18:00'}
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">{item.headline}</h4>
                    <span className="text-xs text-slate-400 font-medium">Source: {item.source || 'Saxo Wire'} · {item.category || 'Equities'}</span>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-300 shrink-0 mt-1" />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
