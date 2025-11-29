import os
import pandas as pd
from fredapi import Fred
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)
FRED_API_KEY = "32d1fa37c639637c4fbf10df162df251"


class FredProvider:
  def __init__(self, api_key: Optional[str] = FRED_API_KEY, cache_dir: str = "data/cache"):
    self.api_key = api_key or os.environ.get('FRED_API_KEY')
    self.cache_dir = cache_dir
    if not os.path.exists(self.cache_dir):
      os.makedirs(self.cache_dir)

    if not self.api_key:
      logger.warning(
        "FRED_API_KEY not found. Credit spread signals may be disabled.")
      self.client = None
    else:
      # The fredapi library does not accept a session object in its constructor.
      self.client = Fred(api_key=self.api_key)

  def _get_cache_path(self, series_id: str) -> str:
    return os.path.join(self.cache_dir, f"FRED_{series_id}.parquet")

  def _is_cache_valid(self, cache_path: str) -> bool:
    if not os.path.exists(cache_path):
      return False
    
    # Check if file is less than 1 day old
    mtime = os.path.getmtime(cache_path)
    file_age = time.time() - mtime
    return file_age < 86400  # 24 hours in seconds

  def fetch_series(self, series_id: str, start_date: str, end_date: Optional[str] = None) -> pd.Series:
    cache_path = self._get_cache_path(series_id)
    
    # Check cache
    if self._is_cache_valid(cache_path):
      try:
        df = pd.read_parquet(cache_path)
        series = df['value']
        # Filter by date
        if start_date:
          series = series[series.index >= pd.to_datetime(start_date)]
        if end_date:
          series = series[series.index <= pd.to_datetime(end_date)]
        return series
      except Exception as e:
        logger.error(f"Error reading cache for {series_id}: {e}")

    # Fetch from remote if cache miss or invalid
    if not self.client:
      return pd.Series(dtype=float)

    try:
      logger.info(f"Fetching FRED series: {series_id} (cache miss/stale)")
      # Fetch full history for caching if possible, or at least from a long time ago
      # FRED API doesn't have a "max" but we can use a very early start date
      fetch_start = "1990-01-01" 
      series = self.client.get_series(
        series_id, observation_start=fetch_start)
      
      # Save to cache
      try:
        df = series.to_frame(name='value')
        df.to_parquet(cache_path)
      except Exception as e:
        logger.error(f"Error caching {series_id}: {e}")

      # Filter for return
      if start_date:
        series = series[series.index >= pd.to_datetime(start_date)]
      if end_date:
        series = series[series.index <= pd.to_datetime(end_date)]
      
      return series
    except Exception as e:
      logger.error(f"Error fetching FRED series {series_id}: {e}")
      return pd.Series(dtype=float)

  def get_credit_spreads(self, start_date: str) -> pd.DataFrame:
    """
    Fetches IG OAS (BAMLC0A0CM) and HY OAS (BAMLH0A0HYM2).
    Returns DataFrame with columns ['IG_OAS', 'HY_OAS'].
    """
    ig = self.fetch_series("BAMLC0A0CM", start_date)
    hy = self.fetch_series("BAMLH0A0HYM2", start_date)

    df = pd.DataFrame({'IG_OAS': ig, 'HY_OAS': hy})
    # Forward fill missing days (weekends/holidays) as spreads don't change
    df = df.ffill()
    return df
