import pandas as pd
import logging
from typing import List, Dict, Optional
from .config import Config

logger = logging.getLogger(__name__)

class Universe:
    def __init__(self, config: Config, override_file: Optional[str] = None):
        self.config = config
        self.override_file = override_file
        self.tickers_df = self._load_universe()
        self.valid_tickers = self._apply_filters()

    def _load_universe(self) -> pd.DataFrame:
        if self.override_file:
            path = self.override_file
            logger.info(f"Loading universe from override file: {path}")
        else:
            profile = self.config.universe_profile
            files = self.config.universe_files
            path = files.get(profile)
            if not path:
                raise ValueError(f"Universe profile '{profile}' not found in config.")
            logger.info(f"Loading universe profile '{profile}' from: {path}")

        try:
            df = pd.read_csv(path)
            # Normalize column names
            df.columns = [c.strip().lower() for c in df.columns]
            if 'ticker' not in df.columns:
                raise ValueError("Universe CSV must contain a 'ticker' column.")
            return df
        except Exception as e:
            logger.error(f"Failed to load universe file: {e}")
            raise

    def _apply_filters(self) -> List[str]:
        df = self.tickers_df.copy()
        initial_count = len(df)
        
        filters = self.config.liquidity_filters
        exclude_patterns = filters.get('exclude_patterns', [])
        allowlist = filters.get('allowlist', [])

        # 1. Pattern Exclusion
        if exclude_patterns:
            pattern = '|'.join(exclude_patterns)
            # Ensure we don't filter out allowlisted items
            mask_exclude = df['ticker'].str.contains(pattern, regex=True)
            mask_allow = df['ticker'].isin(allowlist)
            df = df[~mask_exclude | mask_allow]

        # Note: Liquidity (ADV) and Age filters usually require data fetching first.
        # For this 'static' universe loader, we might only filter on metadata if available.
        # Real filtering happens after data ingestion in the main pipeline.
        # However, if we had metadata in the CSV, we could filter here.
        
        # For now, we return the list of tickers that passed static checks.
        final_count = len(df)
        logger.info(f"Universe loaded: {initial_count} tickers -> {final_count} after static filters.")
        
        return df['ticker'].tolist()

    def get_benchmark_map(self) -> Dict[str, str]:
        """Returns a dictionary mapping ticker -> benchmark_proxy"""
        if 'benchmark_proxy' in self.tickers_df.columns:
            return pd.Series(
                self.tickers_df.benchmark_proxy.values, 
                index=self.tickers_df.ticker
            ).to_dict()
        return {}
