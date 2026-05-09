from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.config import settings
from app.schemas import HealthOut

router = APIRouter()


@router.get("", response_model=HealthOut)
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"

    return HealthOut(
        status="ok" if db_status == "ok" else "degraded",
        environment=settings.ENV,
        version=settings.APP_VERSION,
        db=db_status,
    )
    