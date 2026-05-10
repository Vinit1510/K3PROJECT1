import os
import asyncio
import logging
from contextlib import asynccontextmanager
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/k3_db")
logger = logging.getLogger("k3_db")

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        if not self.pool:
            try:
                logger.info("Initializing database pool connection...")
                self.pool = AsyncConnectionPool(
                    conninfo=DATABASE_URL,
                    open=False,  # open on check, or explicit call
                    kwargs={"row_factory": dict_row}
                )
                await self.pool.open()
                await self.pool.wait()
                logger.info("Database pool connected successfully.")
                await self.init_schema()
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                raise

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed.")

    @asynccontextmanager
    async def get_connection(self):
        async with self.pool.connection() as conn:
            yield conn

    async def execute(self, query: str, params: tuple = None):
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params or ())
                if query.strip().upper().startswith("SELECT"):
                    return await cur.fetchall()
                return cur.rowcount

    async def init_schema(self):
        schema = """
        CREATE TABLE IF NOT EXISTS draw_history (
            issue_number TEXT PRIMARY KEY,
            dice_1 INTEGER,
            dice_2 INTEGER,
            dice_3 INTEGER,
            dice_sum INTEGER,
            big_small TEXT,
            parity TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS engine_features (
            issue_number TEXT PRIMARY KEY REFERENCES draw_history(issue_number),
            spread_range INTEGER,
            has_doubles BOOLEAN,
            has_triples BOOLEAN,
            unique_count INTEGER,
            rolling_sum_avg NUMERIC,
            rolling_sum_var NUMERIC,
            sum_entropy NUMERIC,
            volatility_score NUMERIC,
            current_regime TEXT,
            computed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS engine_audit (
            id SERIAL PRIMARY KEY,
            issue_number TEXT UNIQUE,
            predicted_bigsmall TEXT,
            predicted_parity TEXT,
            confidence NUMERIC,
            uncertainty NUMERIC,
            entropy NUMERIC,
            is_skipped BOOLEAN,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Ensure column compatibility if database pre-exists
        ALTER TABLE engine_audit ADD COLUMN IF NOT EXISTS predicted_parity TEXT;
        ALTER TABLE engine_audit DROP COLUMN IF EXISTS actual_outcome;
        ALTER TABLE engine_audit DROP COLUMN IF EXISTS is_correct;
        
        DELETE FROM engine_audit a USING engine_audit b WHERE a.id < b.id AND a.issue_number = b.issue_number;
        CREATE UNIQUE INDEX IF NOT EXISTS engine_audit_issue_unique_idx ON engine_audit(issue_number);
        CREATE INDEX IF NOT EXISTS idx_draw_history_created ON draw_history(created_at DESC);
        """
        logger.info("Ensuring database tables exist...")
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(schema)
            await conn.commit()

db = Database()
