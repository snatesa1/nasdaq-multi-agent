import { auth } from '@/lib/firebase';
import {
  BrokerStatus,
  BrokerAccountSummary,
  BrokerPositionsResponse,
  BrokerOrdersResponse
} from '@/types/broker';

const getApiBase = () => {
  if (typeof window === 'undefined') return 'http://localhost:8000';
  // Dev server redirects to local fastapi instance
  if (window.location.port === '3000' || window.location.port === '5173') {
    return 'http://localhost:8000';
  }
  return '';
};

const API_BASE_URL = getApiBase();

export async function apiRequest(endpoint: string, method: string = 'GET', body?: any) {
  const url = `${API_BASE_URL}${endpoint}`;
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

  const options: RequestInit = {
    method,
    headers,
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} - ${errorText || response.statusText}`);
    }
    return await response.json();
  } catch (error) {
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
  deleteSession: async (id: string) => {
    const url = `${API_BASE_URL}/tutor/sessions/${id}`;
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    try {
      await auth.authStateReady();
      const token = await auth.currentUser?.getIdToken();
      if (token) {
        headers['Authorization'] = 'Bearer ' + token;
      }
    } catch (e) { /* no-op */ }
    const res = await fetch(url, { method: 'DELETE', headers });
    if (!res.ok && res.status !== 204) throw new Error(`Delete failed: ${res.status}`);
    return true;
  },

  // ── Portfolio ─────────────────────────────────────────────────────────────
  listPortfolios: () => apiRequest('/api/portfolio'),
  getPortfolio: (id: string) => apiRequest(`/api/portfolio/${id}`),
  analyzePortfolio: (id: string) => apiRequest(`/api/portfolio/${id}/analyze`),
  syncPortfolio: (spreadsheetId?: string) => apiRequest(spreadsheetId ? `/api/portfolio/sync?spreadsheet_id=${encodeURIComponent(spreadsheetId)}` : '/api/portfolio/sync', 'POST'),
  deletePortfolio: async (id: string) => {
    const url = `${API_BASE_URL}/api/portfolio/${id}`;
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    try {
      await auth.authStateReady();
      const token = await auth.currentUser?.getIdToken();
      if (token) {
        headers['Authorization'] = 'Bearer ' + token;
      }
    } catch (e) { /* no-op */ }
    const res = await fetch(url, { method: 'DELETE', headers });
    if (!res.ok && res.status !== 204) throw new Error(`Delete failed: ${res.status}`);
    return true;
  },

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
  scanCspOpportunities: (source: string = 'saxo', watchlistId?: string): Promise<{ source: string; scanned_symbols: string[]; opportunities: any[] }> =>
    apiRequest(watchlistId ? `/api/scanner/csp?source=${source}&watchlist_id=${encodeURIComponent(watchlistId)}` : `/api/scanner/csp?source=${source}`),
  placeBrokerOrder: (payload: { uic: number; asset_type?: string; amount?: number; buy_sell?: string; order_type?: string; order_price: number }) =>
    apiRequest('/api/broker/orders', 'POST', payload),
  runBrokerPipelineScan: (params?: { candidates?: string[]; simulate_order_placement?: boolean }) =>
    apiRequest('/api/broker/pipeline/scan', 'POST', params || {}),

  // ── Multi-Year Trade History & Behavioral Forensics ───────────────────────
  uploadPdfReport: async (file: File) => {
    const url = `${API_BASE_URL}/api/history/upload-pdf`;
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
  getPortfolioNews: (top: number = 25) =>
    apiRequest(`/api/history/news?top=${top}`),
  checkOrderSafety: (payload: any) =>
    apiRequest('/api/shield/check-order', 'POST', payload),

  // ── Weekly Intelligence & Trade Approval ─────────────────────────────────
  getWeeklyBriefing: (weekLabel?: string, forceRefresh?: boolean) => {
    const params = new URLSearchParams();
    if (weekLabel) params.append('week_label', weekLabel);
    if (forceRefresh) params.append('force_refresh', 'true');
    const q = params.toString();
    return apiRequest(q ? `/api/intelligence/weekly-briefing?${q}` : '/api/intelligence/weekly-briefing');
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
};



