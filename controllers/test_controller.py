from fastapi import APIRouter

from database import db

router = APIRouter()

@router.get("/database")
async def health_check():
    try:
        await db.command("ping")
        return {"status": "MongoDB connected"}
    except Exception as e:
        return {"status": "MongoDB connection failed", "error": str(e)}