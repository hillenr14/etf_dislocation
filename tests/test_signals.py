import pytest
import pandas as pd
import numpy as np
from src.signals.premium_discount import calculate_premium_discount_signal
from src.signals.volume_liquidity import calculate_volume_liquidity_signal
from src.signals.divergence import calculate_divergence_signal

@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2023-01-01', periods=100)
    prices = pd.DataFrame({'A': np.random.randn(100).cumsum() + 100}, index=dates)
    navs = prices.copy()
    # Create a discount
    navs['A'] = prices['A'] * 1.05 # NAV higher than price -> Discount
    
    ohlcv = pd.DataFrame({
        'Open': prices['A'],
        'High': prices['A'] + 1,
        'Low': prices['A'] - 1,
        'Close': prices['A'],
        'Volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    # MultiIndex for OHLCV
    ohlcv.columns = pd.MultiIndex.from_product([['A'], ohlcv.columns])
    
    return prices, navs, ohlcv

def test_premium_discount_signal(sample_data):
    prices, navs, _ = sample_data
    
    # Test Dict Output
    res = calculate_premium_discount_signal(prices, navs, window=10, threshold_z=1.0)
    assert 'A' in res
    assert res['A']['name'] == 'Premium/Discount'
    
    # Test Series Output
    series = calculate_premium_discount_signal(prices, navs, window=10, return_series=True)
    assert isinstance(series, pd.DataFrame)
    assert 'A' in series.columns
    assert len(series) == 100

def test_volume_signal(sample_data):
    _, _, ohlcv = sample_data
    
    res = calculate_volume_liquidity_signal(ohlcv, vol_window=10, range_window=10, threshold_vol_z=1.0)
    assert 'A' in res
    assert res['A']['name'] == 'Volume/Liquidity'
    
    series = calculate_volume_liquidity_signal(ohlcv, vol_window=10, return_series=True)
    assert isinstance(series, pd.DataFrame)

def test_divergence_signal(sample_data):
    prices, _, _ = sample_data
    benchmark = prices.copy() * 1.1 # Benchmark higher
    
    res = calculate_divergence_signal(prices, benchmark, window=10, threshold_z=1.0)
    assert 'A' in res
    assert res['A']['name'] == 'Divergence'
