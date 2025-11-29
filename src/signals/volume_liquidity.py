import pandas as pd
import numpy as np
from typing import Dict, Any, Union

def calculate_volume_liquidity_signal(
    ohlcv: pd.DataFrame,
    vol_window: int = 20,
    range_window: int = 60,
    threshold_vol_z: float = 2.0,
    threshold_range_z: float = 2.0,
    return_series: bool = False
) -> Union[Dict[str, Any], pd.DataFrame]:
    """
    Calculates Volume & Liquidity Stress signal.
    
    Args:
        ohlcv: MultiIndex DataFrame (Ticker -> OHLCV).
        vol_window: Rolling window for Volume Z-score.
        range_window: Rolling window for Range Z-score.
        return_series: If True, returns DataFrame of Volume Z-scores (primary).
        
    Returns:
        Dictionary keyed by ticker containing signal details,
        OR DataFrame of Volume Z-scores (if return_series=True).
    """
    results = {}
    
    # Check if we have MultiIndex columns or just single level (if single ticker)
    # The provider ensures MultiIndex [Ticker, (Open, High, Low, Close, Volume)]
    
    tickers = ohlcv.columns.levels[0]
    
    vol_z_df = pd.DataFrame(index=ohlcv.index)
    
    for ticker in tickers:
        try:
            df = ohlcv[ticker]
            if df.empty:
                continue
                
            # Volume Z-Score
            volume = df['Volume']
            vol_mean = volume.rolling(window=vol_window).mean()
            vol_std = volume.rolling(window=vol_window).std()
            vol_z = (volume - vol_mean) / vol_std
            
            vol_z_df[ticker] = vol_z
            
            # Range Proxy Z-Score: (High - Low) / Close
            # Using Close from the same row.
            high = df['High']
            low = df['Low']
            close = df['Close']
            
            # Avoid division by zero
            close = close.replace(0, np.nan)
            
            range_proxy = (high - low) / close
            range_mean = range_proxy.rolling(window=range_window).mean()
            range_std = range_proxy.rolling(window=range_window).std()
            range_z = (range_proxy - range_mean) / range_std
            
            # Latest values
            curr_vol_z = vol_z.iloc[-1]
            curr_range_z = range_z.iloc[-1]
            
            triggered = False
            details = []
            
            if pd.notna(curr_vol_z) and curr_vol_z >= threshold_vol_z:
                triggered = True
                details.append(f"Vol Z: {curr_vol_z:.2f}")
                
            if pd.notna(curr_range_z) and curr_range_z >= threshold_range_z:
                triggered = True
                details.append(f"Range Z: {curr_range_z:.2f}")
                
            results[ticker] = {
                "name": "Volume/Liquidity",
                "value": float(curr_vol_z) if pd.notna(curr_vol_z) else None, # Primary value proxy
                "zscore": float(curr_vol_z) if pd.notna(curr_vol_z) else None,
                "triggered": triggered,
                "details": ", ".join(details) if details else "Normal"
            }
            
        except KeyError:
            logger.warning(f"Missing data for {ticker} in Volume signal")
            results[ticker] = {
                "name": "Volume/Liquidity",
                "value": None,
                "zscore": None,
                "triggered": False,
                "details": "Data Error"
            }

    if return_series:
        return vol_z_df
        
    return results
