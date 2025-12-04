from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from models.base import get_db
from models.user import User
from config import settings
from core.auth import get_current_user

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

@router.get("/internal/config/status")
async def internal_config_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Internal diagnostics endpoint (platform_owner only).
    Shows system configuration status without exposing secrets.
    """
    if current_user.role != "platform_owner":
        raise HTTPException(status_code=403, detail="Only platform owners can access this endpoint")
    
    status_report = {
        "timestamp": datetime.utcnow().isoformat(),
        "subsystems": {
            "database": {
                "status": "unknown",
                "source": "environment"
            },
            "openai_api": {
                "status": "missing" if not settings.openai_api_key else "configured",
                "source": "OPENAI_API_KEY secret"
            },
            "optimization_engine": {
                "status": "enabled" if settings.optimization_engine_enabled else "disabled",
                "source": f"OPTIMIZATION_ENGINE_ENABLED={settings.optimization_engine_enabled}",
                "flag": settings.optimization_engine_enabled
            },
            "external_db_integrations": {
                "status": "enabled" if settings.external_db_enable else "disabled",
                "source": f"EXTERNAL_DB_ENABLE={settings.external_db_enable}",
                "flag": settings.external_db_enable
            },
            "pi_default_config": {
                "status": "configured" if settings.pi_base_url else "empty",
                "source": "PI_BASE_URL secret",
                "has_url": bool(settings.pi_base_url)
            },
            "sap_default_config": {
                "status": "configured" if settings.sap_base_url else "empty",
                "source": "SAP_BASE_URL secret",
                "has_url": bool(settings.sap_base_url)
            },
            "opcua_default_creds": {
                "status": "configured" if settings.opcua_username else "empty",
                "source": "OPCUA_USERNAME/OPCUA_PASSWORD secrets",
                "has_creds": bool(settings.opcua_username and settings.opcua_password)
            },
            "demo_mode": {
                "status": "enabled" if settings.demo_mode else "disabled",
                "source": f"DEMO_MODE={settings.demo_mode}",
                "flag": settings.demo_mode
            }
        },
        "feature_flags": {
            "demo_mode": settings.demo_mode,
            "optimization_engine_enabled": settings.optimization_engine_enabled,
            "external_db_enable": settings.external_db_enable
        }
    }
    
    try:
        db.execute(text("SELECT 1"))
        status_report["subsystems"]["database"]["status"] = "ok"
    except Exception as e:
        status_report["subsystems"]["database"]["status"] = "error"
        status_report["subsystems"]["database"]["error"] = str(e)
    
    return status_report
