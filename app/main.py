from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME, description="My attempt at making a fully functional UPI System")

@app.post("/health")
async def health():
    return {
        "status": "healthy",
        "service": "Pay-Up"
          }
