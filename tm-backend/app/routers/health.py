from fastapi import APIRouter
from sqlalchemy import text
from datetime import datetime

from app.database import SessionLocal

router = APIRouter(prefix="/api", tags=["健康检查"])


@router.get("/health")
async def health_check():
    """健康检查接口，返回服务状态和数据库连接状态"""
    status = "healthy"
    db_status = "connected"

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_status = "disconnected"
        status = "unhealthy"

    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "database": db_status
    }
