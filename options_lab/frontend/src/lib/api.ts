import { auth } from '@/lib/firebase';
import {
  BrokerStatus,
  BrokerAccountSummary,
  BrokerPositionsResponse,
  BrokerOrdersResponse
} from '@/types/broker';

// Dynamic API Base Resolver with Adaptive Runtime Discovery
let _activeApiBase: string | null = null;

export const getApiBase = (): string => {
  if (_activeApiBase !== null) return _activeApiBase;
  if (typeof window === 'undefined') return 'http://localhost:8000';
  if (process.env.NEXT_PUBLIC_API_URL) {
    _activeApiBase = process.env.NEXT_PUBLIC_API_URL;
    return _activeApiBase;
  }
  // In development mode, Next.js dev server runs without Nginx, so backend is on port 8000:
  if (process.env.NODE_ENV === 'development') {
    _activeApiBase = `http://${window.location.hostname}:8000`;
    return _activeApiBase;
  }
  // In production builds, default to same-origin relative path '' (Nginx container in Docker)
  // Adaptive handshake below will auto-switch to port 8000 if same-origin is not reverse-proxied (Local PC static host)
  return '';
};

export const setApiBase = (base: string) => {
  _activeApiBase = base;
};

export const API_BASE_URL = getApiBase();

export async function checkBackendHandshake(timeoutMs: number = 3000): Promise<{ ok: boolean; error?: string }> {
  const currentBase = _activeApiBase !== null ? _activeApiBase : getApiBase();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  // 1. Try configured / same-origin API base first
  try {
    const res = await fetch(`${currentBase}/api/health`, { method: 'GET', signal: controller.signal });
    clearTimeout(timer);
    if (res.ok) {
      setApiBase(currentBase);
      return { ok: true };
    }
  } catch (err: any) {
    clearTimeout(timer);
  }

  // 2. Adaptive fallback: If current base failed and we are in the browser, probe direct port 8000
  if (typeof window !== 'undefined' && window.location.hostname) {
    const fallbackBase = `http://${window.location.hostname}:8000`;
    if (currentBase !== fallbackBase) {
      try {
        const directController = new AbortController();
        const directTimer = setTimeout(() => directController.abort(), 2000);
        const directRes = await fetch(`${fallbackBase}/api/health`, {
          method: 'GET',
          signal: directController.signal
        });
        clearTimeout(directTimer);
        if (directRes.ok) {
          setApiBase(fallbackBase);
          console.info(`[OptionsLab Gateway] Adaptive routing locked onto standalone backend at ${fallbackBase}`);
          return { ok: true };
        }
      } catch (dErr) {
        // Direct port 8000 probe also failed
      }
    }
  }

  const targetHost = _activeApiBase || (typeof window !== 'undefined' ? `${window.location.hostname}:${window.location.port || '80'}` : 'localhost:8000');
  return { ok: false, error: `Cannot connect to OptionsLab backend on ${targetHost}. Server is offline.` };
}

export async function apiRequest(endpoint: string, method: string = 'GET', body?: any, timeoutMs: number = 30000) {
  const base = _activeApiBase !== null ? _activeApiBase : getApiBase();
  const url = `${base}${endpoint}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',

  };

  // Attach Firebase auth token if user is signed in
  try {
    const authReady = Promise.race([
      auth.authStateReady(),
      new Promise((resolve) => setTimeout(resolve, 800))
    ]);
    await authReady;
    const token = await auth.currentUser?.getIdToken();
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }
  } catch (e) {
    // Auth not initialized yet or no user — continue without token
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const options: RequestInit = {
    method,
    headers,
    signal: controller.signal
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, options);
    clearTimeout(timer);
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} - ${errorText || response.statusText}`);
    }
    return await response.json();
  } catch (error: any) {
    clearTimeout(timer);
    if (error.name === 'AbortError') {
      const timeoutErr = new Error(`Backend Handshake Timeout: Request to ${endpoint} timed out after ${timeoutMs / 1000}s. Operation short-circuited.`);
      console.error(timeoutErr.message);
      throw timeoutErr;
    }
    if (error.message?.includes('Failed to fetch') || error.message?.includes('NetworkError')) {
      const targetHost = base || (typeof window !== 'undefined' ? `${window.location.hostname}:${window.location.port || '80'}` : 'localhost:8000');
      const netErr = new Error(`Backend Handshake Disconnected: Unable to reach OptionsLab API server (${targetHost}). Please verify the backend container or server is running.`);
      console.error(netErr.message);
      throw netErr;
    }
    console.error(`Request to ${endpoint} failed:`, error);
    throw error;
  }
}

