import pandas as pd
import logging
from typing import Dict, Optional
from .yfinance_provider import YFinanceProvider

logger = logging.getLogger(__name__)

class NavProvider:
    def __init__(self, yf_provider: YFinanceProvider):
        self.yf = yf_provider

    def get_nav_or_proxy(self, tickers: list, benchmark_map: Dict[str, str], start_date: str, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Ideally, we would fetch official NAVs here.
        Since free official NAV APIs are scarce, we will primarily use the 'benchmark_proxy' 
        to estimate fair value or simply return the Close price if we treat Close as the best proxy for now,
        OR we can fetch the benchmark index itself to calculate divergence.
        
        For the 'Premium/Discount' signal specifically:
        - Real NAV is needed. 
        - Without real NAV, we can't compute true Prem/Disc.
        - We can compute 'Relative Performance vs Benchmark' which is the 'Divergence' signal.
        
        If the user wants a 'NAV Proxy' (e.g. estimating ETF NAV based on basket), that's complex without basket data.
        
        Strategy:
        1. Try to fetch official NAV (Not implemented for free sources easily).
        2. Fallback: Return None/Empty for NAV, so the Prem/Disc signal knows to skip.
        
        However, the prompt asks for: "(b) Fallback proxy NAV using appropriate benchmark".
        This implies: ProxyNAV(t) = Price(t0) * (Benchmark(t) / Benchmark(t0))
        This assumes the ETF tracked the benchmark perfectly since t0. This is prone to drift.
        
        Better approach for 'Dislocation':
        We will return the Benchmark Close prices. The signal calculator will then compare ETF Price vs Benchmark Price
        to find divergence.
        
        So this function will return a DataFrame of Benchmark Closes for the given tickers.
        """
        
        # Identify unique benchmarks
        unique_benchmarks = list(set(benchmark_map.values()))
        unique_benchmarks = [b for b in unique_benchmarks if b and isinstance(b, str)]
        
        if not unique_benchmarks:
            logger.warning("No benchmarks defined. NAV/Proxy data will be empty.")
            return pd.DataFrame()

        logger.info(f"Fetching benchmark data for proxies: {unique_benchmarks}")
        bench_data = self.yf.fetch_ohlcv(unique_benchmarks, start_date, end_date)
        
        # Extract Close prices
        # bench_data is MultiIndex [Ticker, (Open, High, Low, Close, Volume)]
        # We want a DataFrame where columns are Tickers and values are Close prices
        
        nav_proxy_df = pd.DataFrame(index=bench_data.index)
        
        for ticker in tickers:
            benchmark = benchmark_map.get(ticker)
            if benchmark and benchmark in bench_data.columns.levels[0]:
                # Get benchmark close
                # Handle case where yf.download might return different casing or structure
                try:
                    proxy_series = bench_data[benchmark]['Close']
                    nav_proxy_df[ticker] = proxy_series
                except KeyError:
                    logger.warning(f"Could not find Close data for benchmark {benchmark}")
            else:
                # No benchmark or data missing
                nav_proxy_df[ticker] = pd.NA
                
        return nav_proxy_df
