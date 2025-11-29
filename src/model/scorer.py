import pandas as pd
import numpy as np
from typing import Dict, Any, List
from ..config import Config

class Scorer:
    def __init__(self, config: Config):
        self.config = config
        self.weights = config.weights
        
    def calculate_composite_score(
        self, 
        prem_disc_results: Dict[str, Any],
        volume_results: Dict[str, Any],
        divergence_results: Dict[str, Any],
        cross_asset_result: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculates composite score for each ticker.
        Score = w1*PremDiscZ + w2*VolZ + w3*DivZ + w4*StressZ
        
        Note: The directionality matters.
        - Premium/Discount: 
            - Large Positive Z (Premium) -> Sell signal (Score should be positive)
            - Large Negative Z (Discount) -> Buy signal (Score should be negative)
            - So we add Z directly.
            
        - Volume/Liquidity:
            - High Volume/Stress -> Usually implies panic/dislocation.
            - If we want to BUY dislocations, we want to identify stress.
            - However, the composite score mapping says:
                score <= -T_buy -> BUY
                score >= T_sell -> SELL
            - If Volume Stress is high, does it mean we should BUY or SELL?
            - Usually, high volume/panic = BUY opportunity (contrarian).
            - So High Volume Z should contribute negatively to the score (towards BUY).
            - BUT, if we are holding, high volume might mean SELL?
            - Let's assume "Dislocation" strategy is Mean Reversion.
            - Discount (Neg Z) -> Buy.
            - Panic Volume (Pos Z) -> Buy.
            - So Volume Z should be subtracted? Or we treat it as a magnitude that amplifies the Prem/Disc signal?
            
            - Let's look at the weights: {premdisc:0.35, volume:0.25, divergence:0.30, cross_asset:0.10}
            - If we simply sum weighted Z-scores:
                - PremDisc Z = -3.0 (Discount) -> Contribution -1.05
                - Volume Z = +3.0 (Panic) -> If we add, it becomes +0.75. Net -0.3. 
                - This cancels out! That's bad. We want Panic to reinforce Discount.
                
            - Improved Logic:
                - The core directional signal is Premium/Discount and Divergence.
                - Volume and Cross-Asset are "Stress Amplifiers".
                - If Direction is BUY (Discount), Stress should make it a STRONGER BUY (more negative).
                - If Direction is SELL (Premium), Stress might make it a STRONGER SELL? Or maybe we don't sell into panic?
                
            - Simpler approach for V1 as per prompt "Weighted sum of A–D":
                - Maybe we flip the sign of Volume/Stress to always be negative (Buy pressure)?
                - Or we make Volume/Stress contribution dependent on the sign of Prem/Disc?
                
            - Let's stick to a linear model but maybe flip signs if needed.
            - Prompt says: "Map to action: score <= -T_buy -> BUY".
            - So we want negative score for BUY.
            - Discount (Z < 0) is BUY.
            - Divergence (Z < 0 means Price < Benchmark) is BUY.
            - Volume/Stress (Z > 0) usually means Panic. We want this to contribute to BUY.
            - So we should SUBTRACT Volume/Stress Z-scores?
            
            - Let's try: Score = w_pd * Z_pd + w_div * Z_div - w_vol * Z_vol - w_stress * Z_stress
            
            - Wait, if we are at a Premium (Z_pd > 0) and Volume is High (Z_vol > 0):
                - Score = (+ve) - (+ve) -> Closer to 0. Neutral.
                - This makes sense. Don't short into high volatility?
                
            - If we are at Discount (Z_pd < 0) and Volume is High (Z_vol > 0):
                - Score = (-ve) - (+ve) -> Very Negative. Strong BUY.
                - This makes sense. Panic Selling.
                
            - Let's proceed with this logic: Stress signals contribute negatively (towards BUY).
        """
        
        scores = {}
        
        # Get all tickers
        tickers = set(prem_disc_results.keys()) | set(volume_results.keys()) | set(divergence_results.keys())
        
        # Cross Asset is global usually, but let's check if it has per-ticker or global
        # The implementation returned a "GLOBAL" key.
        ca_val = 0.0
        if "GLOBAL" in cross_asset_result:
            # If triggered, we treat it as max stress? Or use a Z-score if available?
            # Implementation returned value=1.0 if triggered.
            # Let's use that as a Z-proxy or just a fixed penalty.
            # If triggered, we subtract 2.0 (like a 2-sigma event) * weight?
            if cross_asset_result["GLOBAL"]["triggered"]:
                ca_val = 2.0
        
        for ticker in tickers:
            # Get Z-scores, default to 0 if missing/None
            pd_z = prem_disc_results.get(ticker, {}).get('zscore')
            pd_z = pd_z if pd_z is not None else 0.0
            
            div_z = divergence_results.get(ticker, {}).get('zscore')
            div_z = div_z if div_z is not None else 0.0
            
            vol_z = volume_results.get(ticker, {}).get('zscore')
            vol_z = vol_z if vol_z is not None else 0.0
            
            # Calculate weighted sum
            # Note: We subtract Vol and CrossAsset to make them "Buy" forces (Negative Score)
            
            score = (
                self.weights.get('premdisc', 0.35) * pd_z +
                self.weights.get('divergence', 0.30) * div_z -
                self.weights.get('volume', 0.25) * vol_z -
                self.weights.get('cross_asset', 0.10) * ca_val
            )
            
            scores[ticker] = score
            
        return scores