export const optionsApi = {
  getQuote: (symbol: string) => apiRequest(`/market/quote/${symbol}`),
  getUniverse: () => apiRequest('/market/universe'),
  simulateGbm: (params: { S0: number; mu: number; sigma: number; T: number; N: number; num_paths: number }) => 
    apiRequest('/simulate/gbm', 'POST', params),
  priceAnalytical: (params: { S: number; K: number; T: number; r: number; sigma: number; option_type: string }) =>
    apiRequest('/price/analytical', 'POST', params),
  priceMonteCarlo: (params: { S0: number; K: number; T: number; r: number; sigma: number; option_type: string; num_paths?: number }) =>
    apiRequest('/price/monte-carlo', 'POST', params),
  priceLegacyLab: (params: { S0: number; K: number; T: number; r: number; sigma: number; N: number }) =>
    apiRequest('/price/legacy-lab', 'POST', params),
  getGreeksSurface: (params: { S: number; K: number; T: number; r: number; sigma: number; option_type: string }) =>
    apiRequest('/greeks/surface', 'POST', params),
  simulateStrategy: (params: { legs: any[]; underlying_spot: number; r?: number; sigma?: number; price_range_pct?: number; steps?: number }) =>
    apiRequest('/strategy/payoff', 'POST', params),
  getVolSurface: (params: { spot_price: number; base_sigma?: number; risk_free_rate?: number; strike_ratios?: number[]; expirations_days?: number[] }) =>
    apiRequest('/volatility/surface', 'POST', params),
  getPortfolioGreeks: (params: { positions: any[]; risk_free_rate?: number }) =>
    apiRequest('/portfolio/greeks', 'POST', params),
  askTutor: (params: { message: string; chat_history: any[]; context?: any; enable_grounding?: boolean }) =>
    apiRequest('/tutor/ask', 'POST', params),
  getTutorHint: (params: { chat_history: any[]; context?: any }) =>
    apiRequest('/tutor/hint', 'POST', params),
  explainConcept: (concept: string) =>
    apiRequest('/tutor/explain', 'POST', { concept }),
  scanFundamentalIndex: (symbols?: string[]) =>
    apiRequest('/fundamental-index/scan', 'POST', { symbols }),

  // ── Session Persistence ───────────────────────────────────────────────────
  listSessions: () => apiRequest('/tutor/sessions'),
  createSession: (title: string, messages: { role: string; content: string }[]) =>
    apiRequest('/tutor/sessions', 'POST', { title, messages }),
  getSession: (id: string) => apiRequest(`/tutor/sessions/${id}`),
  updateSession: (id: string, messages: { role: string; content: string }[], title?: string) =>
    apiRequest(`/tutor/sessions/${id}`, 'PUT', { messages, title }),
  deleteSession: (id: string) => apiRequest(`/tutor/sessions/${id}`, 'DELETE'),

  // ── Portfolio ─────────────────────────────────────────────────────────────
  listPortfolios: () => apiRequest('/api/portfolio'),
  getPortfolio: (id: string) => apiRequest(`/api/portfolio/${id}`),
  analyzePortfolio: (id: string) => apiRequest(`/api/portfolio/${id}/analyze`),
  syncPortfolio: (spreadsheetId?: string) => apiRequest(spreadsheetId ? `/api/portfolio/sync?spreadsheet_id=${encodeURIComponent(spreadsheetId)}` : '/api/portfolio/sync', 'POST'),
  deletePortfolio: (id: string) => apiRequest(`/api/portfolio/${id}`, 'DELETE'),

  // ── Multi-Agent ───────────────────────────────────────────────────────────
  runAnalysis: (tickers: string[]) => apiRequest('/multi-agent/analyze', 'POST', { tickers }),

  // ── Earnings Plays ────────────────────────────────────────────────────────
  getUpcomingEarnings: () => apiRequest('/api/earnings/upcoming'),
  scanEarnings: (params: { low_threshold_pct: number; min_open_interest: number }) =>
    apiRequest('/api/earnings/scan', 'POST', params),
  getEarningsVolatility: (symbol: string) => apiRequest(`/api/earnings/volatility/${symbol}`),

  // ── Broker Gateway (Live & SIM Integration) ───────────────────────────────
  getBrokerStatus: (): Promise<BrokerStatus> => apiRequest('/api/broker/status'),
  getBrokerAuthUrl: (): Promise<{ auth_url: string; app_name: string; redirect_url: string }> => apiRequest('/api/broker/oauth/auth-url'),
  setBrokerToken: (payload: { token?: string; code?: string; refresh_token?: string }) => apiRequest('/api/broker/oauth/set-token', 'POST', payload),
  disconnectBroker: () => apiRequest('/api/broker/oauth/disconnect', 'POST'),
  getBrokerAccount: (): Promise<BrokerAccountSummary> => apiRequest('/api/broker/account'),

  getBrokerPositions: (): Promise<BrokerPositionsResponse> => apiRequest('/api/broker/positions'),
  getBrokerOrders: (): Promise<BrokerOrdersResponse> => apiRequest('/api/broker/orders'),
  getBrokerClosedPositions: (): Promise<{ trades: any[]; count: number }> => apiRequest('/api/broker/closed-positions'),
  getBrokerOrderBlotter: (): Promise<any> => apiRequest('/api/broker/order-blotter'),
  refreshBrokerData: (): Promise<any> => apiRequest('/api/broker/refresh', 'POST'),
  getBrokerWatchlists: (): Promise<{ watchlists: any[] }> => apiRequest('/api/broker/watchlists'),
  getBrokerWatchlistInstruments: (watchlistId: string): Promise<{ watchlist_id: string; instruments: any[] }> =>
    apiRequest(`/api/broker/watchlist/${encodeURIComponent(watchlistId)}`),
  addWatchlistSymbol: (watchlistId: string, symbol: string, name?: string): Promise<any> =>
    apiRequest(`/api/broker/watchlist/${encodeURIComponent(watchlistId)}/symbols`, 'POST', { symbol, name }),
  removeWatchlistSymbol: (watchlistId: string, symbol: string): Promise<any> =>
    apiRequest(`/api/broker/watchlist/${encodeURIComponent(watchlistId)}/symbols/${encodeURIComponent(symbol)}`, 'DELETE'),
  scanCspOpportunities: (source: string = 'saxo', watchlistId?: string): Promise<{ source: string; scanned_symbols: string[]; opportunities: any[] }> =>
    apiRequest(watchlistId ? `/api/scanner/csp?source=${source}&watchlist_id=${encodeURIComponent(watchlistId)}` : `/api/scanner/csp?source=${source}`),
  placeBrokerOrder: (payload: { uic: number; asset_type?: string; amount?: number; buy_sell?: string; order_type?: string; order_price: number }) =>
    apiRequest('/api/broker/orders', 'POST', payload),
  runBrokerPipelineScan: (params?: { candidates?: string[]; simulate_order_placement?: boolean }) =>
    apiRequest('/api/broker/pipeline/scan', 'POST', params || {}),

  // ── Multi-Year Trade History & Behavioral Forensics ───────────────────────
  uploadPdfReport: async (file: File) => {
    const url = `${getApiBase()}/api/history/upload-pdf`;
    const formData = new FormData();
    formData.append('file', file);
    const headers: Record<string, string> = {};
    try {
      await auth.authStateReady();
      const token = await auth.currentUser?.getIdToken();
      if (token) headers['Authorization'] = 'Bearer ' + token;
    } catch (e) { /* no-op */ }
    const res = await fetch(url, { method: 'POST', headers, body: formData });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`PDF upload failed: ${err}`);
    }
    return await res.json();
  },
  initSampleReport: () => apiRequest('/api/history/sample-init', 'POST'),
  listReports: () => apiRequest('/api/history/reports'),
  getHistoricalCampaigns: (reportId?: string) =>
    apiRequest(reportId ? `/api/history/campaigns?report_id=${encodeURIComponent(reportId)}` : '/api/history/campaigns'),
  getBehavioralAudit: (reportId?: string) =>
    apiRequest(reportId ? `/api/history/behavioral-audit?report_id=${encodeURIComponent(reportId)}` : '/api/history/behavioral-audit'),
  getPortfolioNews: (top: number = 25, forceRefresh: boolean = false) =>
    apiRequest(`/api/history/news?top=${top}&force_refresh=${forceRefresh}&_t=${Date.now()}`),
  checkOrderSafety: (payload: any) =>
    apiRequest('/api/shield/check-order', 'POST', payload),

  // ── Frontend-Backend Handshake & Connectivity ────────────────────────────
  checkHandshake: (timeoutMs: number = 3000) => checkBackendHandshake(timeoutMs),

  // ── Weekly Intelligence & Trade Approval ─────────────────────────────────
  getWeeklyBriefing: (weekLabel?: string, forceRefresh?: boolean, timeoutMs: number = 75000) => {
    const params = new URLSearchParams();
    if (weekLabel) params.append('week_label', weekLabel);
    if (forceRefresh) params.append('force_refresh', 'true');
    const q = params.toString();
    return apiRequest(q ? `/api/intelligence/weekly-briefing?${q}` : '/api/intelligence/weekly-briefing', 'GET', undefined, timeoutMs);
  },
  getStagedTrades: (weekLabel?: string, status?: string) => {
    const params = new URLSearchParams();
    if (weekLabel) params.append('week_label', weekLabel);
    if (status) params.append('status', status);
    const q = params.toString();
    return apiRequest(q ? `/api/trades/staged?${q}` : '/api/trades/staged');
  },
  approveTrade: (tradeId: string) => apiRequest('/api/trades/approve', 'POST', { trade_id: tradeId }),
  rejectTrade: (tradeId: string, reason?: string) => apiRequest('/api/trades/reject', 'POST', { trade_id: tradeId, reason }),
  getMarginStatus: () => apiRequest('/api/margin/status'),
  runWheelBacktest: (params: {
    symbol: string;
    benchmark?: string;
    lookback_years?: number;
    initial_capital?: number;
    target_dte?: number;
    otm_pct?: number;
    profit_target_pct?: number;
    gamma_roll_dte?: number;
    hold_to_expiration?: boolean;
  }) => apiRequest('/api/analytics/wheel-backtest', 'POST', params),

  // ── Macro Category Taxonomy & Dynamic Corpus ─────────────────────────────
  getMacroCorpus: (category?: string) => {
    const q = category ? `?category=${encodeURIComponent(category)}` : '';
    return apiRequest(`/api/intelligence/corpus${q}`);
  },
  addOrUpdateCorpusKeyword: (payload: {
    category: string;
    keyword: string;
    weight?: number;
    directional_bias?: string;
    default_impact?: number;
    default_tickers?: string;
    source?: string;
  }) => apiRequest('/api/intelligence/corpus/keyword', 'POST', payload),
  deleteCorpusKeyword: (keyword: string) =>
    apiRequest(`/api/intelligence/corpus/keyword/${encodeURIComponent(keyword)}`, 'DELETE'),
};



