/**
 * intelligence.ts — Institutional Weekly Macro Intelligence & Execution Types.
 * 
 * Provides TypeScript definitions for:
 * 1. 4-Dimensional Macro Direction Compass
 * 2. AI Corporate Interlink Cockpit (Anchors, Challengers, GAAP DSI & CapEx)
 * 3. 4-Tier Capital Allocation Scenarios (80/20, 60/40, 50/50, 20/80)
 * 4. $1,000/Month Systematic Wheel Harvest Blotter ($2.00-$3.00 sweet spot, PoP %, cash-burn risk)
 */

export interface MacroEvent {
  event_id: string;
  title: string;
  category: string;
  impact_score: number;
  affected_tickers: string[];
  summary: string;
  bias: string;
  date: string;
}

export interface MacroCompassDimension {
  name: string;
  direction: string;
  score: number;
  key_driver: string;
  momentum: string;
  interlink_health_score?: number;
}

export interface MacroCompass {
  composite_direction: string;
  composite_score: number;
  scale: string;
  dimension_1_rates: MacroCompassDimension;
  dimension_2_earnings: MacroCompassDimension;
  dimension_3_interlink: MacroCompassDimension;
  dimension_4_liquidity: MacroCompassDimension;
}

export interface BalanceProvenance {
  total_equity: number;
  cash_available: number;
  balance_source: 'LIVE_BROKER' | 'CACHED_BROKER' | 'HISTORICAL_REPORT' | 'PORTFOLIO_HOLDINGS' | 'SIMULATED_BENCHMARK' | string;
  is_simulated: boolean;
  account_id?: string;
  currency?: string;
  as_of?: string;
  details?: string;
}

export interface CapitalAllocationScenario {
  scenario_id: '80_20' | '60_40' | '50_50' | '20_80';
  label: string;
  subtitle: string;
  target_equity_pct: number;
  target_cash_pct: number;
  target_equity_dollars: number;
  target_cash_dollars: number;
  benefits: string;
  downside_risk: string;
  options_playbook: string;
  annualized_theta_yield_est: string;
  cash_drag_status: string;
  balance_provenance?: BalanceProvenance;
}

export interface InterlinkAnchorNode {
  ticker: string;
  name: string;
  role: string;
  capex_annual_b: number;
  revenue_annual_b: number;
  inventory_dsi_days: number;
  dsi_status: 'Bottleneck (<65d)' | 'Balanced Supply (65-85d)' | 'Inventory Glut (>85d)' | 'N/A (Asset-Light)' | string;
  is_live_data: boolean;
  filing_date?: string;
}

export interface InterlinkChallengerNode {
  category: string;
  label: string;
  composite_score: number;
  score_derivation: {
    growth_score: number;
    margin_score: number;
    efficiency_score: number;
    formula: string;
    weights: string;
  };
  key_tickers: string[];
  rationale: string;
}

export interface InterlinkEdge {
  from: string;
  to: string;
  relationship: string;
  annual_flow_est_b?: number;
}

export interface InterlinkCockpit {
  engine_version: string;
  last_updated: string;
  anchors: Record<string, InterlinkAnchorNode>;
  challengers: Record<string, InterlinkChallengerNode>;
  edges: InterlinkEdge[];
  composite_interlink_health_index: number;
}

export interface SubAgentConsensus {
  financial_analyst: {
    persona: string;
    status: string;
    verdict: string;
    sweet_spot_score?: string;
    fundamental_floor?: string;
    analyst_defense?: string;
  };
  risk_aggregator: {
    persona: string;
    status: string;
    verdict: string;
    sector_clearance?: string;
    margin_impact?: string;
    collateral_status?: string;
    sizing_rationale?: string;
  };
  executive_allocator: {
    persona: string;
    status: string;
    rank: number;
    golden_trade_label: string;
    monthly_harvest_contribution: string;
    allocation_decision: string;
    target_harvest_gap?: string;
    challenge_inquiry?: string;
    dialectical_verdict?: string;
  };
}

