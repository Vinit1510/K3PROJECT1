import pandas as pd
from strategies.base import BaseStrategy
from typing import Dict, Any

class MomentumProStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("MomentumPro")

    async def analyze(self, history_df: pd.DataFrame, current_features: Dict[str, Any]) -> Dict[str, Any]:
        if len(history_df) < 10:
             return {"prediction": None, "confidence": 0, "signal_strength": 0, "metadata": {}}
             
        # Look at absolute recent sequence
        recent = history_df.tail(5)
        size_list = recent['big_small'].tolist()
        parity_list = recent['parity'].tolist()
        
        # --- DOMAIN 1: PARITY TREND-RIDER (THE WINNING TACTIC) ---
        # Count immediate active streak from tail
        last_p = parity_list[-1]
        streak_p = 1
        for i in range(len(parity_list)-2, -1, -1):
             if parity_list[i] == last_p:
                  streak_p += 1
             else:
                  break
        
        # AGGRESSIVE RULE: If streak is 2 to 5, RIDE THE TRAIN!
        # This is exactly what won the manual showdown.
        if 2 <= streak_p <= 5:
             return {
                  "prediction": last_p, # Follow current trend
                  "confidence": 0.75 + (streak_p * 0.03), 
                  "signal_strength": 0.8,
                  "metadata": {"logic": "PARITY_MOMENTUM_TRAIN", "streak": streak_p}
             }

        # --- DOMAIN 2: SIZE CLUSTER / ZIGZAG DETECTOR ---
        # Check for Perfect Oscillator (S-B-S-B)
        if size_list[-1] != size_list[-2] and size_list[-2] != size_list[-3] and size_list[-3] != size_list[-4]:
             # Oscillator detected, call the bounce!
             next_osc = "BIG" if size_list[-1] == "SMALL" else "SMALL"
             return {
                  "prediction": next_osc,
                  "confidence": 0.82,
                  "signal_strength": 0.85,
                  "metadata": {"logic": "SIZE_OSCILLATOR_BOUNCE"}
             }
             
        # Check for Twin Cluster (B-B-S -> predict S)
        if size_list[-3] == size_list[-2] and size_list[-2] != size_list[-1]:
             # Just entered a new cluster step 1, call step 2 completion!
             next_twin = size_list[-1] 
             return {
                  "prediction": next_twin,
                  "confidence": 0.80,
                  "signal_strength": 0.80,
                  "metadata": {"logic": "SIZE_TWIN_COMPLETION"}
             }

        return {"prediction": None, "confidence": 0, "signal_strength": 0, "metadata": {}}
