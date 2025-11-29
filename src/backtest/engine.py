import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Optional
from ..config import Config
from ..universe import Universe
from ..data_providers.yfinance_provider import YFinanceProvider
from ..data_providers.fred_provider import FredProvider
from ..data_providers.nav_provider import NavProvider
from ..signals.premium_discount import calculate_premium_discount_signal
from ..signals.volume_liquidity import calculate_volume_liquidity_signal
from ..signals.divergence import calculate_divergence_signal
from ..signals.cross_asset_stress import calculate_cross_asset_signal
from .metrics import calculate_metrics

logger = logging.getLogger(__name__)


class BacktestEngine:
  def __init__(self, config: Config):
    self.config = config
    self.universe = Universe(config)
    cache_dir = getattr(config, 'cache_dir', 'data/cache')
    self.yf = YFinanceProvider(cache_dir=cache_dir)
    self.fred = FredProvider(cache_dir=cache_dir)
    self.nav = NavProvider(self.yf)

  def run(self, start_date: str, end_date: str) -> Dict[str, Any]:
    logger.info(f"Starting backtest from {start_date} to {end_date}...")

    # 1. Fetch Data
    tickers = self.universe.valid_tickers

    # Add buffer for rolling windows (e.g. 126 days)
    fetch_start = pd.to_datetime(start_date) - pd.Timedelta(days=200)
    fetch_start_str = fetch_start.strftime('%Y-%m-%d')
    ohlcv = self.yf.fetch_ohlcv(tickers, fetch_start_str, end_date)
    if ohlcv.empty:
      logger.error("No OHLCV data fetched.")
      return {}

    # Extract Close prices
    # Handle MultiIndex
    if isinstance(ohlcv.columns, pd.MultiIndex):
      closes = ohlcv.xs('Close', level=1, axis=1)
    else:
      # Should not happen with current provider logic but safety check
      closes = ohlcv['Close']

    # Fetch NAV/Benchmarks
    bench_map = self.universe.get_benchmark_map()
    navs = self.nav.get_nav_or_proxy(
      tickers, bench_map, fetch_start_str, end_date)

    # Fetch Credit/VIX
    credit = self.fred.get_credit_spreads(fetch_start_str)
    vix_df = self.yf.fetch_single_ticker("^VIX", fetch_start_str, end_date)
    vix = vix_df['Close'] if not vix_df.empty else pd.Series(dtype=float)

    # 2. Calculate Signals (Vectorized)
    logger.info("Calculating signals...")

    # Premium/Discount Z-Scores
    pd_z = calculate_premium_discount_signal(
        closes, navs,
        window=self.config.windows.get('premdisc', 126),
        threshold_z=self.config.thresholds.get('premdisc_z', 2.0),
        return_series=True
    )

    # Volume Z-Scores
    vol_z = calculate_volume_liquidity_signal(
        ohlcv,
        vol_window=self.config.windows.get('volume', 20),
        range_window=self.config.windows.get('range', 60),
        threshold_vol_z=self.config.thresholds.get('volume_z', 2.0),
        threshold_range_z=self.config.thresholds.get('range_z', 2.0),
        return_series=True
    )

    # Divergence Z-Scores
    # Need benchmark closes aligned
    # navs is actually benchmark closes in our proxy implementation
    div_z = calculate_divergence_signal(
        closes, navs,
        window=self.config.windows.get('divergence', 126),
        threshold_z=self.config.thresholds.get('divergence_z', 2.0),
        return_series=True
    )

    # Cross Asset Stress
    stress_series = calculate_cross_asset_signal(
        credit, vix,
        oas_jump_bps=self.config.thresholds.get('oas_jump_bps', 15),
        stress_z=self.config.thresholds.get('stress_z', 2.0),
        vix_z=self.config.thresholds.get('vix_z', 2.0),
        return_series=True
    )

    # 3. Composite Score
    # Score = w1*PD + w2*Div - w3*Vol - w4*Stress
    # Align all to closes index
    pd_z = pd_z.reindex(closes.index).astype(float).fillna(0.0)
    vol_z = vol_z.reindex(closes.index).astype(float).fillna(0.0)
    div_z = div_z.reindex(closes.index).astype(float).fillna(0.0)
    stress_series = stress_series.reindex(closes.index).astype(float).fillna(0.0)

    weights = self.config.weights

    # Broadcast stress series to dataframe shape
    stress_df = pd.DataFrame(index=closes.index, columns=closes.columns)
    for col in stress_df.columns:
      stress_df[col] = stress_series.values

    scores = (
        weights.get('premdisc', 0.35) * pd_z +
        weights.get('divergence', 0.30) * div_z -
        weights.get('volume', 0.25) * vol_z -
        weights.get('cross_asset', 0.10) * stress_df
    )

    # 4. Generate Target Positions
    # Action Map: <= -0.8 BUY, >= 0.8 SELL
    buy_thresh = self.config.composite_action_map.get('buy', -0.8)
    sell_thresh = self.config.composite_action_map.get('sell', 0.8)

    # Target Weights
    # Simple logic:
    # If Score <= BuyThresh -> Target = per_pos_cap (e.g. 8%)
    # If Score >= SellThresh -> Target = 0%
    # Else -> Hold (Keep previous target? Or 0 if not previously held?)
    # This "Hold" logic is tricky in pure vectorization without loop.
    #
    # Vectorized "Hold" usually requires state.
    # State-free approximation:
    # If Score <= BuyThresh -> 1
    # If Score >= SellThresh -> 0
    # Else -> NaN (Forward Fill)

    target_signals = pd.DataFrame(
      np.nan, index=scores.index, columns=scores.columns)
    target_signals[scores <= buy_thresh] = 1.0
    target_signals[scores >= sell_thresh] = 0.0

    # Forward fill to implement "Hold"
    target_signals = target_signals.ffill().fillna(0.0)

    # Apply Position Caps
    per_pos_cap = self.config.risk.get('per_pos_cap', 0.08)
    bucket_cap = self.config.risk.get('bucket_cap', 0.40)
    max_positions = self.config.risk.get('max_positions', 20)

    # Raw Weights
    raw_weights = target_signals * per_pos_cap

    # Enforce Bucket Cap (Total Exposure per day)
    daily_exposure = raw_weights.sum(axis=1)
    scale_factor = bucket_cap / daily_exposure
    scale_factor = scale_factor.clip(upper=1.0)  # Don't scale up, only down

    # Broadcast scaling
    final_weights = raw_weights.mul(scale_factor, axis=0)

    # 5. Calculate Returns
    # Shift weights by 1 day (Signal at Close T -> Trade at Open T+1 or Close T+1)
    # Config says: execution: {use_next_open: true}
    # If using Next Open:
    # PnL = Weight(T) * (Open(T+1) to Open(T+2)) ? No.
    # Standard: Weight(T) determines position held from T+1 to T+2.
    # Return(T+1) = (Price(T+1) - Price(T)) / Price(T)
    # Portfolio Return(T+1) = Sum(Weight(T) * AssetReturn(T+1))

    # If using Close-to-Close returns:
    asset_returns = closes.pct_change()

    # Lag weights by 1 day to simulate trading at Close of signal day (or Open of next day approx)
    # If we trade at Next Open, we capture (Open(T+1) -> Open(T+2))?
    # Simpler: Trade at Close(T+1). Signal at Close(T).
    # So Weight(T) applies to Return(T+1) = (Close(T+1)/Close(T) - 1).

    portfolio_returns = (final_weights.shift(1) * asset_returns).sum(axis=1)

    # Transaction Costs
    # Turnover = abs(Weight(T) - Weight(T-1))
    turnover = final_weights.diff().abs().sum(axis=1)
    cost_bps = self.config.costs.get(
      'tx_bps', 2) + self.config.costs.get('slippage_bps', 3)
    cost_penalty = turnover * (cost_bps / 10000)

    net_returns = portfolio_returns - cost_penalty

    # Trim to start date
    net_returns = net_returns.loc[start_date:]

    # Equity Curve
    equity_curve = (1 + net_returns).cumprod()

    # Metrics
    metrics = calculate_metrics(equity_curve)

    # Generate Trades List (for reporting)
    # Identify changes in position
    trades_list = []
    # This is slow to iterate, but fine for reporting
    # ... skipping detailed trade list generation for speed in V1,
    # or implement a quick diff check.

    return {
        "equity_curve": equity_curve,
        "metrics": metrics,
        "weights": final_weights,
        "scores": scores
    }
