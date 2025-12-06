"""
Black Box API Router
Industrial incident recording, timeline replay, and root cause analysis.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from pydantic import BaseModel

from models.base import get_db
from models.user import User
from models.blackbox import (
    BlackBoxEvent, BlackBoxIncident, BlackBoxIncidentEvent, BlackBoxRCARule,
    SEVERITY_LEVELS, INCIDENT_TYPES, INCIDENT_STATUSES, EVENT_ROLES
)
from core.auth import get_current_user
from core.rbac import has_capability, require_tenant_access
from core.blackbox_engine import EventCollector, IncidentEngine, RCAEngine, run_blackbox_pipeline

router = APIRouter(prefix="/api/blackbox", tags=["blackbox"])


class EventCreate(BaseModel):
    asset_id: Optional[int] = None
    site_id: Optional[int] = None
    source_system: str
    source_type: str
    source_id: Optional[str] = None
    event_time: datetime
    severity: str = "INFO"
    event_category: str
    summary: Optional[str] = None
    payload: Optional[dict] = {}
    tags: Optional[List[str]] = []


class IncidentCreate(BaseModel):
    incident_type: str = "FAILURE"
    severity: str = "MAJOR"
    title: str
    description: Optional[str] = None
    root_asset_id: Optional[int] = None
    site_id: Optional[int] = None
    start_time: datetime
    end_time: Optional[datetime] = None


class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    impact_estimate: Optional[dict] = None


class IncidentEventLink(BaseModel):
    event_id: str
    role: str = "UNKNOWN"
    notes: Optional[str] = None


@router.get("/events")
async def list_events(
    asset_id: Optional[int] = None,
    site_id: Optional[int] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    source_system: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List Black Box events with filters"""
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(BlackBoxEvent).filter(
        BlackBoxEvent.tenant_id == current_user.tenant_id
    )
    
    if asset_id:
        query = query.filter(BlackBoxEvent.asset_id == asset_id)
    if site_id:
        query = query.filter(BlackBoxEvent.site_id == site_id)
    if severity:
        query = query.filter(BlackBoxEvent.severity == severity)
    if category:
        query = query.filter(BlackBoxEvent.event_category == category)
    if source_system:
        query = query.filter(BlackBoxEvent.source_system == source_system)
    if start_time:
        query = query.filter(BlackBoxEvent.event_time >= start_time)
    if end_time:
        query = query.filter(BlackBoxEvent.event_time <= end_time)
    
    total = query.count()
    events = query.order_by(BlackBoxEvent.event_time.desc()).offset(offset).limit(limit).all()
    
    return {
        "events": [e.to_dict() for e in events],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/events")
async def create_event(
    event_data: EventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a manual Black Box event"""
    if not has_capability(current_user, "run_optimization"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    from models.asset import Asset, Site
    
    if event_data.asset_id:
        asset = db.query(Asset).filter(
            Asset.id == event_data.asset_id,
            Asset.tenant_id == current_user.tenant_id
        ).first()
        if not asset:
            raise HTTPException(status_code=400, detail="Asset not found or does not belong to your organization")
    
    if event_data.site_id:
        site = db.query(Site).filter(
            Site.id == event_data.site_id,
            Site.tenant_id == current_user.tenant_id
        ).first()
        if not site:
            raise HTTPException(status_code=400, detail="Site not found or does not belong to your organization")
    
    event = BlackBoxEvent(
        tenant_id=current_user.tenant_id,
        asset_id=event_data.asset_id,
        site_id=event_data.site_id,
        source_system=event_data.source_system,
        source_type=event_data.source_type,
        source_id=event_data.source_id,
        event_time=event_data.event_time,
        severity=event_data.severity,
        event_category=event_data.event_category,
        summary=event_data.summary,
        payload=event_data.payload,
        tags=event_data.tags
    )
    db.add(event)
    db.commit()
    
    return {"success": True, "event": event.to_dict()}


@router.get("/events/{event_id}")
async def get_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single event by ID"""
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    event = db.query(BlackBoxEvent).filter(
        BlackBoxEvent.id == event_id,
        BlackBoxEvent.tenant_id == current_user.tenant_id
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return event.to_dict()


@router.get("/incidents")
async def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    incident_type: Optional[str] = None,
    site_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List incidents with filters"""
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(BlackBoxIncident).filter(
        BlackBoxIncident.tenant_id == current_user.tenant_id
    )
    
    if status:
        query = query.filter(BlackBoxIncident.status == status)
    if severity:
        query = query.filter(BlackBoxIncident.severity == severity)
    if incident_type:
        query = query.filter(BlackBoxIncident.incident_type == incident_type)
    if site_id:
        query = query.filter(BlackBoxIncident.site_id == site_id)
    if asset_id:
        query = query.filter(BlackBoxIncident.root_asset_id == asset_id)
    if start_date:
        query = query.filter(BlackBoxIncident.start_time >= start_date)
    if end_date:
        query = query.filter(BlackBoxIncident.start_time <= end_date)
    
    total = query.count()
    incidents = query.order_by(BlackBoxIncident.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "incidents": [i.to_dict() for i in incidents],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/incidents")
async def create_incident(
    incident_data: IncidentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a manual incident"""
    if not has_capability(current_user, "run_optimization"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    from models.asset import Asset, Site
    
    if incident_data.root_asset_id:
        asset = db.query(Asset).filter(
            Asset.id == incident_data.root_asset_id,
            Asset.tenant_id == current_user.tenant_id
        ).first()
        if not asset:
            raise HTTPException(status_code=400, detail="Asset not found or does not belong to your organization")
    
    if incident_data.site_id:
        site = db.query(Site).filter(
            Site.id == incident_data.site_id,
            Site.tenant_id == current_user.tenant_id
        ).first()
        if not site:
            raise HTTPException(status_code=400, detail="Site not found or does not belong to your organization")
    
    incident = BlackBoxIncident(
        tenant_id=current_user.tenant_id,
        incident_type=incident_data.incident_type,
        severity=incident_data.severity,
        title=incident_data.title,
        description=incident_data.description,
        root_asset_id=incident_data.root_asset_id,
        site_id=incident_data.site_id,
        start_time=incident_data.start_time,
        end_time=incident_data.end_time,
        status="OPEN"
    )
    db.add(incident)
    db.flush()
    incident.generate_incident_number(db)
    db.commit()
    
    return {"success": True, "incident": incident.to_dict()}


@router.get("/incidents/{incident_id}")
async def get_incident(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get incident details with events"""
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    incident = db.query(BlackBoxIncident).filter(
        BlackBoxIncident.id == incident_id,
        BlackBoxIncident.tenant_id == current_user.tenant_id
    ).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    result = incident.to_dict()
    
    incident_events = db.query(BlackBoxIncidentEvent).filter(
        BlackBoxIncidentEvent.incident_id == incident_id
    ).order_by(BlackBoxIncidentEvent.sequence_order.asc()).all()
    
    events_with_details = []
    for ie in incident_events:
        event = db.query(BlackBoxEvent).filter(BlackBoxEvent.id == ie.event_id).first()
        if event:
            event_data = event.to_dict()
            event_data["role"] = ie.role
            event_data["sequence_order"] = ie.sequence_order
            event_data["notes"] = ie.notes
            events_with_details.append(event_data)
    
    result["events"] = events_with_details
    result["event_count"] = len(events_with_details)
    
    if incident.root_asset_id:
        from models.asset import Asset
        asset = db.query(Asset).filter(Asset.id == incident.root_asset_id).first()
        if asset:
            result["root_asset_name"] = asset.name
    
    if incident.site_id:
        from models.asset import Site
        site = db.query(Site).filter(Site.id == incident.site_id).first()
        if site:
            result["site_name"] = site.name
    
    return result


@router.put("/incidents/{incident_id}")
async def update_incident(
    incident_id: str,
    update_data: IncidentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an incident"""
    if not has_capability(current_user, "run_optimization"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    engine = IncidentEngine(db, current_user.tenant_id)
    incident = engine.update_incident(incident_id, update_data.dict(exclude_none=True))
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    return {"success": True, "incident": incident.to_dict()}


@router.post("/incidents/{incident_id}/events")
async def link_event_to_incident(
    incident_id: str,
    link_data: IncidentEventLink,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Link an event to an incident"""
    if not has_capability(current_user, "run_optimization"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    incident = db.query(BlackBoxIncident).filter(
        BlackBoxIncident.id == incident_id,
        BlackBoxIncident.tenant_id == current_user.tenant_id
    ).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    event = db.query(BlackBoxEvent).filter(
        BlackBoxEvent.id == link_data.event_id,
        BlackBoxEvent.tenant_id == current_user.tenant_id
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    max_seq = db.query(func.max(BlackBoxIncidentEvent.sequence_order)).filter(
        BlackBoxIncidentEvent.incident_id == incident_id
    ).scalar() or 0
    
    link = BlackBoxIncidentEvent(
        tenant_id=current_user.tenant_id,
        incident_id=incident.id,
        event_id=event.id,
        role=link_data.role,
        notes=link_data.notes,
        sequence_order=max_seq + 1,
        added_by=current_user.id
    )
    db.add(link)
    db.commit()
    
    return {"success": True, "link": link.to_dict()}


@router.get("/incidents/{incident_id}/timeline")
async def get_incident_timeline(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get timeline data for incident replay"""
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    incident = db.query(BlackBoxIncident).filter(
        BlackBoxIncident.id == incident_id,
        BlackBoxIncident.tenant_id == current_user.tenant_id
    ).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    incident_events = db.query(BlackBoxIncidentEvent).filter(
        BlackBoxIncidentEvent.incident_id == incident_id
    ).all()
    
    event_ids = [ie.event_id for ie in incident_events]
    events = db.query(BlackBoxEvent).filter(
        BlackBoxEvent.id.in_(event_ids)
    ).order_by(BlackBoxEvent.event_time.asc()).all()
    
    event_roles = {str(ie.event_id): ie.role for ie in incident_events}
    
    timeline = []
    for event in events:
        timeline.append({
            "id": str(event.id),
            "time": event.event_time.isoformat() if event.event_time else None,
            "timestamp": event.event_time.timestamp() * 1000 if event.event_time else 0,
            "category": event.event_category,
            "severity": event.severity,
            "source": event.source_system,
            "summary": event.summary,
            "role": event_roles.get(str(event.id), "UNKNOWN"),
            "asset_id": event.asset_id,
            "payload": event.payload
        })
    
    start_time = min([e["timestamp"] for e in timeline]) if timeline else 0
    end_time = max([e["timestamp"] for e in timeline]) if timeline else 0
    
    return {
        "incident_id": str(incident.id),
        "incident_number": incident.incident_number,
        "title": incident.title,
        "severity": incident.severity,
        "start_time": incident.start_time.isoformat() if incident.start_time else None,
        "end_time": incident.end_time.isoformat() if incident.end_time else None,
        "timeline": timeline,
        "timeline_start": start_time,
        "timeline_end": end_time,
        "duration_minutes": (end_time - start_time) / 60000 if end_time > start_time else 0
    }


@router.post("/incidents/{incident_id}/rca")
async def run_rca_analysis(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run root cause analysis on an incident"""
    if not has_capability(current_user, "run_optimization"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    rca_engine = RCAEngine(db, current_user.tenant_id)
    result = rca_engine.analyze_incident(incident_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return {"success": True, "rca_summary": result}


@router.get("/reports/{incident_id}")
async def get_incident_report(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate Black Box incident report"""
    if not has_capability(current_user, "view_optimization"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    incident = db.query(BlackBoxIncident).filter(
        BlackBoxIncident.id == incident_id,
        BlackBoxIncident.tenant_id == current_user.tenant_id
    ).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    incident_events = db.query(BlackBoxIncidentEvent).filter(
        BlackBoxIncidentEvent.incident_id == incident_id
    ).order_by(BlackBoxIncidentEvent.sequence_order.asc()).all()
    
    events = []
    for ie in incident_events:
        event = db.query(BlackBoxEvent).filter(BlackBoxEvent.id == ie.event_id).first()
        if event:
            events.append({
                "event": event.to_dict(),
                "role": ie.role,
                "sequence": ie.sequence_order
            })
    
    from models.tenant import Tenant
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    
    asset_name = None
    site_name = None
    if incident.root_asset_id:
        from models.asset import Asset
        asset = db.query(Asset).filter(Asset.id == incident.root_asset_id).first()
        asset_name = asset.name if asset else None
    
    if incident.site_id:
        from models.asset import Site
        site = db.query(Site).filter(Site.id == incident.site_id).first()
        site_name = site.name if site else None
    
    report = {
        "report_type": "BLACK_BOX_INCIDENT",
        "generated_at": datetime.utcnow().isoformat(),
        "generated_by": current_user.email,
        
        "header": {
            "tenant_name": tenant.name if tenant else "Unknown",
            "incident_number": incident.incident_number,
            "incident_type": incident.incident_type,
            "severity": incident.severity,
            "status": incident.status,
            "site_name": site_name,
            "asset_name": asset_name,
            "start_time": incident.start_time.isoformat() if incident.start_time else None,
            "end_time": incident.end_time.isoformat() if incident.end_time else None
        },
        
        "executive_summary": {
            "title": incident.title,
            "description": incident.description,
            "root_cause_category": incident.rca_summary.get("root_cause_category", "PENDING") if incident.rca_summary else "PENDING",
            "confidence": incident.rca_summary.get("confidence", 0) if incident.rca_summary else 0,
            "total_events": len(events),
            "impact_estimate": incident.impact_estimate or {}
        },
        
        "timeline_overview": [
            {
                "time": e["event"]["event_time"],
                "summary": e["event"]["summary"],
                "severity": e["event"]["severity"],
                "role": e["role"]
            }
            for e in events[:20]
        ],
        
        "rca_section": incident.rca_summary or {
            "status": "PENDING",
            "message": "Root cause analysis has not been performed yet"
        },
        
        "impact_section": {
            "scope": incident.impact_scope,
            "estimate": incident.impact_estimate,
            "affected_assets": len(incident.impact_scope.get("assets", [])) if incident.impact_scope else 0
        },
        
        "recommendations": _generate_recommendations(incident)
    }
    
    return report


def _generate_recommendations(incident: BlackBoxIncident) -> List[dict]:
    """Generate recommendations based on incident analysis"""
    recommendations = []
    
    rca_category = incident.rca_summary.get("root_cause_category", "") if incident.rca_summary else ""
    
    if rca_category == "MAINTENANCE_INDUCED":
        recommendations.append({
            "priority": "HIGH",
            "category": "PROCESS",
            "title": "Review Maintenance Procedures",
            "description": "This incident may have been caused by recent maintenance work. Review procedures and quality checks."
        })
    elif rca_category == "MECHANICAL_STRESS":
        recommendations.append({
            "priority": "HIGH",
            "category": "ENGINEERING",
            "title": "Mechanical Inspection Required",
            "description": "Conduct detailed mechanical inspection of affected equipment to identify stress points."
        })
    elif rca_category == "PROCESS_UPSET":
        recommendations.append({
            "priority": "MEDIUM",
            "category": "OPERATIONS",
            "title": "Review Operating Parameters",
            "description": "Review operating parameters and setpoints to prevent future process upsets."
        })
    
    recommendations.append({
        "priority": "MEDIUM",
        "category": "MONITORING",
        "title": "Enhanced Monitoring",
        "description": "Consider additional monitoring points or tighter alert thresholds for affected assets."
    })
    
    return recommendations


@router.post("/engine/collect")
async def run_event_collection(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger event collection from OPTRIA tables"""
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    collector = EventCollector(db, current_user.tenant_id)
    result = collector.run_collection(since=datetime.utcnow() - timedelta(hours=24))
    
    return {"success": True, "collection_result": result}


@router.post("/engine/detect")
async def run_incident_detection(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger incident detection"""
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    engine = IncidentEngine(db, current_user.tenant_id)
    result = engine.run_detection()
    
    return {"success": True, "detection_result": result}


@router.post("/engine/run")
async def run_full_pipeline(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run complete Black Box pipeline (collect + detect), or seed demo data in DEMO_MODE"""
    import logging
    logger = logging.getLogger(__name__)
    
    if not has_capability(current_user, "manage_integrations"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        from config import settings
        
        if settings.demo_mode:
            try:
                from main import seed_blackbox_demo_data_refresh
                seed_blackbox_demo_data_refresh(db, current_user.tenant_id)
                
                # Count incidents and events created
                incidents = db.query(BlackBoxIncident).filter(
                    BlackBoxIncident.tenant_id == current_user.tenant_id
                ).count()
                events = db.query(BlackBoxEvent).filter(
                    BlackBoxEvent.tenant_id == current_user.tenant_id
                ).count()
                
                return {
                    "status": "ok",
                    "incidents_created": incidents,
                    "events_processed": events,
                    "mode": "demo"
                }
            except Exception as e:
                logger.error(f"Black Box demo seeding error: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail={"status": "error", "message": "Black Box demo seeding failed", "reason": str(e)}
                )
        else:
            result = run_blackbox_pipeline(db, current_user.tenant_id)
            return {
                "status": "ok",
                "incidents_created": result.get("incidents_created", 0),
                "events_processed": result.get("events_processed", 0),
                "mode": "production"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Black Box engine error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": "Black Box engine failure", "reason": str(e)}
        )


@router.get("/incidents/{incident_id}/events")
async def get_incident_events(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all events for a specific incident, ordered by timestamp"""
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    incident = db.query(BlackBoxIncident).filter(
        BlackBoxIncident.id == incident_id,
        BlackBoxIncident.tenant_id == current_user.tenant_id
    ).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    incident_events = db.query(BlackBoxIncidentEvent).filter(
        BlackBoxIncidentEvent.incident_id == incident_id
    ).order_by(BlackBoxIncidentEvent.sequence_order.asc()).all()
    
    events_with_details = []
    for ie in incident_events:
        event = db.query(BlackBoxEvent).filter(BlackBoxEvent.id == ie.event_id).first()
        if event:
            event_data = event.to_dict()
            event_data["role"] = ie.role
            event_data["sequence_order"] = ie.sequence_order
            event_data["notes"] = ie.notes
            events_with_details.append(event_data)
    
    return {
        "incident_id": str(incident_id),
        "events": events_with_details,
        "total_events": len(events_with_details)
    }


@router.get("/stats")
async def get_blackbox_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Black Box statistics for dashboard"""
    if not has_capability(current_user, "view_assets"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tenant_id = current_user.tenant_id
    
    total_events = db.query(func.count(BlackBoxEvent.id)).filter(
        BlackBoxEvent.tenant_id == tenant_id
    ).scalar()
    
    events_24h = db.query(func.count(BlackBoxEvent.id)).filter(
        BlackBoxEvent.tenant_id == tenant_id,
        BlackBoxEvent.event_time >= datetime.utcnow() - timedelta(hours=24)
    ).scalar()
    
    total_incidents = db.query(func.count(BlackBoxIncident.id)).filter(
        BlackBoxIncident.tenant_id == tenant_id
    ).scalar()
    
    open_incidents = db.query(func.count(BlackBoxIncident.id)).filter(
        BlackBoxIncident.tenant_id == tenant_id,
        BlackBoxIncident.status.in_(["OPEN", "INVESTIGATING"])
    ).scalar()
    
    critical_incidents = db.query(func.count(BlackBoxIncident.id)).filter(
        BlackBoxIncident.tenant_id == tenant_id,
        BlackBoxIncident.severity == "CRITICAL",
        BlackBoxIncident.status != "CLOSED"
    ).scalar()
    
    severity_distribution = db.query(
        BlackBoxEvent.severity,
        func.count(BlackBoxEvent.id)
    ).filter(
        BlackBoxEvent.tenant_id == tenant_id,
        BlackBoxEvent.event_time >= datetime.utcnow() - timedelta(days=7)
    ).group_by(BlackBoxEvent.severity).all()
    
    return {
        "total_events": total_events,
        "events_24h": events_24h,
        "total_incidents": total_incidents,
        "open_incidents": open_incidents,
        "critical_incidents": critical_incidents,
        "severity_distribution": {s: c for s, c in severity_distribution}
    }
