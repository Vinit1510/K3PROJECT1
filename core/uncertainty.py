class UncertaintyEngine:
    def __init__(self):
        pass

    def calculate_risk(self, variance, entropy, strategy_disagreement):
        """
        Aggregates multiple data chaos markers into a unified uncertainty score.
        Range: 0.0 - 1.0
        """
        base = (entropy / 3.0) * 0.4 # Normalizing sum entropy (usually < 3)
        v_risk = variance * 0.3
        d_risk = strategy_disagreement * 0.3
        return min(1.0, base + v_risk + d_risk)
