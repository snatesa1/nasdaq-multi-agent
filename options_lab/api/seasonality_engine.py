import os
import json
import logging
import requests
import numpy as np
from typing import Dict, Any, List, Optional
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from . import db as database

load_dotenv()
logger = logging.getLogger("seasonality-engine")


class SeasonalityEngine:
    """
    Descriptive Summary:
        Quantitative Seasonality, 52-Week IV/HV Volatility Rank, and Earnings Blackout Shield Engine.
        Empirically evaluates 8-year historical monthly win rates and drawdowns, rolling volatility
        percentiles, and upcoming corporate earnings events to dynamically calibrate Cash-Secured Put
        strike buffers across the focus universe without relying on qualitative narrative assumptions.

    Parameters / Encapsulation:
        cache_ttl_days (int): Time-to-live in days for SQLite cached seasonality metrics (default: 7).
        alpaca_key (str): Alpaca API Key ID sourced from environment.
        alpaca_secret (str): Alpaca Secret Key sourced from environment.
        alpaca_data_url (str): Alpaca Data v2 API endpoint.

    Returns / Internal State:
        Maintains HTTP session headers and per-symbol cached seasonality analysis payloads.

    Exceptions / Side Effects:
        Persists and queries analysis payloads to/from SQLite `saxo_cache` table.
        Gracefully handles API rate limits, network timeouts, and missing ticker data.

    Usage Example:
        >>> engine = SeasonalityEngine()
        >>> report = engine.evaluate_symbol_seasonality("AAPL", current_spot=220.0, dte=35)
        >>> print(report["recommended_otm_buffer_pct"], report["seasonality_bias"])
        14.0 BEARISH_SEASONAL
    """

    def __init__(self, cache_ttl_days: int = 7):
        self.cache_ttl_days = cache_ttl_days
        self.alpaca_key = os.getenv("ALPACA_API_KEY", "")
        self.alpaca_secret = os.getenv("ALPACA_SECRET_KEY", "")
        self.alpaca_data_url = "https://data.alpaca.markets/v2"
        self._headers = {
            "APCA-API-KEY-ID": self.alpaca_key,
            "APCA-API-SECRET-KEY": self.alpaca_secret
        }

    def fetch_monthly_bars(self, symbol: str, start_year: int = 2018) -> List[Dict[str, Any]]:
        """
        Descriptive Summary:
            Queries 8+ years of split-adjusted monthly OHLCV bars from Alpaca Data API
            for quantitative multi-year monthly return and intra-month drawdown distribution analysis.

        Parameters:
            symbol (str): Equity ticker symbol (e.g. 'AAPL', 'MSFT').
            start_year (int): Starting calendar year for historical sample (default: 2018).

        Returns:
            List[Dict[str, Any]]: List of monthly bar dictionaries with 't', 'o', 'h', 'l', 'c', 'v'.

        Exceptions / Side Effects:
            Non-throwing. Returns empty list if network fails or credentials are invalid.

        Usage Example:
            >>> bars = engine.fetch_monthly_bars("AAPL")
            >>> assert len(bars) >= 80
        """
        if not self.alpaca_key or not self.alpaca_secret:
            logger.warning("Alpaca API credentials not configured. Cannot fetch monthly bars.")
            return []

        try:
            url = f"{self.alpaca_data_url}/stocks/{symbol.upper()}/bars"
            params = {
                "timeframe": "1Month",
                "start": f"{start_year}-01-01",
                "limit": 150
            }
            res = requests.get(url, headers=self._headers, params=params, timeout=8.0)
            if res.status_code == 200:
                data = res.json()
                return data.get("bars", [])
            else:
                logger.warning(f"Alpaca monthly bars query returned HTTP {res.status_code} for {symbol}")
        except Exception as e:
            logger.error(f"Failed to fetch monthly bars for {symbol}: {e}")

        return []

    def fetch_daily_bars(self, symbol: str, lookback_days: int = 365) -> List[Dict[str, Any]]:
        """
        Descriptive Summary:
            Queries 252+ daily OHLCV trading bars from Alpaca Data API over the trailing 12 months
            to calculate rolling realized volatility distributions and 52-week IV/HV rank.

        Parameters:
            symbol (str): Equity ticker symbol.
            lookback_days (int): Trailing calendar days to retrieve (default: 365).

        Returns:
            List[Dict[str, Any]]: List of daily bar dictionaries.

        Exceptions / Side Effects:
            Non-throwing. Returns empty list on network or API failures.

        Usage Example:
            >>> bars = engine.fetch_daily_bars("AAPL")
            >>> assert len(bars) >= 200
        """
        if not self.alpaca_key or not self.alpaca_secret:
            return []

        try:
            start_date = (datetime.now(timezone.utc) - timedelta(days=lookback_days + 15)).strftime("%Y-%m-%d")
            url = f"{self.alpaca_data_url}/stocks/{symbol.upper()}/bars"
            params = {
                "timeframe": "1Day",
                "start": start_date,
                "limit": 300
            }
            res = requests.get(url, headers=self._headers, params=params, timeout=8.0)
            if res.status_code == 200:
                return res.json().get("bars", [])
        except Exception as e:
            logger.error(f"Failed to fetch daily bars for {symbol}: {e}")

        return []

    def calculate_52w_volatility_rank(
        self,
        symbol: str,
        daily_bars: Optional[List[Dict[str, Any]]] = None,
        current_iv: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Descriptive Summary:
            Computes rolling 20-day annualized realized historical volatility (HV) across 252 trading days,
            identifies 52-week minimum and maximum bounds, and calculates the 52-Week IV/HV Rank % to
            determine if option premiums are quantitatively rich or compressed.

        Parameters:
            symbol (str): Equity ticker symbol.
            daily_bars (Optional[List[Dict[str, Any]]]): Pre-fetched daily bars. If None, fetches live.
            current_iv (Optional[float]): Live implied volatility from options quote (e.g. 0.28 = 28%).

        Returns:
            Dict[str, Any]: Volatility rank structure containing:
                - 'current_volatility_pct' (float): Current 20d annualized volatility or quoted IV.
                - 'min_volatility_pct' (float): 52-week lowest rolling volatility.
                - 'max_volatility_pct' (float): 52-week highest rolling volatility.
                - 'iv_rank_pct' (float): 52-week IV/HV Rank (0.0% to 100.0%).
                - 'is_rich_premium' (bool): True if IV Rank >= 40.0% (optimal for selling puts).
                - 'is_cheap_premium' (bool): True if IV Rank < 25.0% (caution for option writing).
                - 'volatility_regime' (str): Descriptive classification string.

        Exceptions / Side Effects:
            None. Non-throwing mathematical audit with deterministic fallbacks.

        Usage Example:
            >>> vol = engine.calculate_52w_volatility_rank("AAPL")
            >>> print(vol["iv_rank_pct"], vol["is_rich_premium"])
        """
        bars = daily_bars if daily_bars is not None else self.fetch_daily_bars(symbol)
        if not bars or len(bars) < 25:
            # Deterministic baseline fallback
            return {
                "current_volatility_pct": round((current_iv * 100.0) if current_iv else 25.0, 1),
                "min_volatility_pct": 15.0,
                "max_volatility_pct": 40.0,
                "iv_rank_pct": 40.0,
                "is_rich_premium": True,
                "is_cheap_premium": False,
                "volatility_regime": "ELEVATED_PREMIUM_SWEETSPOT",
                "data_points": len(bars)
            }

        closes = [float(b["c"]) for b in bars if b.get("c") and float(b["c"]) > 0]
        if len(closes) < 25:
            return {
                "current_volatility_pct": 25.0,
                "min_volatility_pct": 15.0,
                "max_volatility_pct": 40.0,
                "iv_rank_pct": 40.0,
                "is_rich_premium": True,
                "is_cheap_premium": False,
                "volatility_regime": "ELEVATED_PREMIUM_SWEETSPOT",
                "data_points": len(closes)
            }

        log_returns = np.diff(np.log(closes))
        window = 20
        rolling_vols = []
        for i in range(window, len(log_returns) + 1):
            chunk = log_returns[i - window : i]
            ann_vol = float(np.std(chunk) * np.sqrt(252) * 100.0)
            rolling_vols.append(ann_vol)

        if not rolling_vols:
            rolling_vols = [25.0]

        min_vol = min(rolling_vols)
        max_vol = max(rolling_vols)
        curr_vol = (current_iv * 100.0) if (current_iv and current_iv > 0) else rolling_vols[-1]

        denom = max(0.5, max_vol - min_vol)
        rank_pct = max(0.0, min(100.0, (curr_vol - min_vol) / denom * 100.0))

        if rank_pct >= 70.0:
            regime = "HIGH_VOLATILITY_EXPANSION"
        elif rank_pct >= 40.0:
            regime = "ELEVATED_PREMIUM_SWEETSPOT"
        elif rank_pct >= 25.0:
            regime = "MEDIAN_EQUILIBRIUM"
        else:
            regime = "COMPRESSED_VOLATILITY"

        return {
            "current_volatility_pct": round(curr_vol, 1),
            "min_volatility_pct": round(min_vol, 1),
            "max_volatility_pct": round(max_vol, 1),
            "iv_rank_pct": round(rank_pct, 1),
            "is_rich_premium": rank_pct >= 40.0,
            "is_cheap_premium": rank_pct < 25.0,
            "volatility_regime": regime,
            "data_points": len(rolling_vols)
        }

    def calculate_monthly_seasonality(
        self,
        symbol: str,
        monthly_bars: Optional[List[Dict[str, Any]]] = None,
        target_month: Optional[int] = None
    ) -> Dict[str, Any]:
        r"""
        Descriptive Summary:
            Aggregates 8+ years of monthly OHLCV returns and intra-month drawdowns by calendar month,
            computing empirical win rate %, median return, and max historical drawdown for the target month.

        Parameters:
            symbol (str): Equity ticker symbol.
            monthly_bars (Optional[List[Dict[str, Any]]]): Pre-fetched monthly bars. If None, fetches live.
            target_month (Optional[int]): Target month number (1-12). Defaults to current calendar month.

        Returns:
            Dict[str, Any]: Comprehensive seasonality breakdown for all months and target month evaluation:
                - 'target_month' (int): Calendar month evaluated.
                - 'target_month_name' (str): Month name (e.g. 'September').
                - 'sample_years' (int): Total annual occurrences in sample ($N \ge 8$).
                - 'win_rate_pct' (float): % of years month ended positive.
                - 'median_return_pct' (float): Median percentage return.
                - 'avg_return_pct' (float): Mean percentage return.
                - 'worst_drawdown_pct' (float): Maximum historical intra-month drawdown drop.
                - 'seasonality_bias' (str): 'BULLISH_SEASONAL', 'BEARISH_SEASONAL', or 'NEUTRAL_SEASONAL'.
                - 'all_months' (Dict[int, Dict[str, Any]]): 12-month complete distribution table.

        Exceptions / Side Effects:
            None. Non-throwing statistical calculation.

        Usage Example:
            >>> s = engine.calculate_monthly_seasonality("AAPL", target_month=9)
            >>> print(s["target_month_name"], s["win_rate_pct"], s["seasonality_bias"])
            September 44.4 BEARISH_SEASONAL
        """
        bars = monthly_bars if monthly_bars is not None else self.fetch_monthly_bars(symbol)
        curr_month = target_month or datetime.now().month

        MONTH_NAMES = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        }

        by_month = defaultdict(list)
        for b in bars:
            try:
                t_str = str(b.get("t", ""))
                dt = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                m = dt.month
                o = float(b.get("o", 0.0))
                c = float(b.get("c", 0.0))
                l = float(b.get("l", 0.0))
                if o > 0:
                    ret = (c - o) / o * 100.0
                    dd = (l - o) / o * 100.0
                    by_month[m].append({"year": dt.year, "ret": ret, "dd": dd})
            except Exception:
                continue

        all_months = {}
        for m in range(1, 13):
            items = by_month[m]
            rets = [x["ret"] for x in items]
            dds = [x["dd"] for x in items]
            win_rate = (sum(1 for r in rets if r > 0) / len(rets) * 100.0) if rets else 50.0
            med_ret = float(np.median(rets)) if rets else 0.0
            avg_ret = float(np.mean(rets)) if rets else 0.0
            worst_dd = min(dds) if dds else -5.0

            all_months[m] = {
                "month_num": m,
                "month_name": MONTH_NAMES.get(m, f"Month {m}"),
                "sample_count": len(rets),
                "win_rate_pct": round(win_rate, 1),
                "median_return_pct": round(med_ret, 2),
                "avg_return_pct": round(avg_ret, 2),
                "worst_drawdown_pct": round(worst_dd, 2)
            }

        target_stats = all_months.get(curr_month, {
            "month_num": curr_month,
            "month_name": MONTH_NAMES.get(curr_month, ""),
            "sample_count": 8,
            "win_rate_pct": 50.0,
            "median_return_pct": 0.0,
            "avg_return_pct": 0.0,
            "worst_drawdown_pct": -8.0
        })

        # Seasonality bias resolution
        wr = target_stats["win_rate_pct"]
        med = target_stats["median_return_pct"]
        worst = target_stats["worst_drawdown_pct"]

        if wr >= 62.5 and med >= 1.5:
            bias = "BULLISH_SEASONAL"
        elif wr < 50.0 or med <= -1.0 or worst <= -15.0:
            bias = "BEARISH_SEASONAL"
        else:
            bias = "NEUTRAL_SEASONAL"

        return {
            "target_month": curr_month,
            "target_month_name": MONTH_NAMES.get(curr_month, ""),
            "sample_years": target_stats["sample_count"],
            "win_rate_pct": target_stats["win_rate_pct"],
            "median_return_pct": target_stats["median_return_pct"],
            "avg_return_pct": target_stats["avg_return_pct"],
            "worst_drawdown_pct": target_stats["worst_drawdown_pct"],
            "seasonality_bias": bias,
            "all_months": all_months
        }

    def check_earnings_blackout(self, symbol: str, dte: int = 35) -> Dict[str, Any]:
        """
        Descriptive Summary:
            Audits whether an upcoming corporate quarterly earnings announcement falls within
            the proposed option contract's lifespan (days_to_earnings <= dte + 3 days),
            triggering the Earnings Blackout Shield to prevent gap-down assignment risk.

        Parameters:
            symbol (str): Underlying equity ticker symbol.
            dte (int): Days to expiration of the proposed option contract (default: 35).

        Returns:
            Dict[str, Any]: Earnings audit structure containing:
                - 'has_earnings_blackout' (bool): True if earnings occurs prior to or during expiry.
                - 'next_earnings_date' (Optional[str]): Upcoming earnings date YYYY-MM-DD.
                - 'days_until_earnings' (Optional[int]): Calendar days until announcement.
                - 'is_within_option_lifespan' (bool): True if days_until_earnings <= dte + 3.
                - 'risk_warning' (Optional[str]): Actionable warning message.
                - 'recommended_action' (str): Prescribed action ('WIDEN_OTM_BUFFER', 'SAFE_CLEARANCE', etc.).

        Exceptions / Side Effects:
            Catches yfinance or calendar network errors and safely defaults to has_earnings_blackout=False.

        Usage Example:
            >>> res = engine.check_earnings_blackout("AAPL", dte=35)
            >>> print(res["has_earnings_blackout"], res["next_earnings_date"])
        """
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol.upper())
            cal = ticker.calendar
            next_date = None

            if cal and isinstance(cal, dict) and cal.get("Earnings Date"):
                dates = cal["Earnings Date"]
                if dates and len(dates) > 0:
                    d0 = dates[0]
                    next_date = d0.strftime("%Y-%m-%d") if hasattr(d0, "strftime") else str(d0)[:10]

            if not next_date and hasattr(ticker, "earnings_dates") and ticker.earnings_dates is not None:
                ed = ticker.earnings_dates
                if not ed.empty:
                    now_ts = datetime.now(timezone.utc)
                    future = [d for d in ed.index if (d.tzinfo and d > now_ts) or (not d.tzinfo and d > datetime.now())]
                    if future:
                        next_date = future[0].strftime("%Y-%m-%d")

            if next_date:
                earnings_dt = datetime.strptime(next_date, "%Y-%m-%d")
                today_dt = datetime.now()
                days_diff = (earnings_dt - today_dt).days

                # Earnings falls within option lifespan (+ 3 days buffer)
                is_within = 0 <= days_diff <= (dte + 3)
                if is_within:
                    return {
                        "has_earnings_blackout": True,
                        "next_earnings_date": next_date,
                        "days_until_earnings": days_diff,
                        "is_within_option_lifespan": True,
                        "risk_warning": (
                            f"EARNINGS BLACKOUT SHIELD ACTIVE: {symbol} reports earnings on {next_date} "
                            f"({days_diff} days away), falling within your {dte}-DTE option lifespan. "
                            f"Binary earnings gap risk requires widening strike buffer to >= 15% OTM."
                        ),
                        "recommended_action": "WIDEN_OTM_BUFFER"
                    }
                else:
                    return {
                        "has_earnings_blackout": False,
                        "next_earnings_date": next_date,
                        "days_until_earnings": days_diff,
                        "is_within_option_lifespan": False,
                        "risk_warning": None,
                        "recommended_action": "SAFE_CLEARANCE"
                    }
        except Exception as e:
            logger.debug(f"Earnings blackout check non-critical for {symbol}: {e}")

        return {
            "has_earnings_blackout": False,
            "next_earnings_date": None,
            "days_until_earnings": None,
            "is_within_option_lifespan": False,
            "risk_warning": None,
            "recommended_action": "NO_EARNINGS_DETECTED"
        }

    def evaluate_symbol_seasonality(
        self,
        symbol: str,
        current_spot: float = 0.0,
        current_iv: Optional[float] = None,
        dte: int = 35,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Descriptive Summary:
            Synthesizes all quantitative dimensions (8-year monthly win rates/drawdowns, 52-week IV/HV rank,
            and earnings blackout shield) into a unified risk profile and dynamically computes the
            optimal Out-Of-The-Money (OTM) strike buffer (8% to 18%) for Cash-Secured Put writing.

        Parameters:
            symbol (str): Equity ticker symbol.
            current_spot (float): Current market price of underlying.
            current_iv (Optional[float]): Live option implied volatility if available.
            dte (int): Proposed trade days to expiration (default: 35).
            force_refresh (bool): If True, bypasses SQLite cache.

        Returns:
            Dict[str, Any]: Comprehensive unified seasonality assessment containing:
                - 'symbol' (str): Evaluated ticker.
                - 'current_spot' (float): Market spot price.
                - 'recommended_otm_buffer_pct' (float): Dynamically tuned OTM strike buffer (e.g. 10.0%, 14.0%, 18.0%).
                - 'recommended_strike' (float): Suggested strike price after dynamic buffer.
                - 'seasonality_bias' (str): 'BULLISH_SEASONAL', 'BEARISH_SEASONAL', or 'NEUTRAL_SEASONAL'.
                - 'target_month_name' (str): Current calendar month.
                - 'win_rate_pct' (float): Historical win rate for this month.
                - 'median_return_pct' (float): Historical median return for this month.
                - 'worst_drawdown_pct' (float): Worst historical intra-month drawdown.
                - 'iv_rank_pct' (float): 52-week IV/HV Rank %.
                - 'volatility_regime' (str): Volatility regime classification.
                - 'has_earnings_blackout' (bool): True if earnings fall inside contract window.
                - 'next_earnings_date' (Optional[str]): Earnings date if known.
                - 'buffer_rationale' (str): Clear institutional explanation of why the buffer was tuned.
                - 'cached_at' (str): ISO timestamp of calculation.

        Exceptions / Side Effects:
            Reads and writes cache records in SQLite `saxo_cache` table.

        Usage Example:
            >>> report = engine.evaluate_symbol_seasonality("AAPL", current_spot=220.0, dte=35)
            >>> print(report["recommended_strike"], report["buffer_rationale"])
        """
        sym = symbol.upper().strip()
        cache_key = f"seasonality_{sym}"

        # 1. Check persistent SQLite cache
        if not force_refresh:
            try:
                cached = database.get_saxo_cache(cache_key)
                if cached and isinstance(cached, dict):
                    cached_at_str = cached.get("cached_at", "")
                    if cached_at_str:
                        cached_at = datetime.fromisoformat(cached_at_str)
                        if (datetime.now(timezone.utc) - cached_at).days < self.cache_ttl_days:
                            # Re-calibrate strike if current_spot changed
                            if current_spot > 0:
                                buf = cached.get("recommended_otm_buffer_pct", 10.0)
                                cached["current_spot"] = current_spot
                                cached["recommended_strike"] = round(current_spot * (1.0 - buf / 100.0), 2)
                            return cached
            except Exception as e:
                logger.debug(f"Seasonality cache read non-critical: {e}")

        # 2. Live Quantitative Evaluation
        monthly_bars = self.fetch_monthly_bars(sym)
        daily_bars = self.fetch_daily_bars(sym)

        seasonality = self.calculate_monthly_seasonality(sym, monthly_bars=monthly_bars)
        vol_rank = self.calculate_52w_volatility_rank(sym, daily_bars=daily_bars, current_iv=current_iv)
        earnings = self.check_earnings_blackout(sym, dte=dte)

        # 3. Dynamic OTM Buffer Calibration
        # Baseline institutional CSP buffer: 10.0% OTM (~0.20 Delta)
        base_buffer = 10.0
        rationale_items = [f"Baseline 10.0% OTM (~0.20 Delta) for systematic monthly income."]

        # Adjust for Seasonality Bias
        bias = seasonality["seasonality_bias"]
        if bias == "BEARISH_SEASONAL":
            base_buffer += 4.0
            rationale_items.append(
                f"Historical {seasonality['target_month_name']} seasonality is weak "
                f"(Win Rate: {seasonality['win_rate_pct']}%, Median Return: {seasonality['median_return_pct']:+.1f}%). "
                f"Added +4.0% OTM buffer."
            )
        elif bias == "BULLISH_SEASONAL":
            # Strong seasonal support allows standard optimal premium harvest
            rationale_items.append(
                f"Historical {seasonality['target_month_name']} seasonality is strong "
                f"(Win Rate: {seasonality['win_rate_pct']}%, Median Return: {seasonality['median_return_pct']:+.1f}%)."
            )

        # Adjust for Worst Historical Drawdown
        worst_dd = seasonality["worst_drawdown_pct"]
        if worst_dd <= -20.0:
            base_buffer += 2.0
            rationale_items.append(f"High historical intra-month tail risk ({worst_dd:.1f}% max drop). Added +2.0% buffer.")

        # Adjust for Earnings Blackout Shield
        if earnings["has_earnings_blackout"]:
            base_buffer += 4.0
            rationale_items.append(
                f"Upcoming earnings announcement on {earnings['next_earnings_date']} falls within option lifespan. "
                f"Added +4.0% OTM gap protection."
            )

        # Adjust for IV Rank (Reward selling when rich, caution when compressed)
        iv_rank = vol_rank["iv_rank_pct"]
        if vol_rank["is_rich_premium"] and not earnings["has_earnings_blackout"] and bias != "BEARISH_SEASONAL":
            # Rich premium environment allows tighter sweet spot harvest
            base_buffer = max(8.0, base_buffer - 1.0)
            rationale_items.append(f"Elevated IV Rank ({iv_rank:.1f}%) provides rich premium harvest.")
        elif vol_rank["is_cheap_premium"]:
            base_buffer += 1.0
            rationale_items.append(f"Compressed IV Rank ({iv_rank:.1f}%) provides thin premium; widened buffer +1.0%.")

        # Clamp final buffer between 8.0% and 18.0% OTM
        final_buffer = round(max(8.0, min(18.0, base_buffer)), 1)
        rec_strike = round(current_spot * (1.0 - final_buffer / 100.0), 2) if current_spot > 0 else 0.0

        result = {
            "symbol": sym,
            "current_spot": round(current_spot, 2),
            "recommended_otm_buffer_pct": final_buffer,
            "recommended_strike": rec_strike,
            "seasonality_bias": bias,
            "target_month_name": seasonality["target_month_name"],
            "win_rate_pct": seasonality["win_rate_pct"],
            "median_return_pct": seasonality["median_return_pct"],
            "worst_drawdown_pct": seasonality["worst_drawdown_pct"],
            "sample_years": seasonality["sample_years"],
            "iv_rank_pct": vol_rank["iv_rank_pct"],
            "volatility_regime": vol_rank["volatility_regime"],
            "current_volatility_pct": vol_rank["current_volatility_pct"],
            "has_earnings_blackout": earnings["has_earnings_blackout"],
            "next_earnings_date": earnings.get("next_earnings_date"),
            "days_until_earnings": earnings.get("days_until_earnings"),
            "risk_warning": earnings.get("risk_warning"),
            "buffer_rationale": " ".join(rationale_items),
            "cached_at": datetime.now(timezone.utc).isoformat()
        }

        # 4. Save to persistent SQLite cache
        try:
            database.set_saxo_cache(cache_key, result)
        except Exception as e_save:
            logger.debug(f"Failed to cache seasonality analysis for {sym}: {e_save}")

        return result
