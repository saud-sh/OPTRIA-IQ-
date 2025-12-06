"""
Digital Twin Configuration and Management APIs
Manage layouts, nodes, and asset bindings for industrial visualization
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from models.user import User
from models.blackbox import TwinLayout, TwinNode
from models.asset import Asset
from core.auth import get_current_user
from core.rbac import has_capability
from models.base import get_db
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
