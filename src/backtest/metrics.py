import pandas as pd
import numpy as np
from typing import Dict, Any

def calculate_metrics(equity_curve: pd.Series, trades: pd.DataFrame = None) -> Dict[str, Any]:
    """
    Calculates performance metrics for an equity curve.
    
    Args:
        equity_curve: Series of portfolio value over time.
        trades: Optional DataFrame of trades for turnover/hit-rate stats.
        
    Returns:
        Dictionary of metrics.
    """
    if equity_curve.empty:
        return {}
    
    # Daily Returns
    returns = equity_curve.pct_change().dropna()
    
    if returns.empty:
        return {}
    
    # Total Return
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    
    # CAGR
    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    years = days / 365.25
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    
    # Volatility (Annualized)
    vol = returns.std() * np.sqrt(252)
    
    # Sharpe Ratio (Risk Free Rate = 0 for simplicity or pass it in)
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0
    
    # Sortino Ratio (Downside deviation)
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() * np.sqrt(252)
    sortino = (returns.mean() / downside_std) * np.sqrt(252) if downside_std != 0 else 0
    
    # Max Drawdown
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    max_dd = drawdown.min()
    
    # Calmar Ratio
    calmar = cagr / abs(max_dd) if max_dd != 0 else 0
    
    metrics = {
        "Total Return": total_return,
        "CAGR": cagr,
        "Volatility": vol,
        "Sharpe": sharpe,
        "Sortino": sortino,
        "Max Drawdown": max_dd,
        "Calmar": calmar
    }
    
    if trades is not None and not trades.empty:
        # Hit Rate
        winning_trades = trades[trades['pnl'] > 0]
        hit_rate = len(winning_trades) / len(trades)
        
        # Avg Gain / Avg Loss
        avg_gain = winning_trades['pnl'].mean()
        losing_trades = trades[trades['pnl'] <= 0]
        avg_loss = losing_trades['pnl'].mean()
        
        metrics.update({
            "Trades": len(trades),
            "Hit Rate": hit_rate,
            "Avg Gain": avg_gain,
            "Avg Loss": avg_loss
        })
        
    return metrics
