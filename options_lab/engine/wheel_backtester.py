"""
Wheel Strategy Backtester Engine for OptionsLab.

Simulates multi-year systematic 30-DTE Cash-Secured Put and Covered Call cycles
on historical daily price bars, adhering to institutional rules:
- Strict 30-32 DTE entry
- 50% Profit-Taking early exit rule
- 21-DTE Gamma roll avoidance rule
- ~8-10% OTM Strike selection (Delta -0.20 to -0.25 for CSP, +0.25 for CC)
- Dynamic Black-Scholes theoretical mark pricing and daily equity curve generation.
"""

import math
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf

from .black_scholes import black_scholes_price

logger = logging.getLogger("wheel-backtester")


class WheelBacktester:
    """
    Backtesting engine for systematic 30-DTE Wheel Strategy (CSPs & CCs).
    """

    def __init__(self):
        pass

    def fetch_historical_bars(
        self,
        symbol: str,
        benchmark: str = "SPY",
        lookback_years: int = 2
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Fetches historical daily OHLCV bars for the underlying symbol and benchmark.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=int(lookback_years * 365.25 + 60))

        logger.info(f"Downloading historical bars for {symbol} and {benchmark} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Download underlying
        df_sym = yf.download(symbol, start=start_date, end=end_date, progress=False, auto_adjust=True)
        if df_sym.empty:
            raise ValueError(f"Failed to retrieve historical price data for symbol '{symbol}'.")

        # Download benchmark
        df_bench = yf.download(benchmark, start=start_date, end=end_date, progress=False, auto_adjust=True)
        if df_bench.empty:
            df_bench = yf.download("SPY", start=start_date, end=end_date, progress=False, auto_adjust=True)

        # Normalize column names if multi-index
        if isinstance(df_sym.columns, pd.MultiIndex):
            df_sym.columns = [col[0].lower() for col in df_sym.columns]
        else:
            df_sym.columns = [col.lower() for col in df_sym.columns]

        if isinstance(df_bench.columns, pd.MultiIndex):
            df_bench.columns = [col[0].lower() for col in df_bench.columns]
        else:
            df_bench.columns = [col.lower() for col in df_bench.columns]

        return df_sym.dropna(), df_bench.dropna()

    def run_backtest(
        self,
        symbol: str,
        benchmark: str = "SPY",
        lookback_years: float = 2.0,
        initial_capital: float = 100_000.0,
        target_dte: int = 30,
        otm_pct: float = 0.08,
        profit_target_pct: float = 0.50,
        gamma_roll_dte: int = 21,
        hold_to_expiration: bool = True,
        risk_free_rate: float = 0.045
    ) -> Dict[str, Any]:
        """
        Executes the systematic 30-DTE Wheel backtest.
        - hold_to_expiration=True (Default): Holds each option ~30 days to expiration (10-12 monthly cycles/year).
        - hold_to_expiration=False: Active scalping with 50% early profit-taking and 21-DTE roll.
        """
        df_sym, df_bench = self.fetch_historical_bars(symbol, benchmark, lookback_years)

        # Compute 30-day historical rolling annualized volatility
        df_sym["log_ret"] = np.log(df_sym["close"] / df_sym["close"].shift(1))
        df_sym["vol_30"] = df_sym["log_ret"].rolling(30).std() * np.sqrt(252)
        df_sym["vol_30"] = df_sym["vol_30"].fillna(0.25).clip(lower=0.12, upper=1.20)

        # Align to the start of the requested lookback window
        cutoff_date = datetime.now() - timedelta(days=int(lookback_years * 365.25))
        df_sym = df_sym[df_sym.index >= pd.Timestamp(cutoff_date)].copy()
        df_bench = df_bench[df_bench.index >= pd.Timestamp(cutoff_date)].copy()

        if len(df_sym) < 20:
            raise ValueError(f"Insufficient historical data points ({len(df_sym)}) for {symbol}.")

        # Simulation State Tracking
        state = "CASH_CSP" # "CASH_CSP" or "HOLDING_SHARES"
        cash = initial_capital
        shares = 0
        cost_basis = 0.0

        active_option: Optional[Dict[str, Any]] = None
        trade_log: List[Dict[str, Any]] = []
        equity_records: List[Dict[str, Any]] = []

        # Benchmark Initial Value for relative tracking
        bench_close_initial = float(df_bench["close"].iloc[0])
        sym_close_initial = float(df_sym["close"].iloc[0])

        dates = df_sym.index

        for i, dt in enumerate(dates):
            current_spot = float(df_sym.loc[dt, "close"])
            current_vol = float(df_sym.loc[dt, "vol_30"])
            date_str = dt.strftime("%Y-%m-%d")

            # ── 1. If No Position Open, Write New 30-DTE Option ──
            if active_option is None:
                if state == "CASH_CSP":
                    # Determine CSP Strike (~8-10% OTM)
                    strike = round(current_spot * (1.0 - otm_pct), 2)
                    strike = max(1.0, strike)
                    T = target_dte / 365.0
                    prem = black_scholes_price(current_spot, strike, T, risk_free_rate, current_vol, "put")
                    prem = max(0.10, prem)

                    # Collateral required per contract = strike * 100
                    contracts = max(1, int(cash // (strike * 100)))
                    max_contracts = max(1, int(initial_capital * 0.95 // (strike * 100)))
                    contracts = min(contracts, max_contracts)

                    active_option = {
                        "type": "put",
                        "strike": strike,
                        "entry_spot": current_spot,
                        "entry_premium": prem,
                        "contracts": contracts,
                        "entry_date": dt,
                        "entry_date_str": date_str,
                        "target_dte": target_dte,
                        "remaining_dte": target_dte,
                        "vol": current_vol
                    }

                elif state == "HOLDING_SHARES":
                    # Determine Covered Call Strike (max of OTM or cost basis)
                    strike = max(round(current_spot * (1.0 + otm_pct), 2), round(cost_basis, 2))
                    T = target_dte / 365.0
                    prem = black_scholes_price(current_spot, strike, T, risk_free_rate, current_vol, "call")
                    prem = max(0.10, prem)
                    contracts = max(1, shares // 100)

                    active_option = {
                        "type": "call",
                        "strike": strike,
                        "entry_spot": current_spot,
                        "entry_premium": prem,
                        "contracts": contracts,
                        "entry_date": dt,
                        "entry_date_str": date_str,
                        "target_dte": target_dte,
                        "remaining_dte": target_dte,
                        "vol": current_vol
                    }

            # ── 2. Manage Active Option Day-by-Day ──
            option_current_value = 0.0
            closed_this_day = False

            if active_option is not None:
                # Decrement DTE
                calendar_days_passed = (dt - active_option["entry_date"]).days
                active_option["remaining_dte"] = max(0, active_option["target_dte"] - calendar_days_passed)
                rem_dte = active_option["remaining_dte"]
                T_rem = max(rem_dte, 0.5) / 365.0

                current_prem = black_scholes_price(
                    current_spot,
                    active_option["strike"],
                    T_rem,
                    risk_free_rate,
                    current_vol,
                    active_option["type"]
                )
                entry_prem = active_option["entry_premium"]
                contracts = active_option["contracts"]
                strike = active_option["strike"]

                # Total option liability: contracts * 100 * current_prem
                option_liability = contracts * 100 * current_prem

                # Check Early Exit Rules (Only if NOT in hold_to_expiration mode)
                if not hold_to_expiration:
                    profit_pct = (entry_prem - current_prem) / entry_prem
                    if profit_pct >= profit_target_pct:
                        # Capture early profit
                        net_profit = contracts * 100 * (entry_prem - current_prem)
                        cash += net_profit
                        trade_log.append({
                            "id": f"WHL-{len(trade_log)+1:03d}",
                            "strategy": "CSP" if active_option["type"] == "put" else "CC",
                            "symbol": symbol,
                            "entry_date": active_option["entry_date_str"],
                            "exit_date": date_str,
                            "strike": strike,
                            "entry_premium": round(entry_prem, 2),
                            "exit_premium": round(current_prem, 2),
                            "contracts": contracts,
                            "net_pnl": round(net_profit, 2),
                            "return_pct": round(profit_pct * 100, 1),
                            "outcome": "50% Profit Captured Early",
                            "days_held": calendar_days_passed
                        })
                        active_option = None
                        closed_this_day = True

                    elif rem_dte <= gamma_roll_dte and ((active_option["type"] == "put" and current_spot > strike) or (active_option["type"] == "call" and current_spot < strike)):
                        net_profit = contracts * 100 * (entry_prem - current_prem)
                        cash += net_profit
                        trade_log.append({
                            "id": f"WHL-{len(trade_log)+1:03d}",
                            "strategy": "CSP" if active_option["type"] == "put" else "CC",
                            "symbol": symbol,
                            "entry_date": active_option["entry_date_str"],
                            "exit_date": date_str,
                            "strike": strike,
                            "entry_premium": round(entry_prem, 2),
                            "exit_premium": round(current_prem, 2),
                            "contracts": contracts,
                            "net_pnl": round(net_profit, 2),
                            "return_pct": round(profit_pct * 100, 1),
                            "outcome": "21-DTE Gamma Roll (Gains Locked)",
                            "days_held": calendar_days_passed
                        })
                        active_option = None
                        closed_this_day = True

                # Check Expiration (DTE <= 0)
                if not closed_this_day and rem_dte <= 0:
                    if active_option["type"] == "put":
                        if current_spot >= strike:
                            # Expired worthless (100% profit)
                            net_profit = contracts * 100 * entry_prem
                            cash += net_profit
                            trade_log.append({
                                "id": f"WHL-{len(trade_log)+1:03d}",
                                "strategy": "CSP",
                                "symbol": symbol,
                                "entry_date": active_option["entry_date_str"],
                                "exit_date": date_str,
                                "strike": strike,
                                "entry_premium": round(entry_prem, 2),
                                "exit_premium": 0.0,
                                "contracts": contracts,
                                "net_pnl": round(net_profit, 2),
                                "return_pct": 100.0,
                                "outcome": "Expired Worthless (100% Premium Kept)",
                                "days_held": calendar_days_passed
                            })
                            state = "CASH_CSP"
                        else:
                            # Assigned! Buy 100 shares per contract at strike
                            shares_bought = contracts * 100
                            cost_basis = strike - entry_prem
                            shares = shares_bought
                            cash -= (shares_bought * strike) - (shares_bought * entry_prem)
                            trade_log.append({
                                "id": f"WHL-{len(trade_log)+1:03d}",
                                "strategy": "CSP",
                                "symbol": symbol,
                                "entry_date": active_option["entry_date_str"],
                                "exit_date": date_str,
                                "strike": strike,
                                "entry_premium": round(entry_prem, 2),
                                "exit_premium": round(max(0.0, strike - current_spot), 2),
                                "contracts": contracts,
                                "net_pnl": round((current_spot - cost_basis) * shares_bought, 2),
                                "return_pct": round(((current_spot - cost_basis) / cost_basis) * 100, 1),
                                "outcome": f"Assigned @ ${strike:.2f} (Net Basis: ${cost_basis:.2f})",
                                "days_held": calendar_days_passed
                            })
                            state = "HOLDING_SHARES"

                        active_option = None
                        closed_this_day = True

                    elif active_option["type"] == "call":
                        if current_spot <= strike:
                            # Expired worthless, keep shares and full call premium
                            net_profit = contracts * 100 * entry_prem
                            cash += net_profit
                            cost_basis = max(1.0, cost_basis - entry_prem)
                            trade_log.append({
                                "id": f"WHL-{len(trade_log)+1:03d}",
                                "strategy": "CC",
                                "symbol": symbol,
                                "entry_date": active_option["entry_date_str"],
                                "exit_date": date_str,
                                "strike": strike,
                                "entry_premium": round(entry_prem, 2),
                                "exit_premium": 0.0,
                                "contracts": contracts,
                                "net_pnl": round(net_profit, 2),
                                "return_pct": 100.0,
                                "outcome": "Expired Worthless (Yield Harvested)",
                                "days_held": calendar_days_passed
                            })
                            state = "HOLDING_SHARES"
                        else:
                            # Called Away! Sell shares at strike
                            shares_sold = contracts * 100
                            proceeds = (shares_sold * strike) + (shares_sold * entry_prem)
                            pnl = (strike - cost_basis + entry_prem) * shares_sold
                            cash += proceeds
                            shares = 0
                            trade_log.append({
                                "id": f"WHL-{len(trade_log)+1:03d}",
                                "strategy": "CC",
                                "symbol": symbol,
                                "entry_date": active_option["entry_date_str"],
                                "exit_date": date_str,
                                "strike": strike,
                                "entry_premium": round(entry_prem, 2),
                                "exit_premium": round(max(0.0, current_spot - strike), 2),
                                "contracts": contracts,
                                "net_pnl": round(pnl, 2),
                                "return_pct": round((pnl / (cost_basis * shares_sold)) * 100, 1),
                                "outcome": f"Called Away @ ${strike:.2f} (Profit Realized)",
                                "days_held": calendar_days_passed
                            })
                            state = "CASH_CSP"

                        active_option = None
                        closed_this_day = True

            # ── 3. Calculate Composite Portfolio Equity Today ──
            current_shares_val = shares * current_spot
            current_opt_liability = 0.0
            if active_option is not None:
                current_opt_liability = active_option["contracts"] * 100 * current_prem

            portfolio_equity = cash + current_shares_val - current_opt_liability

            # Benchmark Equity
            bench_spot = float(df_bench.loc[dt, "close"]) if dt in df_bench.index else bench_close_initial
            bench_cum_pct = ((bench_spot - bench_close_initial) / bench_close_initial) * 100.0
            underlying_cum_pct = ((current_spot - sym_close_initial) / sym_close_initial) * 100.0
            strategy_cum_pct = ((portfolio_equity - initial_capital) / initial_capital) * 100.0

            equity_records.append({
                "date": date_str,
                "portfolio_equity": round(portfolio_equity, 2),
                "strategy_cum_pct": round(strategy_cum_pct, 2),
                "underlying_cum_pct": round(underlying_cum_pct, 2),
                "benchmark_cum_pct": round(bench_cum_pct, 2),
                "state": state,
                "spot": round(current_spot, 2),
                "shares": shares,
                "cash": round(cash, 2)
            })

        # ── 4. Generate Aligned Daily Return Series for QuantStats ──
        eq_df = pd.DataFrame(equity_records)
        eq_df["date_dt"] = pd.to_datetime(eq_df["date"])
        eq_df.set_index("date_dt", inplace=True)

        eq_df["strategy_daily_ret"] = eq_df["portfolio_equity"].pct_change().fillna(0.0)
        eq_df["underlying_daily_ret"] = df_sym["close"].pct_change().reindex(eq_df.index).fillna(0.0)
        eq_df["benchmark_daily_ret"] = df_bench["close"].pct_change().reindex(eq_df.index).fillna(0.0)

        # Compute underwater drawdown series
        strat_peaks = eq_df["portfolio_equity"].expanding().max()
        eq_df["strategy_drawdown"] = ((eq_df["portfolio_equity"] - strat_peaks) / strat_peaks) * 100.0

        bench_prices = df_bench["close"].reindex(eq_df.index).ffill()
        bench_peaks = bench_prices.expanding().max()
        eq_df["benchmark_drawdown"] = ((bench_prices - bench_peaks) / bench_peaks) * 100.0

        # Build Recharts-ready Equity Curves
        equity_curves = []
        for dt, row in eq_df.iterrows():
            equity_curves.append({
                "date": dt.strftime("%Y-%m-%d"),
                "strategy": round(float(row["strategy_cum_pct"]), 2),
                "underlying": round(float(row["underlying_cum_pct"]), 2),
                "benchmark": round(float(row["benchmark_cum_pct"]), 2),
                "strategy_drawdown": round(float(row["strategy_drawdown"]), 2),
                "benchmark_drawdown": round(float(row["benchmark_drawdown"]), 2)
            })

        return {
            "strategy_returns": eq_df["strategy_daily_ret"],
            "underlying_returns": eq_df["underlying_daily_ret"],
            "benchmark_returns": eq_df["benchmark_daily_ret"],
            "equity_curves": equity_curves,
            "trade_log": trade_log,
            "final_equity": float(eq_df["portfolio_equity"].iloc[-1]),
            "initial_capital": initial_capital,
            "symbol": symbol.upper(),
            "benchmark": benchmark.upper()
        }
