import logging
from typing import Dict

logger = logging.getLogger("k3_weights")

class WeightAdapter:
    """
    Gradually modulates strategy influence levels based on long-term calibration drift.
    Prevents reactive whipsawing through slow alpha decay.
    """
    def __init__(self, learning_rate: float = 0.02):
        self.alpha = learning_rate
        self.weights: Dict[str, float] = {}

    def update_weights(self, strategy_name: str, is_correct: bool):
        current = self.weights.get(strategy_name, 1.0)
        
        # Directional shift
        delta = 1.0 if is_correct else -1.0
        
        # Calculate nudge
        new_val = current + (self.alpha * delta)
        
        # Boundary enforcement
        self.weights[strategy_name] = max(0.2, min(2.0, new_val))
        
    def get_weight(self, strategy_name: str) -> float:
        return self.weights.get(strategy_name, 1.0)
