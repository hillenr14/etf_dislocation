import argparse
import logging
import pandas as pd
import os
from datetime import datetime
from src.config import load_config
from src.universe import Universe
from src.data_providers.yfinance_provider import YFinanceProvider
from src.data_providers.fred_provider import FredProvider
from src.data_providers.nav_provider import NavProvider
from src.signals.premium_discount import calculate_premium_discount_signal
from src.signals.volume_liquidity import calculate_volume_liquidity_signal
from src.signals.divergence import calculate_divergence_signal
from src.signals.cross_asset_stress import calculate_cross_asset_signal
from src.model.scorer import Scorer
from src.model.rules_engine import RulesEngine
from src.reporting.formatter import format_monitor_output
from src.backtest.engine import BacktestEngine
from src.reporting.tearsheet import TearsheetGenerator
from src.utils.dates import get_today_str, get_lookback_date

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_monitor(args):
  config = load_config(args.config)

  # Override profile if provided
  if args.profile:
    # Hacky override of config object internal data
    config._data['universe_profile'] = args.profile

  universe = Universe(config)
  tickers = universe.valid_tickers
  logger.info(f"Monitoring {len(tickers)} tickers...")

  # Setup Providers
  yf_provider = YFinanceProvider()
  fred = FredProvider()
  nav = NavProvider(yf_provider)

  # Dates
  end_date = args.as_of or get_today_str()
  # Need enough lookback for 126d windows + buffer
  start_date = get_lookback_date(end_date, 200)

  # Fetch Data
  ohlcv = yf_provider.fetch_ohlcv(tickers, start_date, end_date)
  if ohlcv.empty:
    logger.error("No data fetched.")
    return

  # Extract Closes
  if isinstance(ohlcv.columns, pd.MultiIndex):
    closes = ohlcv.xs('Close', level=1, axis=1)
  else:
    closes = ohlcv['Close']

  bench_map = universe.get_benchmark_map()
  navs = nav.get_nav_or_proxy(tickers, bench_map, start_date, end_date)

  credit = fred.get_credit_spreads(start_date)
  vix_df = yf_provider.fetch_single_ticker("^VIX", start_date, end_date)
  vix = vix_df['Close'] if not vix_df.empty else pd.Series(dtype=float)

  # Calculate Signals
  pd_res = calculate_premium_discount_signal(
      closes, navs,
      window=config.windows.get('premdisc', 126),
      threshold_z=config.thresholds.get('premdisc_z', 2.0)
  )

  vol_res = calculate_volume_liquidity_signal(
      ohlcv,
      vol_window=config.windows.get('volume', 20),
      range_window=config.windows.get('range', 60),
      threshold_vol_z=config.thresholds.get('volume_z', 2.0),
      threshold_range_z=config.thresholds.get('range_z', 2.0)
  )

  div_res = calculate_divergence_signal(
      closes, navs,  # navs are benchmarks
      window=config.windows.get('divergence', 126),
      threshold_z=config.thresholds.get('divergence_z', 2.0)
  )

  stress_res = calculate_cross_asset_signal(
      credit, vix,
      oas_jump_bps=config.thresholds.get('oas_jump_bps', 15),
      stress_z=config.thresholds.get('stress_z', 2.0),
      vix_z=config.thresholds.get('vix_z', 2.0)
  )

  # Scoring
  scorer = Scorer(config)
  scores = scorer.calculate_composite_score(
    pd_res, vol_res, div_res, stress_res)

  # Rules
  rules = RulesEngine(config)

  # Format Output
  all_signals = {
      'premdisc': pd_res,
      'volume': vol_res,
      'divergence': div_res,
      'cross_asset': stress_res
  }

  df = format_monitor_output(scores, all_signals, rules)

  # Save
  out_dir = config.reporting.get('out_dir', 'reports')
  if not os.path.exists(out_dir):
    os.makedirs(out_dir)

  out_file = os.path.join(out_dir, f"recs_{end_date}.csv")
  df.to_csv(out_file, index=False)
  logger.info(f"Report saved to {out_file}")

  # Print Top Opportunities
  print("\nTop Opportunities:")
  print(df[df['action'] != 'HOLD'].head(10).to_string(index=False))


def run_backtest(args):
  config = load_config(args.config)
  engine = BacktestEngine(config)

  results = engine.run(args.start, args.end)

  if not results:
    logger.error("Backtest failed.")
    return

  # Reporting
  out_dir = config.reporting.get('out_dir', 'reports')
  gen = TearsheetGenerator(out_dir)
  gen.generate(results['equity_curve'], results['metrics'])

  # Save Trades/Equity
  results['equity_curve'].to_csv(os.path.join(out_dir, "equity_curve.csv"))

  print("\nBacktest Complete.")
  print("Metrics:")
  for k, v in results['metrics'].items():
    print(f"{k}: {v}")


def run_refresh_universe(args):
  logger.info("Refreshing universe... (Not implemented yet, using static CSVs)")
  # Placeholder for wikipedia scrape or similar
  pass


def main():
  parser = argparse.ArgumentParser(description="ETF Dislocation Monitor")
  subparsers = parser.add_subparsers(dest='command', help='Command to run')

  # Monitor Command
  monitor_parser = subparsers.add_parser('monitor', help='Run daily monitor')
  monitor_parser.add_argument(
    '--config', default='config/default.yaml', help='Path to config file')
  monitor_parser.add_argument(
    '--as-of', help='Date to run analysis for (YYYY-MM-DD)')
  monitor_parser.add_argument('--profile', help='Override universe profile')

  # Backtest Command
  backtest_parser = subparsers.add_parser('backtest', help='Run backtest')
  backtest_parser.add_argument(
    '--config', default='config/default.yaml', help='Path to config file')
  backtest_parser.add_argument(
    '--start', required=True, help='Start date (YYYY-MM-DD)')
  backtest_parser.add_argument(
    '--end', required=True, help='End date (YYYY-MM-DD)')

  # Refresh Universe Command
  refresh_parser = subparsers.add_parser(
    'refresh-universe', help='Refresh universe list')
  refresh_parser.add_argument('--out', required=True, help='Output CSV path')

  args = parser.parse_args()

  if args.command == 'monitor':
    run_monitor(args)
  elif args.command == 'backtest':
    run_backtest(args)
  elif args.command == 'refresh-universe':
    run_refresh_universe(args)
  else:
    parser.print_help()


if __name__ == "__main__":
  main()
