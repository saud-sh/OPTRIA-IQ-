"""
Industrial Black Box Models
Event recording, incident management, and root cause analysis for industrial operations.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey,
    Numeric, Index, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base


class BlackBoxEvent(Base):
    """
    Canonical event record for the Industrial Black Box.
    Captures normalized events from multiple sources (OT, IT, CMMS, AI).
    """
    __tablename__ = "blackbox_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True, index=True)
    
    source_system = Column(String(50), nullable=False, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    source_id = Column(String(255), nullable=True)
    
    event_time = Column(DateTime(timezone=True), nullable=False, index=True)
    ingest_time = Column(DateTime(timezone=True), server_default=func.now())
    
    severity = Column(String(20), default="INFO", index=True)
    event_category = Column(String(50), nullable=False, index=True)
    summary = Column(String(500), nullable=True)
    payload = Column(JSONB, default={})
    tags = Column(ARRAY(String), default=[])
    
    is_processed = Column(Boolean, default=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_blackbox_events_tenant_time', 'tenant_id', 'event_time'),
        Index('ix_blackbox_events_tenant_asset', 'tenant_id', 'asset_id'),
        Index('ix_blackbox_events_tenant_severity', 'tenant_id', 'severity'),
        Index('ix_blackbox_events_tenant_category', 'tenant_id', 'event_category'),
    )
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "asset_id": self.asset_id,
            "site_id": self.site_id,
            "source_system": self.source_system,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "ingest_time": self.ingest_time.isoformat() if self.ingest_time else None,
            "severity": self.severity,
            "event_category": self.event_category,
            "summary": self.summary,
            "payload": self.payload or {},
            "tags": self.tags or [],
            "is_processed": self.is_processed
        }


class BlackBoxIncident(Base):
    """
    Industrial incident record with root cause analysis.
    Groups related events into a unified incident timeline.
    """
    __tablename__ = "blackbox_incidents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    
    incident_number = Column(String(50), nullable=True, index=True)
    incident_type = Column(String(30), nullable=False, default="FAILURE")
    status = Column(String(20), nullable=False, default="OPEN", index=True)
    severity = Column(String(20), nullable=False, default="MAJOR", index=True)
    
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    root_asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    
    impact_scope = Column(JSONB, default={})
    
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    trigger_event_id = Column(UUID(as_uuid=True), nullable=True)
    
    rca_status = Column(String(20), default="PENDING")
    rca_summary = Column(JSONB, default={})
    rca_completed_at = Column(DateTime(timezone=True), nullable=True)
    rca_completed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    impact_estimate = Column(JSONB, default={})
    
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    events = relationship("BlackBoxIncidentEvent", back_populates="incident", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_blackbox_incidents_tenant_status', 'tenant_id', 'status'),
        Index('ix_blackbox_incidents_tenant_severity', 'tenant_id', 'severity'),
        Index('ix_blackbox_incidents_tenant_time', 'tenant_id', 'start_time'),
    )
    
    def to_dict(self, include_events=False):
        result = {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "incident_number": self.incident_number,
            "incident_type": self.incident_type,
            "status": self.status,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "root_asset_id": self.root_asset_id,
            "site_id": self.site_id,
            "impact_scope": self.impact_scope or {},
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "trigger_event_id": str(self.trigger_event_id) if self.trigger_event_id else None,
            "rca_status": self.rca_status,
            "rca_summary": self.rca_summary or {},
            "rca_completed_at": self.rca_completed_at.isoformat() if self.rca_completed_at else None,
            "impact_estimate": self.impact_estimate or {},
            "assigned_to": self.assigned_to,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        if include_events and self.events:
            result["events"] = [e.to_dict() for e in self.events]
        return result
    
    def generate_incident_number(self, db):
        """Generate sequential incident number for tenant"""
        from sqlalchemy import func as sqlfunc
        count = db.query(sqlfunc.count(BlackBoxIncident.id)).filter(
            BlackBoxIncident.tenant_id == self.tenant_id
        ).scalar()
        year = datetime.utcnow().year
        self.incident_number = f"INC-{year}-{str(count + 1).zfill(5)}"


class BlackBoxIncidentEvent(Base):
    """
    Links events to incidents with role classification.
    Enables timeline reconstruction and RCA.
    """
    __tablename__ = "blackbox_incident_events"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("blackbox_incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("blackbox_events.id"), nullable=False, index=True)
    
    role = Column(String(20), default="UNKNOWN")
    sequence_order = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    
    added_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    
    incident = relationship("BlackBoxIncident", back_populates="events")
    
    __table_args__ = (
        Index('ix_blackbox_incident_events_incident', 'incident_id'),
        Index('ix_blackbox_incident_events_event', 'event_id'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "incident_id": str(self.incident_id),
            "event_id": str(self.event_id),
            "role": self.role,
            "sequence_order": self.sequence_order,
            "notes": self.notes,
            "added_by": self.added_by,
            "added_at": self.added_at.isoformat() if self.added_at else None
        }


class BlackBoxRCARule(Base):
    """
    Rule-based patterns for root cause analysis.
    Stored as JSON patterns that the RCA engine evaluates.
    """
    __tablename__ = "blackbox_rca_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    pattern = Column(JSONB, nullable=False)
    root_cause_category = Column(String(100), nullable=False)
    confidence = Column(Numeric(3, 2), default=0.5)
    
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)
    priority = Column(Integer, default=100)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "pattern": self.pattern,
            "root_cause_category": self.root_cause_category,
            "confidence": float(self.confidence) if self.confidence else 0.5,
            "is_active": self.is_active,
            "is_system": self.is_system,
            "priority": self.priority
        }


SOURCE_SYSTEMS = [
    "OPTRIA_ALERT",
    "OPTRIA_WORKORDER",
    "AI_ENGINE",
    "PI_HISTORIAN",
    "OPC_UA",
    "SCADA",
    "CMMS",
    "SAP_PM",
    "MANUAL"
]

SOURCE_TYPES = [
    "TAG_READING",
    "ALERT",
    "ALARM",
    "WORK_ORDER",
    "OPERATOR_ACTION",
    "CONFIG_CHANGE",
    "SYSTEM_EVENT",
    "AI_PREDICTION",
    "ANOMALY"
]

EVENT_CATEGORIES = [
    "SENSOR",
    "ALERT",
    "FAILURE",
    "MAINTENANCE",
    "OPERATOR_ACTION",
    "CONFIG_CHANGE",
    "SYSTEM",
    "AI_OUTPUT",
    "PROCESS"
]

SEVERITY_LEVELS = [
    "INFO",
    "WARNING",
    "MINOR",
    "MAJOR",
    "CRITICAL"
]

INCIDENT_TYPES = [
    "FAILURE",
    "NEAR_MISS",
    "ANOMALY",
    "DEGRADATION",
    "SAFETY"
]

INCIDENT_STATUSES = [
    "OPEN",
    "INVESTIGATING",
    "RESOLVED",
    "CLOSED"
]

EVENT_ROLES = [
    "CAUSE",
    "SYMPTOM",
    "CONTEXT",
    "NOISE",
    "UNKNOWN"
]

RCA_CATEGORIES = [
    "MECHANICAL_STRESS",
    "ELECTRICAL_FAILURE",
    "INSTRUMENTATION_ERROR",
    "OPERATOR_ERROR",
    "MAINTENANCE_INDUCED",
    "PROCESS_UPSET",
    "EXTERNAL_FACTOR",
    "DESIGN_DEFICIENCY",
    "MATERIAL_DEFECT",
    "UNKNOWN"
]
