import asyncio
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List
from core.db import db
from core.feature_store import feature_store
from strategies.sum_trend import SumTrendStrategy
from strategies.transition_engine import TransitionStrategy
from strategies.momentum_pro import MomentumProStrategy
from strategies.chaos_vacuum import ChaosVacuumStrategy
from core.uncertainty import UncertaintyEngine

logger = logging.getLogger("k3_engine")

class QuantumEngine:
    def __init__(self):
        self.strategies = [
            SumTrendStrategy(),
            TransitionStrategy(),
            MomentumProStrategy(),
            ChaosVacuumStrategy()
        ]
        self.uncertainty_engine = None # initialized separately to avoid circular deps
        self.min_confidence_threshold = 0.6
        self.max_uncertainty_threshold = 0.4

    def _sanitize_float(self, val):
        import math
        try:
            v = float(val)
            if math.isnan(v) or math.isinf(v):
                return 0.0
            return v
        except:
            return 0.0

    async def get_latest_history(self, limit=100):
        query = """
            SELECT d.*, 
                   a.predicted_bigsmall, 
                   a.predicted_parity, 
                   a.is_skipped as audit_skipped
            FROM draw_history d
            LEFT JOIN engine_audit a ON d.issue_number = a.issue_number
            ORDER BY d.issue_number DESC 
            LIMIT %s
        """
        rows = await db.execute(query, (limit,))
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        # Reverse to ascending order for proper feature calculation (rolling)
        df = df.iloc[::-1].reset_index(drop=True)
        return df

    async def generate_prediction(self, input_history: pd.DataFrame = None) -> Dict[str, Any]:
        if input_history is not None:
            history_df = input_history
        else:
            history_df = await self.get_latest_history(50)
            
        if history_df.empty or len(history_df) < 10:
            return {"status": "insufficient_data", "prediction": None}

        enriched_df = feature_store.compute_features(history_df)
        current_features = enriched_df.iloc[-1].to_dict()
        current_regime = feature_store.determine_regime(enriched_df.iloc[-1])
        
        # Automated increment of last issue number
        last_issue = current_features.get('issue_number', "0")
        try:
            # Attempts to cleanly increment pure numeric period strings
            next_issue = str(int(last_issue) + 1)
        except ValueError:
            next_issue = "PENDING"

        # --- SELF-LEARNING CALIBRATION MODULE ---
        # Dynamically audits the last 3 rounds to detect "Hot" or "Cold" strategies.
        momentum_multipliers = {}
        try:
            for strat in self.strategies:
                momentum = 1.0
                penalty = 0.0
                # Evaluate past 3 completed cycles
                for backstep in range(1, 4): 
                    # past_context contains data BEFORE the target result arrived
                    if len(enriched_df) <= backstep: continue
                    past_context = enriched_df.iloc[:-backstep]
                    
                    # The target row contains the actual arrival result for this step
                    target_row = enriched_df.iloc[-backstep]
                    
                    if len(past_context) < 8: continue
                    
                    back_res = await strat.analyze(past_context, past_context.iloc[-1].to_dict())
                    b_pred = back_res.get("prediction")
                    if b_pred:
                         is_bs = b_pred in ["BIG", "SMALL"]
                         actual = target_row.get("big_small") if is_bs else target_row.get("parity")
                         
                         if b_pred == actual:
                              # Winning streak adds weight faster
                              penalty -= 0.2
                         else:
                              # Labeled failure drastically slashes immediate authority
                              penalty += 0.4
                
                # Finalize dynamic modifier range [0.2 to 1.3]
                momentum_multipliers[strat.name] = max(0.2, min(1.3, 1.0 - penalty))
        except Exception as calibrate_error:
             logger.warn(f"Self-calibration drift ignored: {calibrate_error}")

        # Collect all predictions
        votes = []
        is_chaotic_regime = (current_regime == "CHAOTIC")
        
        for strat in self.strategies:
            # EXPERT ISOLATION PROTOCOL
            # During Chaos, standard strategies are blinded by randomness. 
            # We SILENCE all generalists and force explicit reliance ONLY on the Specialist!
            if is_chaotic_regime and strat.name != "ChaosVacuumCore":
                 continue
                 
            res = await strat.analyze(enriched_df, current_features)
            pred_val = res.get("prediction")
            if pred_val:
                # Classify target bucket
                target = "BS" if pred_val in ["BIG", "SMALL"] else "PARITY"
                
                # Apply self-learning multiplier!
                dyn_mult = momentum_multipliers.get(strat.name, 1.0)
                
                votes.append({
                    "strat": strat.name,
                    "target": target,
                    "pred": pred_val,
                    "conf": res["confidence"] * strat.historical_accuracy * dyn_mult,
                })

        # 1. Handle BigSmall Aggregation
        bs_votes = [v for v in votes if v["target"] == "BS"]
        big_score = sum(v["conf"] for v in bs_votes if v["pred"] == "BIG")
        small_score = sum(v["conf"] for v in bs_votes if v["pred"] == "SMALL")
        bs_total = big_score + small_score
        
        if bs_total > 0:
            final_bs = "BIG" if big_score >= small_score else "SMALL"
            bs_conf = max(big_score, small_score) / bs_total
        else:
            final_bs = None
            bs_conf = 0.0

        # 2. Handle Parity Aggregation
        par_votes = [v for v in votes if v["target"] == "PARITY"]
        odd_score = sum(v["conf"] for v in par_votes if v["pred"] == "ODD")
        even_score = sum(v["conf"] for v in par_votes if v["pred"] == "EVEN")
        par_total = odd_score + even_score
        
        if par_total > 0:
            final_parity = "ODD" if odd_score >= even_score else "EVEN"
            par_conf = max(odd_score, even_score) / par_total
        else:
            final_parity = None
            par_conf = 0.0

        # Simple uncertainty blend
        agreement = 1.0
        if bs_total > 0:
            agreement = abs(big_score - small_score) / bs_total
        uncertainty = 1.0 - agreement

        # Regime-based dynamic thresholds
        current_threshold = self.min_confidence_threshold
        is_chaotic = (current_regime == "CHAOTIC")
        
        if is_chaotic:
            # During detected Chaos, our specialized vacuum logic manages itself.
            # We Lower the restrictive gates and ignore traditional uncertainty filters to let it strike!
            current_threshold = 0.55
            uncertainty = min(1.0, uncertainty) # cap don't escalate
        
        # Decides skip based mostly on confidence of active predictions
        max_conf = max(bs_conf, par_conf)
        
        if is_chaotic:
            # Chaos Override: Trust Confidence alone, bypass uncertainty cap
            is_skipped = (max_conf < current_threshold)
        else:
            is_skipped = (max_conf < current_threshold) or (uncertainty > self.max_uncertainty_threshold)
            
        if max_conf == 0:
             is_skipped = True

        result = {
            "issue_number": next_issue,
            "prediction_bs": final_bs,
            "prediction_parity": final_parity,
            "confidence": round(float(max_conf), 3),
            "uncertainty": round(float(uncertainty), 3),
            "entropy": round(float(current_features.get('sum_entropy', 0)), 3),
            "regime": current_regime,
            "is_skipped": bool(is_skipped),
            "volatility": round(float(current_features.get('volatility_score', 0)), 3)
        }
        
        return result

    async def snapshot_and_save(self):
        """Executes full projection cycle and logs result to persisting audit log."""
        try:
            res = await self.generate_prediction()
            if "issue_number" in res and res["issue_number"] != "PENDING":
                query = """
                INSERT INTO engine_audit (issue_number, predicted_bigsmall, predicted_parity, confidence, uncertainty, entropy, is_skipped)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (issue_number) DO UPDATE SET
                    predicted_bigsmall = EXCLUDED.predicted_bigsmall,
                    predicted_parity = EXCLUDED.predicted_parity,
                    confidence = EXCLUDED.confidence,
                    uncertainty = EXCLUDED.uncertainty,
                    entropy = EXCLUDED.entropy,
                    is_skipped = EXCLUDED.is_skipped;
                """
                await db.execute(query, (
                    str(res["issue_number"]).strip(),
                    res["prediction_bs"],
                    res["prediction_parity"],
                    self._sanitize_float(res["confidence"]),
                    self._sanitize_float(res["uncertainty"]),
                    self._sanitize_float(res["entropy"]),
                    res["is_skipped"]
                ))
        except Exception as e:
            logger.error(f"Failed to save audit snapshot: {e}")

    async def backfill_missing_audits(self, max_rows=20):
        """Detects historical entries lacking stored audits and runs retroactive projections using proper chronological slicing."""
        try:
            # Fetch items that do not exist in engine_audit table
            query = """
                SELECT issue_number FROM draw_history 
                WHERE issue_number NOT IN (SELECT issue_number FROM engine_audit)
                ORDER BY issue_number ASC
                LIMIT %s
            """
            missing = await db.execute(query, (max_rows,))
            if not missing:
                return
            
            logger.info(f"Found {len(missing)} historical items with missing audits. Initiating retroactive analysis...")
            
            # Load raw universal history to slide the window accurately
            all_hist_query = "SELECT * FROM draw_history ORDER BY issue_number ASC"
            all_data = pd.DataFrame(await db.execute(all_hist_query))
            
            if all_data.empty:
                return

            count = 0
            for row in missing:
                missing_issue = row["issue_number"]
                # Extract historical snapshot existing PRIOR to this issue moment
                prior_context = all_data[all_data["issue_number"] < missing_issue].tail(50)
                
                if len(prior_context) < 10:
                    continue
                    
                # Regenerate projection based ONLY on past context (zero data leakage)
                proj = await self.generate_prediction(input_history=prior_context)
                
                if proj.get("status") == "insufficient_data":
                    continue
                
                # Safely explicitly override issue number back to the one we're filling, to verify continuity
                save_query = """
                INSERT INTO engine_audit (issue_number, predicted_bigsmall, predicted_parity, confidence, uncertainty, entropy, is_skipped)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (issue_number) DO NOTHING
                """
                await db.execute(save_query, (
                    str(missing_issue).strip(), # Store directly under original missing issue identifier
                    proj["prediction_bs"],
                    proj["prediction_parity"],
                    self._sanitize_float(proj["confidence"]),
                    self._sanitize_float(proj["uncertainty"]),
                    self._sanitize_float(proj["entropy"]),
                    proj["is_skipped"]
                ))
                count += 1
            
            if count > 0:
                logger.info(f"Completed dynamic audit backfill. Repaired {count} records.")
                
        except Exception as e:
            logger.error(f"Backfill analysis encountered failure: {e}")

engine = QuantumEngine()
