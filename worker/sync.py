import asyncio
import httpx
import logging
from datetime import datetime
from typing import List, Dict, Any
from core.db import db

logger = logging.getLogger("k3_sync")
logging.basicConfig(level=logging.INFO)

API_URL = "https://draw.ar-lottery01.com/K3/K3_1M/GetHistoryIssuePage.json"

class SyncWorker:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self.is_running = False

    async def fetch_history(self) -> List[Dict[str, Any]]:
        try:
            # Making simple GET, could evolve to POST with pagination payload if needed
            response = await self.client.get(API_URL)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}).get("list", [])
        except Exception as e:
            logger.error(f"Error fetching history: {e}")
            return []

    async def store_results(self, draw_list: List[Dict[str, Any]]):
        for draw in draw_list:
            try:
                issue = draw.get("issueNumber")
                premium = str(draw.get("premium", ""))
                
                if not premium or len(premium) < 3:
                    continue
                
                d1 = int(premium[0])
                d2 = int(premium[1])
                d3 = int(premium[2])
                d_sum = d1 + d2 + d3
                
                big_small = "BIG" if d_sum >= 11 else "SMALL"
                parity = "EVEN" if d_sum % 2 == 0 else "ODD"

                query = """
                INSERT INTO draw_history (issue_number, dice_1, dice_2, dice_3, dice_sum, big_small, parity)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (issue_number) DO NOTHING
                """
                async with db.get_connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(query, (issue, d1, d2, d3, d_sum, big_small, parity))
                    await conn.commit()
            except Exception as e:
                logger.error(f"Failed to store result for issue {draw.get('issueNumber')}: {e}")

    async def run_loop(self):
        self.is_running = True
        logger.info("K3 Sync Worker initiated.")
        while self.is_running:
            try:
                history = await self.fetch_history()
                if history:
                    await self.store_results(history)
                    logger.info(f"Successfully synchronized {len(history)} recent items.")
                    
                    # Proactively compute and store PREDICTION for next round immediately following data drop
                    from core.engine import engine
                    await engine.snapshot_and_save()
                    # Periodically heal any small missed gaps retroactively
                    await engine.backfill_missing_audits(max_rows=5)
                
                # Optimal polling for 1M interval is around 15-30s
                await asyncio.sleep(15)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                await asyncio.sleep(10)

    async def stop(self):
        self.is_running = False
        await self.client.aclose()

sync_worker = SyncWorker()
