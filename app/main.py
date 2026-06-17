from datetime import datetime, UTC

from fastapi import FastAPI


app = FastAPI(
    title="AgroCollective API",
    version="0.1.0"
)


@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat()
    }