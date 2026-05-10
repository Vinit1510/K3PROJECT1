from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import asyncio
from contextlib import asynccontextmanager
import logging
import os
import io
import pandas as pd

from core.db import db
from core.engine import engine
from worker.sync import sync_worker

logger = logging.getLogger("k3_api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    await db.connect()
    
    # Run initial backfill to heal any "PENDING" legacy records
    asyncio.create_task(engine.backfill_missing_audits(max_rows=100))
    
    # Start the persistent background synchronization worker task
    asyncio.create_task(sync_worker.run_loop())
    
    yield
    
    # Shutdown actions
    await sync_worker.stop()
    await db.disconnect()

app = FastAPI(title="K3 Quantum Adaptive Engine API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
@app.get("/api/health")
async def health():
    return {"status": "alive"}

@app.get("/api/current_prediction")
async def get_prediction():
    prediction_res = await engine.generate_prediction()
    return prediction_res

@app.get("/api/history")
async def get_history(limit: int = 20):
    df = await engine.get_latest_history(limit)
    if df.empty:
        return []
    # Reverse back to newest first for proper UI chronological display
    reversed_df = df.iloc[::-1]
    return reversed_df.to_dict(orient="records")

@app.post("/api/clear_data")
async def clear_all_data():
    try:
        # Cascading deletions across system tables
        await db.execute("DELETE FROM engine_audit")
        await db.execute("DELETE FROM draw_history")
        return {"status": "success", "message": "System registers completely sanitized."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/download_excel")
async def download_history_excel():
    try:
        # Load rich historical dataset
        df = await engine.get_latest_history(limit=1000)
        if df.empty:
             # Create an empty structured DF to avoid crash
             df = pd.DataFrame(columns=["issue_number", "dice_sum", "big_small", "parity"])
             
        # Clean column display formatting
        df = df.iloc[::-1] # chronological
        
        # Binary buffer writing sequence
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="K3_Audits")
        
        buffer.seek(0)
        headers = {'Content-Disposition': 'attachment; filename="k3_quantum_report.xlsx"'}
        return StreamingResponse(buffer, headers=headers, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        logger.error(f"Excel export encountered catastrophic failure: {e}")
        return {"error": str(e)}

# Mount the public dashboard after everything is generated
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")
os.makedirs(PUBLIC_DIR, exist_ok=True)

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(PUBLIC_DIR, "index.html"))

# Optional static folder mounting if assets exist
# app.mount("/static", StaticFiles(directory="public"), name="public")
