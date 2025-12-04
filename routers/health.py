from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from models.base import get_db
from config import settings

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/live")
async def liveness():
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "app": settings.app_name,
        "version": settings.app_version
    }

@router.get("/ready")
async def readiness(db: Session = Depends(get_db)):
    checks = {
        "database": False,
        "ai_service": False,
        "optimization_engine": False,
        "integrations": False
    }
    
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        checks["database_error"] = str(e)
    
    try:
        from core.ai_service import AIService
        checks["ai_service"] = True
    except Exception as e:
        checks["ai_service_error"] = str(e)
    
    try:
        from core.optimization_engine import OptimizationEngine
        import pulp
        checks["optimization_engine"] = True
    except Exception as e:
        checks["optimization_engine_error"] = str(e)
    
    try:
        from core.connectors import CONNECTOR_TYPES
        checks["integrations"] = len(CONNECTOR_TYPES) > 0
    except Exception as e:
        checks["integrations_error"] = str(e)
    
    all_healthy = all(v for k, v in checks.items() if not k.endswith("_error"))
    
    return {
        "status": "ready" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
        "demo_mode": settings.demo_mode
    }

@router.get("/")
async def health_root():
    return {"status": "ok", "app": settings.app_name}
