from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from models.base import get_db
from models.user import User
from models.integration import (
    TenantIntegration, ExternalSignalMapping, AuditLog,
    TenantIdentityProvider, TenantOnboardingProgress, TenantCostModel,
    IntegrationActionLog
)
from models.asset import Asset
from core.auth import get_current_user
from core.rbac import has_capability, require_tenant_access
from core.connectors import get_connector, CONNECTOR_TYPES, CONNECTOR_SCHEMAS, SSO_PROVIDER_SCHEMAS

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

class SignalMappingUpdate(BaseModel):
    asset_id: Optional[int] = None
    component_id: Optional[int] = None
    external_tag: Optional[str] = None
    internal_metric_name: Optional[str] = None
    unit: Optional[str] = None
    scaling_factor: Optional[float] = None
    offset_value: Optional[float] = None

class BulkMappingCreate(BaseModel):
    integration_id: int
    mappings: List[Dict[str, Any]]

class IdentityProviderCreate(BaseModel):
    provider_type: str
    name: str
    display_name: Optional[str] = None
    client_id: str
    client_secret: str
    issuer_url: Optional[str] = None
    authority_url: Optional[str] = None
    tenant_id: Optional[str] = None
    scopes: str = "openid profile email"
    domain_allowlist: List[str] = []
    config: Dict[str, Any] = {}

class IdentityProviderUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    issuer_url: Optional[str] = None
    scopes: Optional[str] = None
    domain_allowlist: Optional[List[str]] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None

class CostModelCreate(BaseModel):
    name: str = "Default Cost Model"
    description: Optional[str] = None
    default_downtime_cost_per_hour: float = 10000
    risk_appetite: str = "medium"
    cost_per_asset_family: Dict[str, float] = {}
    production_value_per_unit: Optional[float] = None
    production_value_per_site: Dict[str, float] = {}
    criticality_thresholds: Dict[str, int] = {}
    currency: str = "SAR"

class CostModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_downtime_cost_per_hour: Optional[float] = None
    risk_appetite: Optional[str] = None
    cost_per_asset_family: Optional[Dict[str, float]] = None
    production_value_per_unit: Optional[float] = None
    production_value_per_site: Optional[Dict[str, float]] = None
    criticality_thresholds: Optional[Dict[str, int]] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None

class OnboardingStepUpdate(BaseModel):
    step_key: str
    status: str

@router.get("/types")
async def list_integration_types(
    current_user: User = Depends(get_current_user)
):
    types = []
    for type_name in CONNECTOR_TYPES.keys():
        schema = CONNECTOR_SCHEMAS.get(type_name, {})
        types.append({
            "type": type_name,
            "name": schema.get("name", type_name.upper()),
            "description": schema.get("description", ""),
            "fields": schema.get("fields", [])
        })
    return types

@router.get("/schemas/{integration_type}")
async def get_integration_schema(
    integration_type: str,
    current_user: User = Depends(get_current_user)
):
    if integration_type not in CONNECTOR_SCHEMAS:
        raise HTTPException(status_code=404, detail="Integration type not found")
    return CONNECTOR_SCHEMAS[integration_type]

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

