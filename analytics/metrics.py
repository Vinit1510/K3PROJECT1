import pandas as pd
import numpy as np

class MetricAnalyzer:
    @staticmethod
    def calculate_sum_distribution(df: pd.DataFrame):
        """Calculates counts for sums 3 through 18"""
        if df.empty:
            return {}
        dist = df['dice_sum'].value_counts().sort_index().to_dict()
        # Ensure all possible dice sums are represented for UI graphing compatibility
        full_dist = {s: int(dist.get(s, 0)) for s in range(3, 19)}
        return full_dist

    @staticmethod
    def calculate_win_rate(audit_rows: list) -> float:
        if not audit_rows:
            return 0.0
        valid = [r for r in audit_rows if not r.get('is_skipped')]
        if not valid:
            return 0.0
        correct = [r for r in valid if r.get('is_correct')]
        return len(correct) / len(valid)

    @staticmethod
    def calculate_current_streak(df: pd.DataFrame, column: str) -> int:
        """Calculate the running active streak length"""
        if df.empty:
            return 0
        vals = df[column].values[::-1] # Newest first
        streak = 1
        for i in range(len(vals) - 1):
            if vals[i] == vals[i+1]:
                streak += 1
            else:
                break
        return streak
