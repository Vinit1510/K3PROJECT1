import pandas as pd
from strategies.base import BaseStrategy
from core.transition_matrix import TransitionEngine
from typing import Dict, Any

class TransitionStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("MarkovTransitionEngine")
        self.te = TransitionEngine()

    async def analyze(self, history_df: pd.DataFrame, current_features: Dict[str, Any]) -> Dict[str, Any]:
        if len(history_df) < 20:
            return {"prediction": None, "confidence": 0, "signal_strength": 0, "metadata": {}}
            
        states = ["BIG", "SMALL"]
        probs = self.te.get_next_probability(history_df['big_small'], states)
        
        p_big = probs.get("BIG", 0.5)
        p_small = probs.get("SMALL", 0.5)
        
        diff = abs(p_big - p_small)
        
        # Higher confidence threshold for transition data
        if diff > 0.15:
            final_pred = "BIG" if p_big > p_small else "SMALL"
            conf = max(p_big, p_small)
            return {
                "prediction": final_pred,
                "confidence": float(conf),
                "signal_strength": float(diff),
                "metadata": probs
            }
            
        return {"prediction": None, "confidence": 0, "signal_strength": 0, "metadata": {}}
