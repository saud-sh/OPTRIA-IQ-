from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from models.base import get_db
from models.user import User
from models.integration import TenantIntegration, ExternalSignalMapping, AuditLog
from models.asset import Asset
from core.auth import get_current_user
from core.rbac import has_capability, require_tenant_access
from core.connectors import get_connector, CONNECTOR_TYPES

router = APIRouter(prefix="/api/integrations", tags=["Integrations"])

class IntegrationCreate(BaseModel):
    name: str
    integration_type: str
    config: Dict[str, Any] = {}

class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class SignalMappingCreate(BaseModel):
    integration_id: int
    asset_id: Optional[int] = None
    component_id: Optional[int] = None
    external_tag: str
    internal_metric_name: str
    unit: Optional[str] = None
    scaling_factor: float = 1.0
    offset_value: float = 0.0

@router.get("/types")
async def list_integration_types(
    current_user: User = Depends(get_current_user)
):
    types = []
    for type_name, connector_class in CONNECTOR_TYPES.items():
        types.append({
            "type": type_name,
            "name": type_name.upper(),
            "config_schema": connector_class.get_config_schema()
        })
    return types

@router.get("/")
async def list_integrations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations") and not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(TenantIntegration)
    
    if current_user.role != "platform_owner":
        query = query.filter(TenantIntegration.tenant_id == current_user.tenant_id)
    
    integrations = query.all()
    return [i.to_dict() for i in integrations]

@router.get("/{integration_id}")
async def get_integration(
    integration_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    integration = db.query(TenantIntegration).filter(
        TenantIntegration.id == integration_id
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    require_tenant_access(current_user, integration.tenant_id)
    
    result = integration.to_dict()
    
    mappings = db.query(ExternalSignalMapping).filter(
        ExternalSignalMapping.integration_id == integration_id,
        ExternalSignalMapping.is_active == True
    ).all()
    result["mappings"] = [m.to_dict() for m in mappings]
    
    return result

@router.post("/")
async def create_integration(
    request: Request,
    integration_data: IntegrationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    if integration_data.integration_type not in CONNECTOR_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid integration type. Valid: {list(CONNECTOR_TYPES.keys())}")
    
    integration = TenantIntegration(
        tenant_id=tenant_id,
        name=integration_data.name,
        integration_type=integration_data.integration_type,
        config=integration_data.config,
        status="inactive"
    )
    db.add(integration)
    db.flush()
    
    audit_log = AuditLog(
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="create_integration",
        entity_type="integration",
        entity_id=integration.id,
        new_values={"name": integration.name, "type": integration.integration_type},
        ip_address=request.client.host if request.client else None
    )
    db.add(audit_log)
    
    db.commit()
    
    return {"success": True, "integration": integration.to_dict()}

@router.put("/{integration_id}")
async def update_integration(
    request: Request,
    integration_id: int,
    update_data: IntegrationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    integration = db.query(TenantIntegration).filter(
        TenantIntegration.id == integration_id
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    require_tenant_access(current_user, integration.tenant_id)
    
    old_values = integration.to_dict()
    
    if update_data.name is not None:
        integration.name = update_data.name
    if update_data.config is not None:
        integration.config = update_data.config
    if update_data.is_active is not None:
        integration.is_active = update_data.is_active
    
    integration.updated_at = datetime.utcnow()
    
    audit_log = AuditLog(
        tenant_id=integration.tenant_id,
        user_id=current_user.id,
        action="update_integration",
        entity_type="integration",
        entity_id=integration.id,
        old_values=old_values,
        new_values=integration.to_dict(),
        ip_address=request.client.host if request.client else None
    )
    db.add(audit_log)
    
    db.commit()
    
    return {"success": True, "integration": integration.to_dict()}

@router.post("/{integration_id}/test")
async def test_integration(
    integration_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    integration = db.query(TenantIntegration).filter(
        TenantIntegration.id == integration_id
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    require_tenant_access(current_user, integration.tenant_id)
    
    try:
        connector = get_connector(integration.integration_type, integration.config)
        success = connector.test_connection()
        
        integration.last_sync_at = datetime.utcnow()
        integration.last_sync_status = "success" if success else "failed"
        integration.last_sync_message = None if success else connector.last_error
        
        if success:
            integration.status = "active"
        
        db.commit()
        
        return {
            "success": success,
            "status": connector.get_status(),
            "message": "Connection successful" if success else connector.last_error
        }
    except Exception as e:
        integration.last_sync_status = "error"
        integration.last_sync_message = str(e)
        db.commit()
        
        return {"success": False, "message": str(e)}

@router.get("/{integration_id}/available-tags")
async def get_available_tags(
    integration_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    integration = db.query(TenantIntegration).filter(
        TenantIntegration.id == integration_id
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    require_tenant_access(current_user, integration.tenant_id)
    
    try:
        connector = get_connector(integration.integration_type, integration.config)
        tags = connector.get_available_tags()
        return {"tags": tags}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/mappings")
async def list_signal_mappings(
    integration_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(ExternalSignalMapping).filter(ExternalSignalMapping.is_active == True)
    
    if current_user.role != "platform_owner":
        query = query.filter(ExternalSignalMapping.tenant_id == current_user.tenant_id)
    
    if integration_id:
        query = query.filter(ExternalSignalMapping.integration_id == integration_id)
    if asset_id:
        query = query.filter(ExternalSignalMapping.asset_id == asset_id)
    
    mappings = query.all()
    return [m.to_dict() for m in mappings]

@router.post("/mappings")
async def create_signal_mapping(
    mapping_data: SignalMappingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    integration = db.query(TenantIntegration).filter(
        TenantIntegration.id == mapping_data.integration_id
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    require_tenant_access(current_user, integration.tenant_id)
    
    if mapping_data.asset_id:
        asset = db.query(Asset).filter(Asset.id == mapping_data.asset_id).first()
        if not asset or asset.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Asset not found")
    
    mapping = ExternalSignalMapping(
        tenant_id=tenant_id,
        integration_id=mapping_data.integration_id,
        asset_id=mapping_data.asset_id,
        component_id=mapping_data.component_id,
        external_tag=mapping_data.external_tag,
        internal_metric_name=mapping_data.internal_metric_name,
        unit=mapping_data.unit,
        scaling_factor=mapping_data.scaling_factor,
        offset_value=mapping_data.offset_value
    )
    db.add(mapping)
    db.commit()
    
    return {"success": True, "mapping": mapping.to_dict()}

@router.delete("/mappings/{mapping_id}")
async def delete_signal_mapping(
    mapping_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    mapping = db.query(ExternalSignalMapping).filter(
        ExternalSignalMapping.id == mapping_id
    ).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    require_tenant_access(current_user, mapping.tenant_id)
    
    mapping.is_active = False
    db.commit()
    
    return {"success": True}
