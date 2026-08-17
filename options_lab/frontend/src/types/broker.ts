/**
 * Broker Gateway & Execution TypeScript Interfaces (Type-Safe SIM & Live Platform)
 */

export type BrokerEnvironmentMode = 'SIMULATION' | 'LIVE';

export interface BrokerStatus {
  environment: BrokerEnvironmentMode;
  allow_live_execution: boolean;
  has_access_token: boolean;
  has_refresh_token: boolean;
  base_url: string;
  timeout_seconds: number;
  status: string;
}

export interface BrokerAccountSummary {
  status: string;
  environment: BrokerEnvironmentMode;
  cash_available: number;
  total_equity: number;
  margin_available: number;
  margin_used: number;
  currency: string;
  account_id?: string;
  updated_at: string;
}

export interface BrokerPosition {
  position_id: string;
  uic: number;
  symbol: string;
  description: string;
  asset_type: 'Stock' | 'StockOption' | 'Contract' | string;
  option_type?: 'call' | 'put' | null;
  strike_price?: number | null;
  expiry_date?: string | null;
  amount: number;
  open_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  currency: string;
}

export interface BrokerPositionsResponse {
  environment: BrokerEnvironmentMode;
  status: string;
  total_positions_count: number;
  total_unrealized_pnl: number;
  positions: BrokerPosition[];
  updated_at: string;
}

export interface BrokerOrder {
  order_id: string;
  uic: number;
  symbol: string;
  description: string;
  asset_type: string;
  buy_sell: 'Buy' | 'Sell';
  order_type: 'Limit' | 'Market' | 'StopLimit' | string;
  amount: number;
  order_price: number;
  filled_price?: number | null;
  status: 'Filled' | 'Working' | 'Cancelled' | 'Rejected' | string;
  placed_at: string;
  executed_at?: string | null;
}

export interface BrokerOrdersResponse {
  environment: BrokerEnvironmentMode;
  status: string;
  total_orders_count: number;
  orders: BrokerOrder[];
  updated_at: string;
}
