import pandas as pd
import numpy as np
from typing import Dict, Any, Union

def calculate_divergence_signal(
    prices: pd.DataFrame,
    benchmark_prices: pd.DataFrame,
    window: int = 126,
    threshold_z: float = 2.0,
    return_series: bool = False
) -> Union[Dict[str, Any], pd.DataFrame]:
    """
    Calculates Relative Divergence vs Benchmark.
    
    Args:
        prices: DataFrame of ETF Close prices.
        benchmark_prices: DataFrame of Benchmark Close prices (aligned columns).
        window: Rolling window for Z-score.
        return_series: If True, returns DataFrame of Z-scores.
        
    Returns:
        Dictionary keyed by ticker, or DataFrame if return_series=True.
    """
    results = {}
    
    # Align indices
    common_index = prices.index.intersection(benchmark_prices.index)
    prices = prices.loc[common_index]
    benchmark_prices = benchmark_prices.loc[common_index]
    
    z_scores_df = pd.DataFrame(index=prices.index)
    
    # Calculate Spread/Ratio
    # We use Ratio = Price / Benchmark
    # Then Z-score of that ratio
    
    for ticker in prices.columns:
        if ticker not in benchmark_prices.columns or pd.isna(benchmark_prices[ticker].iloc[-1]):
            results[ticker] = {
                "name": "Divergence",
                "value": None,
                "zscore": None,
                "triggered": False,
                "details": "Benchmark data unavailable"
            }
            z_scores_df[ticker] = pd.NA
            continue
            
        price = prices[ticker]
        bench = benchmark_prices[ticker]
        
        # Avoid division by zero
        bench = bench.replace(0, np.nan)
        
        ratio = price / bench
        
        # Rolling Z-Score of the ratio
        rolling_mean = ratio.rolling(window=window).mean()
        rolling_std = ratio.rolling(window=window).std()
        z_scores = (ratio - rolling_mean) / rolling_std
        
        z_scores_df[ticker] = z_scores
        
        curr_z = z_scores.iloc[-1]
        
        triggered = False
        if pd.notna(curr_z) and abs(curr_z) >= threshold_z:
            triggered = True
            
        results[ticker] = {
            "name": "Divergence",
            "value": float(ratio.iloc[-1]) if pd.notna(ratio.iloc[-1]) else None,
            "zscore": float(curr_z) if pd.notna(curr_z) else None,
            "triggered": triggered,
            "details": f"Div Z: {curr_z:.2f}" if pd.notna(curr_z) else "Insufficient data"
        }
        
    if return_series:
        return z_scores_df
        
    return results
