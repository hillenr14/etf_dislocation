import pandas as pd
import numpy as np
from typing import Dict, Any, Union

def calculate_premium_discount_signal(
    prices: pd.DataFrame, 
    navs: pd.DataFrame, 
    window: int = 126, 
    threshold_z: float = 2.0,
    return_series: bool = False
) -> Union[Dict[str, Any], pd.DataFrame]:
    """
    Calculates Premium/Discount signal.
    
    Args:
        prices: DataFrame of ETF Close prices.
        navs: DataFrame of ETF NAVs (or proxy benchmarks).
        window: Rolling window for Z-score.
        threshold_z: Z-score threshold for triggering.
        return_series: If True, returns the DataFrame of Z-scores.
        
    Returns:
        Dictionary keyed by ticker containing signal details (latest),
        OR DataFrame of Z-scores (if return_series=True).
    """
    results = {}
    
    # Align indices
    common_index = prices.index.intersection(navs.index)
    prices = prices.loc[common_index]
    navs = navs.loc[common_index]
    
    # Calculate Premium/Discount %
    prem_disc = (prices - navs) / navs
    
    # Rolling Z-Score
    rolling_mean = prem_disc.rolling(window=window).mean()
    rolling_std = prem_disc.rolling(window=window).std()
    z_scores = (prem_disc - rolling_mean) / rolling_std
    
    if return_series:
        return z_scores
    
    # Get latest values
    latest_date = prices.index[-1]
    
    for ticker in prices.columns:
        if ticker not in navs.columns or pd.isna(navs[ticker].iloc[-1]):
            results[ticker] = {
                "name": "Premium/Discount",
                "value": None,
                "zscore": None,
                "triggered": False,
                "details": "NAV data unavailable"
            }
            continue
            
        val = prem_disc[ticker].iloc[-1]
        z = z_scores[ticker].iloc[-1]
        
        triggered = False
        if pd.notna(z) and abs(z) >= threshold_z:
            triggered = True
            
        results[ticker] = {
            "name": "Premium/Discount",
            "value": float(val) if pd.notna(val) else None,
            "zscore": float(z) if pd.notna(z) else None,
            "triggered": triggered,
            "details": f"Prem/Disc: {val:.2%}, Z: {z:.2f}" if pd.notna(val) else "Insufficient data"
        }
        
    return results
