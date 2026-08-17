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
    await auth.authStateReady();
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
  syncPortfolio: (spreadsheetId?: string) => apiRequest(spreadsheetId ? `/api/portfolio/sync?spreadsheet_id=${spreadsheetId}` : '/api/portfolio/sync', 'POST'),
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
  placeBrokerOrder: (payload: { uic: number; asset_type?: string; amount?: number; buy_sell?: string; order_type?: string; order_price: number }) =>
    apiRequest('/api/broker/orders', 'POST', payload),
  runBrokerPipelineScan: (params?: { candidates?: string[]; simulate_order_placement?: boolean }) =>
    apiRequest('/api/broker/pipeline/scan', 'POST', params || {}),
};


