# ETF Dislocation Monitor & Backtester

A production-quality Python application to monitor ETF dislocations (premium/discount, liquidity, divergence) and backtest trading strategies based on these signals.

## Features

- **Dislocation Signals**:
  - Premium/Discount to NAV (or proxy).
  - Volume & Liquidity Stress.
  - Relative Divergence vs Benchmark/Peers.
  - Cross-Asset Stress Overlay (VIX, Credit Spreads).
- **Vectorized Backtester**:
  - Fast, pandas-based engine.
  - Metrics: CAGR, Sharpe, Sortino, Max Drawdown, Turnover, etc.
- **Configurable**:
  - YAML-based configuration.
  - Custom universe support via CSV.
- **Reporting**:
  - Daily monitoring reports (CSV).
  - Backtest tearsheets (Markdown + Charts).

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: Create a `requirements.txt` with `pandas`, `numpy`, `yfinance`, `fredapi`, `matplotlib`, `seaborn`, `pyyaml`, `scipy`)*

2.  **Environment Variables**:
    - `FRED_API_KEY`: Required for credit spread data (get one from [FRED](https://fred.stlouisfed.org/docs/api/api_key.html)).

## Usage

### Monitoring (Daily Run)

```bash
python run.py monitor --config config/default.yaml
```

### Backtesting

```bash
python run.py backtest --config config/default.yaml --start 2015-01-01 --end 2023-12-31
```

### Refresh Universe

```bash
python run.py refresh-universe --out tickers/tickers_vanguard_core.csv
```

## Configuration

See `config/default.yaml` for all available options. You can override the universe profile or file path there.

## Disclaimer

See `DISCLAIMER.md`.
