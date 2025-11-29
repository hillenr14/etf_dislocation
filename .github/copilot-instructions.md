# Copilot / AI Agent Instructions

Purpose: Help an AI coding agent quickly become productive in this repo by explaining architecture, conventions, key entry points, config patterns, and common pitfalls.

**Big Picture**
- **What it is**: A production-style Python toolkit to monitor ETF dislocations (premium/discount, volume/liquidity stress, divergence) and to backtest mean-reversion trading rules.
- **Major components**:
  - `run.py`: CLI entry — supports `monitor`, `backtest`, `refresh-universe` subcommands. Use this to reproduce runs locally.
  - `config/`: YAML-driven configuration. Primary file is `config/default.yaml` (windows, thresholds, weights, risk, reporting, etc.).
  - `src/data_providers/`: adapters that fetch data (`yfinance`, `fred`, NAV proxies). Expect DataFrames, sometimes MultiIndex columns for OHLCV.
  - `src/signals/`: signal implementations. Each file exposes a `calculate_*_signal` function which either returns a dict of latest trigger details or a time-series DataFrame when `return_series=True`.
  - `src/model/`: scoring and rules (e.g., `scorer.py`, `rules_engine.py`). Scoring combines signal z-scores into composite score -> action mapping.
  - `src/backtest/engine.py`: vectorized backtester that fetches data, computes signals, creates target weights, simulates returns and returns `equity_curve`, `metrics`, `weights`, `scores`.

**Key Conventions & Patterns**
- Signals: signature pattern `calculate_xxx_signal(..., return_series=False)`. If `return_series=True` the function returns a `pd.DataFrame` of per-ticker z-scores aligned to price index; otherwise it returns a dict keyed by ticker with keys like `zscore`, `triggered`, `details`.
- Providers: `YFinanceProvider.fetch_ohlcv` returns a MultiIndex DataFrame `(ticker, [Open,High,Low,Close,Volume])` for >1 ticker. For single ticker this provider rebuilds a MultiIndex — watch for both shapes in upstream code (the repo already handles this in `run.py` and `engine.py`).
- Scores directionality: The codebase treats negative composite scores as BUY (mean reversion into discounts) and positive as SELL; volume and cross-asset stress are treated as amplifiers (subtracted) — see `src/model/scorer.py` for the exact sign logic.
- Config keys used heavily: `windows`, `thresholds`, `weights`, `composite_to_action` (mapping thresholds for buy/neutral/sell), `risk`, `execution.use_next_open`, `reporting.out_dir`.

**Important Implementation Details / Gotchas**
- The backtester uses rolling windows and therefore fetches ~200 days of extra history before `start` to allow clean z-score calculation. Be careful when adjusting windows in `config/default.yaml`.
- The engine implements a stateless, vectorized “Hold” via forward-fill of target signals (see `BacktestEngine.run` comments). Changing to a stateful implementation requires careful handling of position state and trade generation.
- `YFinanceProvider` can return empty DataFrames on network errors — callers log and abort if data is missing (check for `.empty`).
- NAVs may be proxies (see `src/data_providers/nav_provider.py` imported in `run.py`/`engine.py`). Some tickers will have NAV unavailable — signal functions return dict entries with `zscore=None` and `triggered=False` in that case.

**How to run & test**
- Install: `pip install -r requirements.txt`.
- Environment: set `FRED_API_KEY` for FRED calls.
- Typical runs:
  - Monitor (single date): `python run.py monitor --config config/default.yaml --as-of 2024-01-10`
  - Backtest: `python run.py backtest --config config/default.yaml --start 2015-01-01 --end 2023-12-31`
  - Update universe (placeholder): `python run.py refresh-universe --out tickers/tickers_vanguard_core.csv`
- Tests: `pytest -q` — existing unit tests are small and focused (e.g., `tests/test_scorer.py` demonstrates expected sign/weight logic).

**What to change carefully**
- Changing `weights`, `thresholds`, or `execution.use_next_open` changes P&L assumptions; verify by re-running backtests & checking `reports/equity_curve.csv`.
- Modifying signal function return shapes (dict vs DataFrame) requires updating both `run.py` (monitor mode) and `src/backtest/engine.py` (vectorized backtest) because they use both styles (`return_series=True` vs latest-dict).

**Files to inspect for implementation examples**
- Signal pattern: `src/signals/premium_discount.py` (z-score computation, `return_series` toggle).
- Provider pattern: `src/data_providers/yfinance_provider.py` (MultiIndex handling, `fetch_single_ticker`).
- Scoring: `src/model/scorer.py` (weight sign decisions; unit test in `tests/test_scorer.py`).
- Backtest orchestration: `src/backtest/engine.py` (fetch -> signals -> scores -> weights -> returns -> metrics).

If anything here is unclear or you'd like me to expand a section (for example: exact return schema for a signal, typical failure modes of providers, or a sample patch to make signals fully stateful), tell me which section to iterate on.
