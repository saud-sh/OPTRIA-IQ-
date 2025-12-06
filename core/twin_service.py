"""
Digital Twin Service - Asset Status Aggregation and Live Data
Provides structured asset views with health, connectivity, and incident status
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from models.asset import Asset, Site, AssetAIScore
from models.integration import TenantIntegration, ExternalSignalMapping
from models.blackbox import BlackBoxIncident


class TwinAssetView(BaseModel):
    """Structured asset view for Digital Twin with live status"""
    id: int
    name: str
    asset_code: Optional[str] = None
    asset_type: Optional[str] = None
    site_name: Optional[str] = None
    criticality: Optional[str] = None
    health: Optional[float] = None
    failure_probability: Optional[float] = None
    risk_index: Optional[float] = None
    status: str  # "disconnected", "live", "warning", "critical", "normal"
    data_sources: Dict[str, bool]  # {"opcua": True, "pi": False, "external_sql": True}
    last_updated: Optional[datetime] = None
    live_values: Dict[str, Any] = {}
    has_open_incident: bool = False
    open_incident_id: Optional[int] = None

    class Config:
        from_attributes = True


class TwinSummary(BaseModel):
    """Summary statistics for Digital Twin"""
    total_assets: int
    live_assets: int
    disconnected: int
    critical: int
    warning: int
    normal: int


def check_connector_availability(db: Session, tenant_id: int) -> Dict[str, bool]:
    """Check which data source connectors are configured and available for this tenant"""
    from config import settings
    
    available = {
        "opcua": False,
        "pi": False,
        "external_sql": False,
        "demo": settings.demo_mode
    }
    
    # Check for active integrations
    integrations = db.query(TenantIntegration).filter(
        TenantIntegration.tenant_id == tenant_id,
        TenantIntegration.status == "active"
    ).all()
    
    for integration in integrations:
        if integration.integration_type == "opcua":
            available["opcua"] = True
        elif integration.integration_type in ["pi", "pi_webapi"]:
            available["pi"] = True
        elif integration.integration_type == "external_sql":
            available["external_sql"] = True
    
    return available


def get_twin_assets_for_tenant(db: Session, tenant_id: int) -> tuple[List[TwinAssetView], TwinSummary]:
    """
    Get all assets with aggregated status data for a tenant.
    Returns list of TwinAssetView and summary statistics.
    """
    # Query all assets for tenant
    assets = db.query(Asset).filter(
        Asset.tenant_id == tenant_id
    ).order_by(Asset.criticality.desc(), Asset.name).all()
    
    if not assets:
        return [], TwinSummary(
            total_assets=0,
            live_assets=0,
            disconnected=0,
            critical=0,
            warning=0,
            normal=0
        )
    
    # Check connector availability
    connector_availability = check_connector_availability(db, tenant_id)
    
    # Build asset views
    asset_views: List[TwinAssetView] = []
    stats = {
        "total": 0,
        "live": 0,
        "disconnected": 0,
        "critical": 0,
        "warning": 0,
        "normal": 0
    }
    
    for asset in assets:
        # Get latest AI score
        ai_score = db.query(AssetAIScore).filter(
            AssetAIScore.tenant_id == tenant_id,
            AssetAIScore.asset_id == asset.id
        ).order_by(AssetAIScore.computed_at.desc()).first()
        
        # Get site info
        site = db.query(Site).filter(Site.id == asset.site_id).first() if asset.site_id else None
        
        # Check signal mappings for this asset
        mappings = db.query(ExternalSignalMapping).filter(
            ExternalSignalMapping.tenant_id == tenant_id,
            ExternalSignalMapping.asset_id == asset.id
        ).all()
        
        has_mappings = len(mappings) > 0
        
        # Determine data source connectivity
        data_sources = {
            "opcua": connector_availability["opcua"] and has_mappings,
            "pi": connector_availability["pi"] and has_mappings,
            "external_sql": connector_availability["external_sql"] and has_mappings,
            "demo": connector_availability["demo"]
        }
        
        any_live = any(data_sources.values())
        data_status = "live" if (data_sources["opcua"] or data_sources["pi"] or data_sources["external_sql"]) else ("demo" if data_sources["demo"] else "disconnected")
        
        # Determine health status
        health_score = ai_score.health_score if ai_score else None
        failure_prob = ai_score.failure_probability if ai_score else None
        
        if health_score is not None:
            if health_score >= 80:
                health_status = "normal"
            elif health_score >= 50:
                health_status = "warning"
            else:
                health_status = "critical"
        else:
            health_status = "unknown"
        
        # Check for open BlackBox incidents
        open_incident = db.query(BlackBoxIncident).filter(
            BlackBoxIncident.tenant_id == tenant_id,
            BlackBoxIncident.asset_id == asset.id,
            BlackBoxIncident.status.in_(["open", "investigating"])
        ).order_by(BlackBoxIncident.start_time.desc()).first()
        
        # Overall status (priority: open_incident > critical > warning > normal > disconnected)
        if open_incident:
            overall_status = "critical"
            has_incident = True
            incident_id = open_incident.id
        elif health_status == "critical":
            overall_status = "critical"
            has_incident = False
            incident_id = None
        elif health_status == "warning":
            overall_status = "warning"
            has_incident = False
            incident_id = None
        elif health_status == "normal":
            overall_status = "normal"
            has_incident = False
            incident_id = None
        else:
            overall_status = data_status if any_live else "disconnected"
            has_incident = False
            incident_id = None
        
        # Create asset view
        asset_view = TwinAssetView(
            id=asset.id,
            name=asset.name,
            asset_code=asset.code,
            asset_type=asset.asset_type,
            site_name=site.name if site else None,
            criticality=asset.criticality,
            health=health_score,
            failure_probability=failure_prob,
            risk_index=health_score,  # Use health score as risk proxy
            status=overall_status,
            data_sources=data_sources,
            last_updated=ai_score.computed_at if ai_score else None,
            live_values={},  # Populated by connectors if available
            has_open_incident=has_incident,
            open_incident_id=incident_id
        )
        
        asset_views.append(asset_view)
        
        # Update stats
        stats["total"] += 1
        if any_live:
            stats["live"] += 1
        else:
            stats["disconnected"] += 1
        
        if health_status == "critical":
            stats["critical"] += 1
        elif health_status == "warning":
            stats["warning"] += 1
        elif health_status == "normal":
            stats["normal"] += 1
    
    summary = TwinSummary(
        total_assets=stats["total"],
        live_assets=stats["live"],
        disconnected=stats["disconnected"],
        critical=stats["critical"],
        warning=stats["warning"],
        normal=stats["normal"]
    )
    
    return asset_views, summary
