import pytest
from src.model.scorer import Scorer
from src.config import Config

class MockConfig:
    weights = {'premdisc': 0.5, 'volume': 0.5, 'divergence': 0.0, 'cross_asset': 0.0}

def test_scorer():
    config = MockConfig()
    scorer = Scorer(config)
    
    pd_res = {'A': {'zscore': -2.0}} # Discount
    vol_res = {'A': {'zscore': 2.0}} # Panic Volume
    div_res = {}
    stress_res = {}
    
    # Score = 0.5 * (-2.0) - 0.5 * (2.0) = -1.0 - 1.0 = -2.0
    # Strong Buy
    
    scores = scorer.calculate_composite_score(pd_res, vol_res, div_res, stress_res)
    assert scores['A'] == -2.0
