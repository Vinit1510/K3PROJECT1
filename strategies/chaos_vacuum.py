import pandas as pd
import numpy as np
from strategies.base import BaseStrategy
from typing import Dict, Any

class ChaosVacuumStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("ChaosVacuumCore")
        # Dormancy trigger threshold raised to match recalibrated regime
        self.entropy_gate = 2.25

    async def analyze(self, history_df: pd.DataFrame, current_features: Dict[str, Any]) -> Dict[str, Any]:
        current_ent = float(current_features.get('sum_entropy', 0))
        
        # 1. Dormancy Check (Only wake up if truly chaotic)
        if current_ent < self.entropy_gate:
             return {"prediction": None, "confidence": 0, "signal_strength": 0, "metadata": {"status": "dormant"}}

        if len(history_df) < 10:
             return {"prediction": None, "confidence": 0, "signal_strength": 0}

        # 2. The Imbalance Vacuum Calculation
        # Look at the last 15 rounds making up this chaotic cluster
        sample_window = history_df.tail(15)
        
        bs_series = sample_window['big_small']
        parity_series = sample_window['parity']
        
        big_c = (bs_series == 'BIG').sum()
        small_c = (bs_series == 'SMALL').sum()
        odd_c = (parity_series == 'ODD').sum()
        even_c = (parity_series == 'EVEN').sum()
        
        # Calculate critical deficit ratios
        bs_total = big_c + small_c
        par_total = odd_c + even_c
        
        pred = None
        target = None
        confidence = 0.0
        
        # Identify single greatest deficit across BOTH domains
        # (Targeting the category most "starved" during this chaos window)
        
        # Domain 1: Size Imbalance
        bs_diff = abs(big_c - small_c)
        bs_ratio = bs_diff / bs_total if bs_total > 0 else 0
        
        # Domain 2: Parity Imbalance
        par_diff = abs(odd_c - even_c)
        par_ratio = par_diff / par_total if par_total > 0 else 0
        
        # Direct the strike towards the most starved target
        if bs_ratio >= par_ratio and bs_ratio > 0.15:
             # Big/Small is the most starved
             pred = "BIG" if small_c > big_c else "SMALL"
             confidence = 0.75 + (bs_ratio * 0.2) # Dynamic scaling
             target = "BS"
        elif par_ratio > 0.15:
             # Parity is the most starved
             pred = "ODD" if even_c > odd_c else "EVEN"
             confidence = 0.75 + (par_ratio * 0.2)
             target = "PARITY"
             
        return {
            "prediction": pred,
            "confidence": min(0.95, confidence),
            "signal_strength": max(bs_ratio, par_ratio),
            "metadata": {
                "mode": "CHAOS_HUNTER",
                "entropy_reading": current_ent,
                "target_domain": target
            }
        }
