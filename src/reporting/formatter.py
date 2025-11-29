import pandas as pd
from typing import Dict, Any, List

def format_monitor_output(
    scores: Dict[str, float],
    signals: Dict[str, Dict[str, Any]],
    rules_engine: Any
) -> pd.DataFrame:
    """
    Formats the daily monitoring output into a DataFrame.
    """
    rows = []
    
    for ticker, score in scores.items():
        action = rules_engine.get_action(score)
        rationale = rules_engine.generate_rationale(ticker, action, score, signals)
        
        # Collect triggered signals
        triggered = []
        for sig_name, sig_data in signals.items():
            # Handle Global vs Ticker
            if sig_name == 'cross_asset' and 'GLOBAL' in sig_data:
                data = sig_data['GLOBAL']
            else:
                data = sig_data.get(ticker, {})
                
            if data.get('triggered'):
                triggered.append(sig_name)
                
        rows.append({
            "ticker": ticker,
            "action": action,
            "score": round(score, 2),
            "signals_fired": ", ".join(triggered),
            "rationale": rationale
        })
        
    df = pd.DataFrame(rows)
    # Sort by Score (ascending for BUYs, descending for SELLs)
    df = df.sort_values('score')
    return df
