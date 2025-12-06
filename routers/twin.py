"""
Digital Twin Configuration and Management APIs
Manage layouts, nodes, and asset bindings for industrial visualization
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime, timedelta
from models.user import User
from models.blackbox import TwinLayout, TwinNode, BlackBoxIncident
from models.asset import Asset, Site, AssetAIScore
from models.integration import TenantIntegration, ExternalSignalMapping
from core.auth import get_current_user
from core.rbac import has_capability
from models.base import get_db
from core.twin_service import get_twin_assets_for_tenant
from pydantic import BaseModel

router = APIRouter(prefix="/api/twins", tags=["twins"])


class TwinLayoutCreate(BaseModel):
    name: str
    description: Optional[str] = None
    site_id: Optional[int] = None
    width: int = 1200
    height: int = 800
    background_color: str = "#ffffff"
    background_image: Optional[str] = None
    config: dict = {}
    is_default: bool = False


class TwinLayoutUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    background_color: Optional[str] = None
    background_image: Optional[str] = None
    config: Optional[dict] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class TwinNodeCreate(BaseModel):
    layout_id: int
    node_type: str
    label: Optional[str] = None
    asset_id: Optional[int] = None
    position_x: int = 0
    position_y: int = 0
    width: int = 100
    height: int = 80
    rotation: int = 0
    icon: Optional[str] = None
    color: str = "#3b82f6"
    style: dict = {}
    parent_node_id: Optional[int] = None
    data_bindings: dict = {}
    z_index: int = 0


class TwinNodeUpdate(BaseModel):
    label: Optional[str] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    rotation: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    style: Optional[dict] = None
    data_bindings: Optional[dict] = None
    z_index: Optional[int] = None
    is_visible: Optional[bool] = None


@router.get("/layouts")
async def list_layouts(
    site_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List digital twin layouts"""
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(TwinLayout).filter(
        TwinLayout.tenant_id == current_user.tenant_id
    )
    
    if site_id:
        query = query.filter(TwinLayout.site_id == site_id)
    if is_active is not None:
        query = query.filter(TwinLayout.is_active == is_active)
    
    total = query.count()
    layouts = query.order_by(TwinLayout.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "layouts": [l.to_dict(include_nodes=True) for l in layouts],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/layouts")
async def create_layout(
    layout_data: TwinLayoutCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new digital twin layout"""
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if layout_data.site_id:
        from models.asset import Site
        site = db.query(Site).filter(
            Site.id == layout_data.site_id,
            Site.tenant_id == current_user.tenant_id
        ).first()
        if not site:
            raise HTTPException(status_code=400, detail="Site not found")
    
    layout = TwinLayout(
        tenant_id=current_user.tenant_id,
        name=layout_data.name,
        description=layout_data.description,
        site_id=layout_data.site_id,
        width=layout_data.width,
        height=layout_data.height,
        background_color=layout_data.background_color,
        background_image=layout_data.background_image,
        config=layout_data.config,
        is_default=layout_data.is_default,
        is_active=True
    )
    db.add(layout)
    db.commit()
    
    return {"success": True, "layout": layout.to_dict()}


@router.get("/layouts/{layout_id}")
async def get_layout(
    layout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get layout with all nodes"""
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    layout = db.query(TwinLayout).filter(
        TwinLayout.id == layout_id,
        TwinLayout.tenant_id == current_user.tenant_id
    ).first()
    
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    return layout.to_dict(include_nodes=True)


@router.put("/layouts/{layout_id}")
async def update_layout(
    layout_id: int,
    layout_data: TwinLayoutUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update layout configuration"""
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    layout = db.query(TwinLayout).filter(
        TwinLayout.id == layout_id,
        TwinLayout.tenant_id == current_user.tenant_id
    ).first()
    
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    if layout_data.name:
        layout.name = layout_data.name
    if layout_data.description is not None:
        layout.description = layout_data.description
    if layout_data.width:
        layout.width = layout_data.width
    if layout_data.height:
        layout.height = layout_data.height
    if layout_data.background_color:
        layout.background_color = layout_data.background_color
    if layout_data.background_image is not None:
        layout.background_image = layout_data.background_image
    if layout_data.config:
        layout.config = layout_data.config
    if layout_data.is_default is not None:
        layout.is_default = layout_data.is_default
    if layout_data.is_active is not None:
        layout.is_active = layout_data.is_active
    
    layout.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "layout": layout.to_dict()}


@router.delete("/layouts/{layout_id}")
async def delete_layout(
    layout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete layout and all nodes"""
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    layout = db.query(TwinLayout).filter(
        TwinLayout.id == layout_id,
        TwinLayout.tenant_id == current_user.tenant_id
    ).first()
    
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    db.delete(layout)
    db.commit()
    
    return {"success": True, "message": "Layout deleted"}


@router.post("/layouts/{layout_id}/nodes")
async def create_node(
    layout_id: int,
    node_data: TwinNodeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a node in a layout"""
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    layout = db.query(TwinLayout).filter(
        TwinLayout.id == layout_id,
        TwinLayout.tenant_id == current_user.tenant_id
    ).first()
    
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    if node_data.asset_id:
        asset = db.query(Asset).filter(
            Asset.id == node_data.asset_id,
            Asset.tenant_id == current_user.tenant_id
        ).first()
        if not asset:
            raise HTTPException(status_code=400, detail="Asset not found")
    
    node = TwinNode(
        tenant_id=current_user.tenant_id,
        layout_id=layout_id,
        node_type=node_data.node_type,
        label=node_data.label,
        asset_id=node_data.asset_id,
        position_x=node_data.position_x,
        position_y=node_data.position_y,
        width=node_data.width,
        height=node_data.height,
        rotation=node_data.rotation,
        icon=node_data.icon,
        color=node_data.color,
        style=node_data.style,
        parent_node_id=node_data.parent_node_id,
        data_bindings=node_data.data_bindings,
        z_index=node_data.z_index
    )
    db.add(node)
    db.commit()
    
    return {"success": True, "node": node.to_dict()}


@router.put("/nodes/{node_id}")
async def update_node(
    node_id: int,
    node_data: TwinNodeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update node properties"""
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    node = db.query(TwinNode).filter(
        TwinNode.id == node_id,
        TwinNode.tenant_id == current_user.tenant_id
    ).first()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    if node_data.label is not None:
        node.label = node_data.label
    if node_data.position_x is not None:
        node.position_x = node_data.position_x
    if node_data.position_y is not None:
        node.position_y = node_data.position_y
    if node_data.width:
        node.width = node_data.width
    if node_data.height:
        node.height = node_data.height
    if node_data.rotation is not None:
        node.rotation = node_data.rotation
    if node_data.icon is not None:
        node.icon = node_data.icon
    if node_data.color:
        node.color = node_data.color
    if node_data.style:
        node.style = node_data.style
    if node_data.data_bindings:
        node.data_bindings = node_data.data_bindings
    if node_data.z_index is not None:
        node.z_index = node_data.z_index
    if node_data.is_visible is not None:
        node.is_visible = node_data.is_visible
    
    node.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "node": node.to_dict()}


@router.delete("/nodes/{node_id}")
async def delete_node(
    node_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a node"""
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    node = db.query(TwinNode).filter(
        TwinNode.id == node_id,
        TwinNode.tenant_id == current_user.tenant_id
    ).first()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    db.delete(node)
    db.commit()
    
    return {"success": True, "message": "Node deleted"}


@router.get("/layouts/{layout_id}/nodes")
async def list_layout_nodes(
    layout_id: int,
    asset_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all nodes in a layout"""
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    layout = db.query(TwinLayout).filter(
        TwinLayout.id == layout_id,
        TwinLayout.tenant_id == current_user.tenant_id
    ).first()
    
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    query = db.query(TwinNode).filter(
        TwinNode.layout_id == layout_id,
        TwinNode.tenant_id == current_user.tenant_id
    )
    
    if asset_id:
        query = query.filter(TwinNode.asset_id == asset_id)
    
    nodes = query.order_by(TwinNode.z_index.asc()).all()
    
    return {
        "nodes": [n.to_dict() for n in nodes],
        "total": len(nodes)
    }


@router.get("/summary")
async def get_twin_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Digital Twin summary with aggregated stats and asset list"""
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    assets, summary = get_twin_assets_for_tenant(db, current_user.tenant_id)
    
    return {
        "stats": {
            "total_assets": summary.total_assets,
            "live_assets": summary.live_assets,
            "disconnected": summary.disconnected,
            "critical": summary.critical,
            "warning": summary.warning,
            "normal": summary.normal
        },
        "assets": [a.dict() for a in assets]
    }


@router.get("/assets")
async def list_assets_with_status(
    site_id: Optional[int] = None,
    asset_type: Optional[str] = None,
    criticality: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get assets with health and connectivity status for Digital Twin view"""
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tenant_id = current_user.tenant_id
    if current_user.role == "platform_owner":
        tenant_id = tenant_id or 1
    
    query = db.query(Asset).filter(Asset.tenant_id == tenant_id)
    
    if site_id:
        query = query.filter(Asset.site_id == site_id)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    if criticality:
        query = query.filter(Asset.criticality == criticality)
    
    assets = query.order_by(Asset.criticality.desc(), Asset.name).all()
    
    active_integrations = db.query(TenantIntegration).filter(
        TenantIntegration.tenant_id == tenant_id,
        TenantIntegration.status == "active"
    ).count()
    
    mapped_asset_ids = set()
    mappings = db.query(ExternalSignalMapping.asset_id).filter(
        ExternalSignalMapping.tenant_id == tenant_id
    ).distinct().all()
    mapped_asset_ids = {m[0] for m in mappings if m[0]}
    
    result = []
    for asset in assets:
        ai_score = db.query(AssetAIScore).filter(
            AssetAIScore.tenant_id == tenant_id,
            AssetAIScore.asset_id == asset.id
        ).order_by(AssetAIScore.computed_at.desc()).first()
        
        site = db.query(Site).filter(Site.id == asset.site_id).first() if asset.site_id else None
        
        if asset.id in mapped_asset_ids and active_integrations > 0:
            data_status = "live"
        elif active_integrations > 0:
            data_status = "demo"
        else:
            data_status = "disconnected"
        
        health_score = ai_score.health_score if ai_score else None
        if health_score is not None:
            if health_score >= 80:
                health_status = "normal"
            elif health_score >= 50:
                health_status = "warning"
            else:
                health_status = "critical"
        else:
            health_status = "unknown"
        
        result.append({
            "id": asset.id,
            "code": asset.code,
            "name": asset.name,
            "name_ar": asset.name_ar,
            "asset_type": asset.asset_type,
            "criticality": asset.criticality,
            "status": asset.status,
            "site_id": asset.site_id,
            "site_name": site.name if site else None,
            "health_score": health_score,
            "failure_probability": ai_score.failure_probability if ai_score else None,
            "remaining_useful_life_days": ai_score.remaining_useful_life_days if ai_score else None,
            "health_status": health_status,
            "data_status": data_status,
            "is_data_connected": data_status == "live"
        })
    
    sites = db.query(Site).filter(Site.tenant_id == tenant_id).all()
    asset_types = list(set([a.asset_type for a in assets if a.asset_type]))
    
    return {
        "assets": result,
        "total": len(result),
        "filters": {
            "sites": [{"id": s.id, "name": s.name} for s in sites],
            "asset_types": asset_types,
            "criticalities": ["high", "medium", "low"]
        },
        "summary": {
            "total_assets": len(result),
            "live_data": sum(1 for a in result if a["data_status"] == "live"),
            "demo_data": sum(1 for a in result if a["data_status"] == "demo"),
            "disconnected": sum(1 for a in result if a["data_status"] == "disconnected"),
            "normal": sum(1 for a in result if a["health_status"] == "normal"),
            "warning": sum(1 for a in result if a["health_status"] == "warning"),
            "critical": sum(1 for a in result if a["health_status"] == "critical")
        }
    }


@router.get("/assets/{asset_id}")
async def get_asset_detail(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed asset information for the side panel"""
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tenant_id = current_user.tenant_id
    if current_user.role == "platform_owner":
        tenant_id = tenant_id or 1
    
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.tenant_id == tenant_id
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    site = db.query(Site).filter(Site.id == asset.site_id).first() if asset.site_id else None
    
    ai_score = db.query(AssetAIScore).filter(
        AssetAIScore.tenant_id == tenant_id,
        AssetAIScore.asset_id == asset.id
    ).order_by(AssetAIScore.computed_at.desc()).first()
    
    mappings = db.query(ExternalSignalMapping).filter(
        ExternalSignalMapping.tenant_id == tenant_id,
        ExternalSignalMapping.asset_id == asset_id
    ).all()
    
    from models.blackbox import BlackBoxIncident
    incidents = db.query(BlackBoxIncident).filter(
        BlackBoxIncident.tenant_id == tenant_id,
        BlackBoxIncident.root_asset_id == asset_id,
        BlackBoxIncident.status.in_(["open", "investigating"])
    ).order_by(BlackBoxIncident.start_time.desc()).limit(5).all()
    
    return {
        "asset": {
            "id": asset.id,
            "code": asset.code,
            "name": asset.name,
            "name_ar": asset.name_ar,
            "asset_type": asset.asset_type,
            "manufacturer": asset.manufacturer,
            "model": asset.model,
            "criticality": asset.criticality,
            "status": asset.status,
            "site_name": site.name if site else None,
            "site_code": site.code if site else None
        },
        "health": {
            "health_score": ai_score.health_score if ai_score else None,
            "failure_probability": ai_score.failure_probability if ai_score else None,
            "remaining_useful_life_days": ai_score.remaining_useful_life_days if ai_score else None,
            "anomaly_score": ai_score.anomaly_score if ai_score else None,
            "last_updated": ai_score.computed_at.isoformat() if ai_score else None
        },
        "signal_mappings": [
            {
                "id": m.id,
                "external_tag": m.external_tag,
                "internal_metric_name": m.internal_metric_name
            } for m in mappings
        ],
        "recent_incidents": [
            {
                "id": str(i.id),
                "incident_number": i.incident_number,
                "incident_type": i.incident_type,
                "severity": i.severity,
                "status": i.status
            } for i in incidents
        ]
    }
