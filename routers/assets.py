from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import List, Optional
from models.base import get_db
from models.user import User
from models.asset import Site, Asset, AssetComponent, AssetFailureMode, AssetAIScore, AssetMetricsSnapshot
from core.auth import get_current_user
from core.rbac import has_capability, require_tenant_access

router = APIRouter(prefix="/api/assets", tags=["Assets"])

class SiteCreate(BaseModel):
    code: str
    name: str
    name_ar: Optional[str] = None
    location: Optional[str] = None
    site_type: Optional[str] = None

class AssetCreate(BaseModel):
    site_id: Optional[int] = None
    parent_asset_id: Optional[int] = None
    code: str
    name: str
    name_ar: Optional[str] = None
    asset_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    criticality: str = "medium"

@router.get("/sites")
async def list_sites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tenant_id = current_user.tenant_id
    if current_user.role == "platform_owner":
        sites = db.query(Site).filter(Site.is_active == True).all()
    else:
        sites = db.query(Site).filter(
            Site.tenant_id == tenant_id,
            Site.is_active == True
        ).all()
    
    return [s.to_dict() for s in sites]

@router.post("/sites")
async def create_site(
    site_data: SiteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    site = Site(
        tenant_id=tenant_id,
        code=site_data.code,
        name=site_data.name,
        name_ar=site_data.name_ar,
        location=site_data.location,
        site_type=site_data.site_type
    )
    db.add(site)
    db.commit()
    
    return {"success": True, "site": site.to_dict()}

@router.get("/")
async def list_assets(
    site_id: Optional[int] = None,
    criticality: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(Asset).filter(Asset.is_active == True)
    
    if current_user.role != "platform_owner":
        query = query.filter(Asset.tenant_id == current_user.tenant_id)
    
    if site_id:
        query = query.filter(Asset.site_id == site_id)
    if criticality:
        query = query.filter(Asset.criticality == criticality)
    if status:
        query = query.filter(Asset.status == status)
    
    total = query.count()
    assets = query.offset(offset).limit(limit).all()
    
    result = []
    for asset in assets:
        asset_dict = asset.to_dict()
        ai_score = db.query(AssetAIScore).filter(
            AssetAIScore.asset_id == asset.id
        ).order_by(desc(AssetAIScore.computed_at)).first()
        if ai_score:
            asset_dict["ai_score"] = ai_score.to_dict()
        result.append(asset_dict)
    
    return {"total": total, "assets": result}

@router.get("/{asset_id}")
async def get_asset(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    require_tenant_access(current_user, asset.tenant_id)
    
    asset_dict = asset.to_dict()
    
    ai_score = db.query(AssetAIScore).filter(
        AssetAIScore.asset_id == asset_id
    ).order_by(desc(AssetAIScore.computed_at)).first()
    if ai_score:
        asset_dict["ai_score"] = ai_score.to_dict()
    
    components = db.query(AssetComponent).filter(
        AssetComponent.asset_id == asset_id,
        AssetComponent.is_active == True
    ).all()
    asset_dict["components"] = [{"id": c.id, "code": c.code, "name": c.name} for c in components]
    
    failure_modes = db.query(AssetFailureMode).filter(
        AssetFailureMode.asset_id == asset_id,
        AssetFailureMode.is_active == True
    ).all()
    asset_dict["failure_modes"] = [{
        "id": fm.id, "code": fm.code, "name": fm.name,
        "severity": fm.severity, "occurrence": fm.occurrence, 
        "detection": fm.detection, "rpn": fm.rpn
    } for fm in failure_modes]
    
    return asset_dict

@router.post("/")
async def create_asset(
    asset_data: AssetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    asset = Asset(
        tenant_id=tenant_id,
        site_id=asset_data.site_id,
        parent_asset_id=asset_data.parent_asset_id,
        code=asset_data.code,
        name=asset_data.name,
        name_ar=asset_data.name_ar,
        asset_type=asset_data.asset_type,
        manufacturer=asset_data.manufacturer,
        model=asset_data.model,
        serial_number=asset_data.serial_number,
        criticality=asset_data.criticality
    )
    db.add(asset)
    db.commit()
    
    return {"success": True, "asset": asset.to_dict()}

@router.get("/{asset_id}/metrics")
async def get_asset_metrics(
    asset_id: int,
    limit: int = Query(default=100, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    require_tenant_access(current_user, asset.tenant_id)
    
    metrics = db.query(AssetMetricsSnapshot).filter(
        AssetMetricsSnapshot.asset_id == asset_id
    ).order_by(desc(AssetMetricsSnapshot.recorded_at)).limit(limit).all()
    
    return [{
        "id": m.id,
        "metric_name": m.metric_name,
        "metric_value": float(m.metric_value) if m.metric_value else None,
        "unit": m.unit,
        "quality": m.quality,
        "recorded_at": m.recorded_at.isoformat() if m.recorded_at else None,
        "source": m.source
    } for m in metrics]

@router.get("/{asset_id}/ai-scores")
async def get_asset_ai_scores(
    asset_id: int,
    limit: int = Query(default=10, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    require_tenant_access(current_user, asset.tenant_id)
    
    scores = db.query(AssetAIScore).filter(
        AssetAIScore.asset_id == asset_id
    ).order_by(desc(AssetAIScore.computed_at)).limit(limit).all()
    
    return [s.to_dict() for s in scores]