export interface StagedTrade {
  trade_id: string;
  symbol: string;
  name?: string;
  sector?: string;
  strategy: string;
  direction: string;
  spot_price: number;
  strike: number;
  delta: number;
  dte: number;
  premium_estimate: number;
  bid_price?: number;
  ask_price?: number;
  spread?: number;
  pricing_source?: string;
  contracts: number;
  annualized_roc_pct?: number;
  pop_pct?: number;
  collateral_required: number;
  breakeven_price?: number;
  discount_to_spot_pct?: number;
  assignment_probability_pct?: number;
  assignment_risk_description?: string;
  contract_verified?: boolean;
  contract_uic?: number;
  contract_description?: string;
  contract_symbol?: string;
  verification_status?: string;
  exchange_precheck_viable?: boolean;
  precheck_margin_impact?: number;
  max_margin_impact_pct: number;
  projected_total_margin_pct?: number;
  thesis: string;
  edge_source: string;
  risk_rating: number;
  safety_check?: string;
  status: string;
  saxo_order_id?: string;
  proposed_at: string;
  approved_at?: string;
  executed_at?: string;
  week_label: string;
  expiration_date?: string;
  collateral_explanation?: string;
  collateral_coverage_type?: string;
  golden_trade_rank?: number;
  sub_agent_consensus?: SubAgentConsensus;
  pillars?: {
    watchlist_status: string;
    trade_history_profile: string;
    margin_status: string;
  };
}

export interface WheelHarvestBlotter {
  monthly_harvest_target: number;
  target_premium_band: string;
  total_staged_contracts: number;
  projected_monthly_harvest_dollars: number;
  target_achievement_pct: number;
  average_pop_percent: number;
  total_collateral_required: number;
  candidates_cap?: number;
  max_allowed_collateral?: number;
  collateral_headroom?: number;
  collateral_utilization_pct?: number;
  collateral_coverage_rationale?: string;
  allocator_challenge_active?: boolean;
  allocator_shortfall_dollars?: number;
  allocator_challenge_statement?: string;
  candidates: StagedTrade[];
}

export interface MarginStatus {
  total_equity: number;
  cash_available: number;
  margin_used: number;
  margin_utilization_pct: number;
  max_margin_limit_pct: number;
  allowed_margin_dollars: number;
  remaining_margin_headroom: number;
  is_within_limit: boolean;
  currency: string;
  updated_at: string;
}

export interface MarketSummaryItem {
  id: string;
  title: string;
  context: string;
  sources: string[];
  sites_count: number;
  category: string;
  bias?: 'BULLISH' | 'BEARISH' | 'NEUTRAL' | string;
  link?: string;
  date?: string;
}

export interface CrossAssetRow {
  asset: string;
  benchmark_code: string;
  level: string;
  change: string;
  direction: 'UP' | 'DOWN' | 'FLAT';
  bias: 'BULLISH' | 'BEARISH' | 'NEUTRAL' | 'RANGE-BOUND';
  driver: string;
  options_stance: string;
}

export interface BriefingData {
  week_label: string;
  generated_at: string;
  ai_summary: string;
  framework?: string;
  hitl_status?: string;
  margin_status: MarginStatus;
  scoped_universe_count: number;
  watchlist_tickers: string[];
  active_position_tickers: string[];
  macro_events: MacroEvent[];
  potential_trades: StagedTrade[];
  macro_compass?: MacroCompass;
  capital_allocation_scenarios?: CapitalAllocationScenario[];
  balance_provenance?: BalanceProvenance;
  interlink_cockpit?: InterlinkCockpit;
  wheel_harvest_blotter?: WheelHarvestBlotter;
  market_summary?: MarketSummaryItem[];
  cross_asset_table?: CrossAssetRow[];
}
