from typing import Dict, Any, List
from ..config import Config

class RulesEngine:
    def __init__(self, config: Config):
        self.config = config
        self.action_map = config.composite_action_map
        
    def get_action(self, score: float) -> str:
        buy_thresh = self.action_map.get('buy', -0.8)
        sell_thresh = self.action_map.get('sell', 0.8)
        
        if score <= buy_thresh:
            return "BUY"
        elif score >= sell_thresh:
            return "SELL" # Or TRIM
        else:
            return "HOLD"

    def generate_rationale(
        self, 
        ticker: str, 
        action: str, 
        score: float,
        signals: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Generates human-readable rationale.
        Example: "BUY: VTV — premium/discount z=-2.4, volume_z=2.1, IG_OAS +18bps; composite=-0.92"
        """
        parts = []
        
        # Check triggered signals
        # Signals dict structure: {'premdisc': {...}, 'volume': {...}, ...}
        
        for sig_type, sig_data in signals.items():
            # Handle Global signal structure
            if sig_type == 'cross_asset' and 'GLOBAL' in sig_data:
                sig_data = sig_data['GLOBAL']
            elif ticker in sig_data:
                sig_data = sig_data[ticker]
            else:
                continue
                
            if sig_data.get('triggered'):
                details = sig_data.get('details', '')
                parts.append(details)
                
        rationale_str = ", ".join(parts)
        if not rationale_str:
            rationale_str = "No specific triggers"
            
        return f"{action}: {ticker} — {rationale_str}; composite={score:.2f}"
