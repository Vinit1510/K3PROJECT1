import numpy as np
import pandas as pd
from typing import Dict

class TransitionEngine:
    def __init__(self):
        pass

    @staticmethod
    def calculate_markov_chain(series: pd.Series, states: list) -> pd.DataFrame:
        """
        Builds an empirical transition probability matrix for arbitrary categoricals.
        """
        if series.empty or len(series) < 10:
            # Return uniform distribution placeholder
            size = len(states)
            return pd.DataFrame(1.0 / size, index=states, columns=states)
            
        matrix = pd.DataFrame(0, index=states, columns=states)
        
        shifted = series.shift(-1)
        for i in range(len(series) - 1):
            curr_st = series.iloc[i]
            next_st = shifted.iloc[i]
            if curr_st in states and next_st in states:
                matrix.loc[curr_st, next_st] += 1
                
        # Normalize rows to 1.0
        row_sums = matrix.sum(axis=1)
        # Add laplace smoothing to avoid zero division
        matrix = matrix.add(0.1)
        row_sums = matrix.sum(axis=1)
        
        return matrix.div(row_sums, axis=0)

    def get_next_probability(self, series: pd.Series, states: list) -> Dict[str, float]:
        """
        Evaluates the probability distribution for the immediate next step based on last observed state.
        """
        if series.empty:
            return {s: 1.0/len(states) for s in states}
            
        matrix = self.calculate_markov_chain(series, states)
        last_state = series.iloc[-1]
        
        if last_state in matrix.index:
            return matrix.loc[last_state].to_dict()
        return {s: 1.0/len(states) for s in states}
