import numpy as np
import pandas as pd
from scipy.stats import entropy
from typing import List, Dict, Any

class FeatureEngineer:
    @staticmethod
    def compute_features(draws_df: pd.DataFrame) -> pd.DataFrame:
        """
        Accepts DataFrame with columns: [dice_1, dice_2, dice_3]
        Returns DataFrame with engineered features.
        """
        if draws_df.empty:
            return draws_df
            
        df = draws_df.copy()
        
        # Basic sums and categories
        df['dice_sum'] = df[['dice_1', 'dice_2', 'dice_3']].sum(axis=1)
        df['big_small'] = np.where(df['dice_sum'] >= 11, 'BIG', 'SMALL')
        df['parity'] = np.where(df['dice_sum'] % 2 == 0, 'EVEN', 'ODD')
        
        # Spread and Uniqueness
        dices = df[['dice_1', 'dice_2', 'dice_3']].values
        df['spread_range'] = dices.max(axis=1) - dices.min(axis=1)
        
        unique_counts = [len(np.unique(r)) for r in dices]
        df['unique_count'] = unique_counts
        df['has_doubles'] = df['unique_count'] == 2
        df['has_triples'] = df['unique_count'] == 1
        
        # Rolling Stats
        df['rolling_sum_avg'] = df['dice_sum'].rolling(window=10, min_periods=1).mean()
        df['rolling_sum_var'] = df['dice_sum'].rolling(window=10, min_periods=1).var().fillna(0)
        df['rolling_sum_std'] = df['dice_sum'].rolling(window=10, min_periods=1).std().fillna(0)
        
        # Z-Score
        overall_mean = df['dice_sum'].mean()
        overall_std = df['dice_sum'].std()
        df['z_score'] = (df['dice_sum'] - overall_mean) / (overall_std if overall_std > 0 else 1)
        
        # Entropy - Rolling measure of distribution uniformity
        def calc_rolling_entropy(x):
            value_counts = pd.Series(x).value_counts(normalize=True)
            return entropy(value_counts)
            
        df['sum_entropy'] = df['dice_sum'].rolling(window=15, min_periods=5).apply(calc_rolling_entropy, raw=False).fillna(0)
        
        # Map categorical states to numeric proxies before rolling to avoid pandas.errors.DataError
        big_small_numeric = (df['big_small'] == 'BIG').astype(int)
        df['big_small_entropy'] = big_small_numeric.rolling(window=15, min_periods=5).apply(calc_rolling_entropy, raw=False).fillna(0)
        
        # Volatility Score - Normalized standard deviation of sums
        df['volatility_score'] = (df['rolling_sum_std'] / 4.0).clip(0, 1) # Max theoretical std is around 4 for dice sums
        
        return df

    @staticmethod
    def determine_regime(row: pd.Series) -> str:
        """Heuristic approach to categorize current game state regime"""
        vol = row.get('volatility_score', 0)
        ent = row.get('sum_entropy', 0)
        var = row.get('rolling_sum_var', 0)
        
        if vol > 0.9 or ent > 2.3:
            return "CHAOTIC"
        if var < 1.5:
            return "COMPRESSED"
        if vol < 0.3 and abs(row.get('z_score', 0)) > 1.0:
            return "TRENDING"
        
        return "NORMAL"

feature_store = FeatureEngineer()
