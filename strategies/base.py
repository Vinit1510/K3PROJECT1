import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name
        self.weight = 1.0
        self.historical_accuracy = 0.5
        self.total_predictions = 0
        
    @abstractmethod
    async def analyze(self, history_df: pd.DataFrame, current_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes history and predicts next state.
        Returns dict containing:
        - prediction: Any (e.g. "BIG", "SMALL", "ODD", "EVEN")
        - confidence: float (0.0 - 1.0)
        - signal_strength: float (0.0 - 1.0)
        - metadata: dict
        """
        pass

    def update_performance(self, was_correct: bool):
        self.total_predictions += 1
        alpha = 0.05 # Adaptation speed
        outcome = 1.0 if was_correct else 0.0
        self.historical_accuracy = (1 - alpha) * self.historical_accuracy + alpha * outcome
        # Soft Cap to avoid strategy death
        self.historical_accuracy = max(0.1, min(0.9, self.historical_accuracy))
