import pandas as pd
import numpy as np
from strategies.base import BaseStrategy
from typing import Dict, Any

class SumTrendStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("SumTrendEngine")

    async def analyze(self, history_df: pd.DataFrame, current_features: Dict[str, Any]) -> Dict[str, Any]:
        if len(history_df) < 5:
            return {"prediction": None, "confidence": 0, "signal_strength": 0, "metadata": {}}
        
        # Sort by arrival if not already
        sorted_history = history_df.sort_index(ascending=False)
        recent_sums = sorted_history['dice_sum'].head(10).values
        
        mean_val = recent_sums.mean()
        
        # Simple Mean Reversion approach
        # Global dice expectation is 10.5
        EXPECTATION = 10.5
        
        if mean_val > 11.5:
            # Extended Highs, predicting drop
            prediction = "SMALL"
            strength = min((mean_val - 10.5) / 4.0, 1.0)
        elif mean_val < 9.5:
            # Extended Lows, predicting rise
            prediction = "BIG"
            strength = min((10.5 - mean_val) / 4.0, 1.0)
        else:
            prediction = None
            strength = 0.1

        return {
            "prediction": prediction,
            "confidence": float(strength),
            "signal_strength": float(strength),
            "metadata": {"recent_avg_sum": float(mean_val)}
        }
