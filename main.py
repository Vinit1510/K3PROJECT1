import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 K3 Quantum Adaptive Engine igniting on {host}:{port}")
    uvicorn.run("api.server:app", host=host, port=port, reload=True)