@router.get("/mappings")
async def list_signal_mappings_early(
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

@router.get("/identity-providers")
async def list_identity_providers_early(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(TenantIdentityProvider)
    
    if current_user.role != "platform_owner":
        query = query.filter(TenantIdentityProvider.tenant_id == current_user.tenant_id)
    
    providers = query.all()
    return [p.to_dict() for p in providers]

@router.get("/cost-models/active")
async def get_active_cost_model_early(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    model = db.query(TenantCostModel).filter(
        TenantCostModel.tenant_id == tenant_id,
        TenantCostModel.is_active == True
    ).first()
    
    if not model:
        model = TenantCostModel(
            tenant_id=tenant_id,
            name="Default Cost Model",
            is_active=True
        )
        db.add(model)
        db.commit()
    
    return model.to_dict()

@router.get("/onboarding/progress")
async def get_onboarding_progress_early(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    progress = db.query(TenantOnboardingProgress).filter(
        TenantOnboardingProgress.tenant_id == tenant_id
    ).first()
    
    if not progress:
        progress = TenantOnboardingProgress(tenant_id=tenant_id)
        db.add(progress)
        db.commit()
        db.refresh(progress)
    
    has_integrations = db.query(TenantIntegration).filter(
        TenantIntegration.tenant_id == tenant_id,
        TenantIntegration.is_active == True
    ).first() is not None
    
    has_mappings = db.query(ExternalSignalMapping).filter(
        ExternalSignalMapping.tenant_id == tenant_id,
        ExternalSignalMapping.is_active == True
    ).first() is not None
    
    has_cost_model = db.query(TenantCostModel).filter(
        TenantCostModel.tenant_id == tenant_id,
        TenantCostModel.is_active == True
    ).first() is not None
    
    has_sso = db.query(TenantIdentityProvider).filter(
        TenantIdentityProvider.tenant_id == tenant_id,
        TenantIdentityProvider.is_active == True
    ).first() is not None
    
    steps = progress.steps or {}
    result = progress.to_dict()
    result["computed_status"] = {
        "has_integrations": has_integrations,
        "has_mappings": has_mappings,
        "has_cost_model": has_cost_model,
        "has_sso": has_sso
    }
    
    completed_steps = sum([
        steps.get("tenant_profile", {}).get("status") == "completed",
        has_integrations,
        has_mappings,
        has_cost_model,
        has_sso or steps.get("configure_sso", {}).get("status") == "skipped",
        steps.get("invite_team", {}).get("status") in ["completed", "skipped"]
    ])
    result["progress_percent"] = int((completed_steps / 6) * 100)
    
    return result

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
    result["schema"] = CONNECTOR_SCHEMAS.get(integration.integration_type, {})
    
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
        current_config = dict(integration.config) if integration.config else {}
        current_config.update(update_data.config)
        integration.config = current_config
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

@router.patch("/{integration_id}/config")
async def update_integration_config(
    integration_id: int,
    config: Dict[str, Any],
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
    
    current_config = dict(integration.config) if integration.config else {}
    current_config.update(config)
    integration.config = current_config
    integration.updated_at = datetime.utcnow()
    
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
        
        action_log = IntegrationActionLog(
            tenant_id=integration.tenant_id,
            integration_id=integration.id,
            action="test_connection",
            status="success" if success else "failed",
            message=connector.last_error if not success else "Connection successful"
        )
        db.add(action_log)
        
        db.commit()
        
        return {
            "success": success,
            "status": connector.get_status(),
            "message": "Connection successful" if success else connector.last_error
        }
    except Exception as e:
        integration.last_sync_status = "error"
        integration.last_sync_message = str(e)
        
        action_log = IntegrationActionLog(
            tenant_id=integration.tenant_id,
            integration_id=integration.id,
            action="test_connection",
            status="error",
            message=str(e)
        )
        db.add(action_log)
        db.commit()
        
        return {"success": False, "message": str(e)}

@router.post("/{integration_id}/demo-stream/start")
async def start_demo_stream(
    integration_id: int,
    background_tasks: BackgroundTasks,
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
    
    integration.demo_stream_active = True
    integration.status = "streaming"
    
    action_log = IntegrationActionLog(
        tenant_id=integration.tenant_id,
        integration_id=integration.id,
        action="start_demo_stream",
        status="success",
        message="Demo stream started"
    )
    db.add(action_log)
    db.commit()
    
    return {"success": True, "message": "Demo stream started"}

@router.post("/{integration_id}/demo-stream/stop")
async def stop_demo_stream(
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
    
    integration.demo_stream_active = False
    integration.status = "active" if integration.last_sync_status == "success" else "inactive"
    
    action_log = IntegrationActionLog(
        tenant_id=integration.tenant_id,
        integration_id=integration.id,
        action="stop_demo_stream",
        status="success",
        message="Demo stream stopped"
    )
    db.add(action_log)
    db.commit()
    
    return {"success": True, "message": "Demo stream stopped"}

@router.post("/{integration_id}/run-ai")
async def run_ai_optimization(
    integration_id: int,
    optimization_type: str = "maintenance_priority",
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "run_optimization"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    integration = db.query(TenantIntegration).filter(
        TenantIntegration.id == integration_id
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    require_tenant_access(current_user, integration.tenant_id)
    
    from core.optimization_engine import get_optimization_engine
    
    engine = get_optimization_engine(db)
    tenant_id = integration.tenant_id
    
    if optimization_type == "maintenance_priority":
        run = engine.run_maintenance_prioritization(tenant_id, current_user.id, {})
    elif optimization_type == "deferral_cost":
        run = engine.run_deferral_cost_analysis(tenant_id, current_user.id, {})
    elif optimization_type == "production_risk":
        run = engine.run_production_risk_optimization(tenant_id, current_user.id, {})
    elif optimization_type == "workforce_dispatch":
        run = engine.run_workforce_dispatch_optimization(tenant_id, current_user.id, {})
    else:
        raise HTTPException(status_code=400, detail="Invalid optimization type")
    
    action_log = IntegrationActionLog(
        tenant_id=integration.tenant_id,
        integration_id=integration.id,
        action="run_ai_optimization",
        status="success",
        message=f"Started {optimization_type} optimization",
        details={"run_id": run.id}
    )
    db.add(action_log)
    db.commit()
    
    return {"success": True, "run": run.to_dict()}

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

@router.get("/{integration_id}/action-logs")
async def get_integration_action_logs(
    integration_id: int,
    limit: int = 50,
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
    
    logs = db.query(IntegrationActionLog).filter(
        IntegrationActionLog.integration_id == integration_id
    ).order_by(IntegrationActionLog.created_at.desc()).limit(limit).all()
    
    return [log.to_dict() for log in logs]

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

@router.post("/mappings/bulk")
async def create_bulk_mappings(
    bulk_data: BulkMappingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    integration = db.query(TenantIntegration).filter(
        TenantIntegration.id == bulk_data.integration_id
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    require_tenant_access(current_user, integration.tenant_id)
    
    created = []
    for m in bulk_data.mappings:
        mapping = ExternalSignalMapping(
            tenant_id=tenant_id,
            integration_id=bulk_data.integration_id,
            asset_id=m.get("asset_id"),
            component_id=m.get("component_id"),
            external_tag=m.get("external_tag"),
            internal_metric_name=m.get("internal_metric_name"),
            unit=m.get("unit"),
            scaling_factor=m.get("scaling_factor", 1.0),
            offset_value=m.get("offset_value", 0.0)
        )
        db.add(mapping)
        created.append(mapping)
    
    db.commit()
    
    return {"success": True, "created_count": len(created), "mappings": [m.to_dict() for m in created]}

@router.put("/mappings/{mapping_id}")
async def update_signal_mapping(
    mapping_id: int,
    update_data: SignalMappingUpdate,
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
    
    if update_data.asset_id is not None:
        mapping.asset_id = update_data.asset_id
    if update_data.component_id is not None:
        mapping.component_id = update_data.component_id
    if update_data.external_tag is not None:
        mapping.external_tag = update_data.external_tag
    if update_data.internal_metric_name is not None:
        mapping.internal_metric_name = update_data.internal_metric_name
    if update_data.unit is not None:
        mapping.unit = update_data.unit
    if update_data.scaling_factor is not None:
        mapping.scaling_factor = update_data.scaling_factor
    if update_data.offset_value is not None:
        mapping.offset_value = update_data.offset_value
    
    mapping.updated_at = datetime.utcnow()
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

@router.get("/sso/providers")
async def list_sso_provider_types(
    current_user: User = Depends(get_current_user)
):
    providers = []
    for provider_type, schema in SSO_PROVIDER_SCHEMAS.items():
        providers.append({
            "type": provider_type,
            "name": schema.get("name", provider_type),
            "description": schema.get("description", ""),
            "fields": schema.get("fields", [])
        })
    return providers

@router.post("/identity-providers")
async def create_identity_provider(
    provider_data: IdentityProviderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    if provider_data.provider_type not in SSO_PROVIDER_SCHEMAS:
        raise HTTPException(status_code=400, detail=f"Invalid provider type. Valid: {list(SSO_PROVIDER_SCHEMAS.keys())}")
    
    authority = provider_data.authority_url
    if provider_data.provider_type == "azure_ad" and provider_data.tenant_id:
        authority = f"https://login.microsoftonline.com/{provider_data.tenant_id}"
    
    provider = TenantIdentityProvider(
        tenant_id=tenant_id,
        provider_type=provider_data.provider_type,
        name=provider_data.name,
        display_name=provider_data.display_name or provider_data.name,
        client_id=provider_data.client_id,
        client_secret=provider_data.client_secret,
        issuer_url=provider_data.issuer_url,
        authority_url=authority,
        scopes=provider_data.scopes,
        domain_allowlist=provider_data.domain_allowlist,
        config=provider_data.config,
        is_active=False
    )
    db.add(provider)
    db.commit()
    
    return {"success": True, "provider": provider.to_dict()}

@router.put("/identity-providers/{provider_id}")
async def update_identity_provider(
    provider_id: int,
    update_data: IdentityProviderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    provider = db.query(TenantIdentityProvider).filter(
        TenantIdentityProvider.id == provider_id
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Identity provider not found")
    
    require_tenant_access(current_user, provider.tenant_id)
    
    if update_data.name is not None:
        provider.name = update_data.name
    if update_data.display_name is not None:
        provider.display_name = update_data.display_name
    if update_data.client_id is not None:
        provider.client_id = update_data.client_id
    if update_data.client_secret is not None:
        provider.client_secret = update_data.client_secret
    if update_data.issuer_url is not None:
        provider.issuer_url = update_data.issuer_url
    if update_data.scopes is not None:
        provider.scopes = update_data.scopes
    if update_data.domain_allowlist is not None:
        provider.domain_allowlist = update_data.domain_allowlist
    if update_data.is_active is not None:
        provider.is_active = update_data.is_active
    if update_data.config is not None:
        provider.config = update_data.config
    
    provider.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "provider": provider.to_dict()}

@router.post("/identity-providers/{provider_id}/test")
async def test_identity_provider(
    provider_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    provider = db.query(TenantIdentityProvider).filter(
        TenantIdentityProvider.id == provider_id
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Identity provider not found")
    
    require_tenant_access(current_user, provider.tenant_id)
    
    import httpx
    
    try:
        discovery_url = None
        if provider.provider_type == "azure_ad":
            discovery_url = f"{provider.authority_url}/.well-known/openid-configuration"
        elif provider.provider_type == "okta":
            discovery_url = f"{provider.issuer_url}/.well-known/openid-configuration"
        elif provider.provider_type == "google":
            discovery_url = "https://accounts.google.com/.well-known/openid-configuration"
        
        if discovery_url:
            async with httpx.AsyncClient() as client:
                response = await client.get(discovery_url, timeout=10)
                if response.status_code == 200:
                    provider.last_sync_status = "success"
                    provider.last_sync_at = datetime.utcnow()
                    db.commit()
                    return {"success": True, "message": "OpenID configuration retrieved successfully"}
                else:
                    provider.last_sync_status = "failed"
                    db.commit()
                    return {"success": False, "message": f"Failed to retrieve OpenID configuration: {response.status_code}"}
        
        return {"success": False, "message": "No discovery URL available for this provider type"}
    except Exception as e:
        provider.last_sync_status = "error"
        db.commit()
        return {"success": False, "message": str(e)}

@router.delete("/identity-providers/{provider_id}")
async def delete_identity_provider(
    provider_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    provider = db.query(TenantIdentityProvider).filter(
        TenantIdentityProvider.id == provider_id
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Identity provider not found")
    
    require_tenant_access(current_user, provider.tenant_id)
    
    provider.is_active = False
    db.commit()
    
    return {"success": True}

@router.get("/cost-models")
async def list_cost_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "view_optimization"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(TenantCostModel)
    
    if current_user.role != "platform_owner":
        query = query.filter(TenantCostModel.tenant_id == current_user.tenant_id)
    
    models = query.all()
    return [m.to_dict() for m in models]

@router.post("/cost-models")
async def create_cost_model(
    model_data: CostModelCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_cost_models"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    model = TenantCostModel(
        tenant_id=tenant_id,
        name=model_data.name,
        description=model_data.description,
        default_downtime_cost_per_hour=model_data.default_downtime_cost_per_hour,
        risk_appetite=model_data.risk_appetite,
        cost_per_asset_family=model_data.cost_per_asset_family,
        production_value_per_unit=model_data.production_value_per_unit,
        production_value_per_site=model_data.production_value_per_site,
        criticality_thresholds=model_data.criticality_thresholds,
        currency=model_data.currency,
        is_active=True
    )
    db.add(model)
    db.commit()
    
    return {"success": True, "cost_model": model.to_dict()}

@router.put("/cost-models/{model_id}")
async def update_cost_model(
    model_id: int,
    update_data: CostModelUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_cost_models"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    model = db.query(TenantCostModel).filter(
        TenantCostModel.id == model_id
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail="Cost model not found")
    
    require_tenant_access(current_user, model.tenant_id)
    
    if update_data.name is not None:
        model.name = update_data.name
    if update_data.description is not None:
        model.description = update_data.description
    if update_data.default_downtime_cost_per_hour is not None:
        model.default_downtime_cost_per_hour = update_data.default_downtime_cost_per_hour
    if update_data.risk_appetite is not None:
        model.risk_appetite = update_data.risk_appetite
    if update_data.cost_per_asset_family is not None:
        model.cost_per_asset_family = update_data.cost_per_asset_family
    if update_data.production_value_per_unit is not None:
        model.production_value_per_unit = update_data.production_value_per_unit
    if update_data.production_value_per_site is not None:
        model.production_value_per_site = update_data.production_value_per_site
    if update_data.criticality_thresholds is not None:
        model.criticality_thresholds = update_data.criticality_thresholds
    if update_data.currency is not None:
        model.currency = update_data.currency
    if update_data.is_active is not None:
        model.is_active = update_data.is_active
    
    model.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "cost_model": model.to_dict()}

@router.put("/onboarding/progress")
async def update_onboarding_progress(
    step_update: OnboardingStepUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ["tenant_admin", "platform_owner"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    progress = db.query(TenantOnboardingProgress).filter(
        TenantOnboardingProgress.tenant_id == tenant_id
    ).first()
    
    if not progress:
        progress = TenantOnboardingProgress(tenant_id=tenant_id)
        db.add(progress)
    
    steps = dict(progress.steps) if progress.steps else {}
    
    if step_update.step_key in steps:
        steps[step_update.step_key] = {
            "status": step_update.status,
            "completed_at": datetime.utcnow().isoformat() if step_update.status == "completed" else None
        }
        progress.steps = steps
        
        all_completed = all(s.get("status") == "completed" for s in steps.values())
        if all_completed:
            progress.status = "completed"
            progress.completed_at = datetime.utcnow()
    
    progress.updated_at = datetime.utcnow()
    db.commit()
    
    return progress.to_dict()

@router.get("/external-db/test-sample")
async def test_external_db_sample(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Test external SQL database connection using EXTERNAL_SQL_URL.
    Platform owner only - tests the global default connection.
    """
    if current_user.role != "platform_owner":
        raise HTTPException(status_code=403, detail="Only platform owners can test external database connections")
    
    try:
        from core.connectors.sql import SQLConnector
        from config import settings
        
        if not settings.external_sql_url:
            return {
                "success": False,
                "message": "EXTERNAL_SQL_URL is not configured",
                "details": {
                    "db_type": "postgresql",
                    "used_global_default": False
                }
            }
        
        # Create a connector with the global default URL
        connector = SQLConnector({
            "connection_string": settings.external_sql_url,
            "database_type": "postgresql"
        })
        
        # Run the test query
        success, message, details = connector.test_sample_query()
        
        return {
            "success": success,
            "message": message,
            "details": details
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error testing external database: {str(e)}",
            "details": {
                "db_type": "postgresql",
                "used_global_default": False
            }
        }
