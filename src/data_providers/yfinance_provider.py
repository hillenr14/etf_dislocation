import yfinance as yf
import pandas as pd
import logging
import os
import time
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)


class YFinanceProvider:
  def __init__(self, cache_dir: str = "data/cache"):
    self.cache_dir = cache_dir
    if not os.path.exists(self.cache_dir):
      os.makedirs(self.cache_dir)

  def _get_cache_path(self, ticker: str) -> str:
    # Sanitize ticker for filename
    safe_ticker = ticker.replace("^", "hat_").replace("=", "_eq_")
    return os.path.join(self.cache_dir, f"{safe_ticker}.parquet")

  def _is_cache_valid(self, cache_path: str) -> bool:
    if not os.path.exists(cache_path):
      return False
    
    # Check if file is less than 1 day old
    mtime = os.path.getmtime(cache_path)
    file_age = time.time() - mtime
    return file_age < 86400  # 24 hours in seconds

  def fetch_ohlcv(self, tickers: List[str], start_date: str, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Fetches OHLCV data for a list of tickers with caching.
    Returns a MultiIndex DataFrame (Ticker, OHLCV columns).
    """
    if not tickers:
      return pd.DataFrame()

    logger.info(
      f"Fetching OHLCV for {len(tickers)} tickers from {start_date} to {end_date}...")

    # Identify which tickers need downloading
    to_download = []
    for ticker in tickers:
      cache_path = self._get_cache_path(ticker)
      if not self._is_cache_valid(cache_path):
        to_download.append(ticker)

    # Download missing/stale tickers
    if to_download:
      logger.info(f"Downloading {len(to_download)} tickers (cache miss/stale)...")
      # yfinance expects space-separated string for multiple tickers
      tickers_str = " ".join(to_download)
      try:
        # Fetch full history for caching
        df_download = yf.download(tickers_str, period="max",
                         group_by='ticker', auto_adjust=True, progress=False)
        
        # Save to cache
        if len(to_download) == 1:
          # Single ticker, df columns are just OHLCV
          ticker = to_download[0]
          cache_path = self._get_cache_path(ticker)
          df_download.to_parquet(cache_path)
        else:
          # MultiIndex columns: (Ticker, OHLCV)
          # Iterate and save each
          for ticker in to_download:
            try:
              # Extract data for this ticker
              # xs might fail if ticker not found in download
              if ticker in df_download.columns.get_level_values(0):
                ticker_df = df_download.xs(ticker, level=0, axis=1)
                cache_path = self._get_cache_path(ticker)
                ticker_df.to_parquet(cache_path)
              else:
                logger.warning(f"Ticker {ticker} not found in downloaded data.")
            except Exception as e:
              logger.error(f"Error caching {ticker}: {e}")
      except Exception as e:
        logger.error(f"Error downloading from yfinance: {e}")

    # Load all from cache and combine
    combined_data = {}
    for ticker in tickers:
      cache_path = self._get_cache_path(ticker)
      if os.path.exists(cache_path):
        try:
          df = pd.read_parquet(cache_path)
          
          # If df has MultiIndex columns (Ticker, Price), drop Ticker level
          # This happens because we saved yfinance output which might be MultiIndex
          if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(0, axis=1)

          # Filter by date
          if start_date:
            df = df[df.index >= pd.to_datetime(start_date)]
          if end_date:
            df = df[df.index <= pd.to_datetime(end_date)]
          combined_data[ticker] = df
        except Exception as e:
          logger.error(f"Error reading cache for {ticker}: {e}")
      else:
        logger.warning(f"No data found for {ticker} (download failed?)")

    if not combined_data:
      return pd.DataFrame()

    # Combine into MultiIndex DataFrame
    # pd.concat with keys creates the MultiIndex (Ticker, OHLCV)
    result = pd.concat(combined_data.values(), axis=1, keys=combined_data.keys())
    
    # Ensure columns are named correctly if they aren't already
    # The concat keys puts Ticker at level 0, OHLCV at level 1.
    
    return result

  def fetch_single_ticker(self, ticker: str, start_date: str, end_date: Optional[str] = None) -> pd.DataFrame:
    """Fetches data for a single ticker with caching."""
    # Reuse fetch_ohlcv logic but return single level DF
    df = self.fetch_ohlcv([ticker], start_date, end_date)
    if df.empty:
      return df
      
    # If fetch_ohlcv returns MultiIndex, strip it
    if isinstance(df.columns, pd.MultiIndex):
      return df.xs(ticker, level=0, axis=1)
    return df
