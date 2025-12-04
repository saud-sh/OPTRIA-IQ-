from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from models.base import Base

class TenantIntegration(Base):
    __tablename__ = "tenant_integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    integration_type = Column(String(50), nullable=False)
    config = Column(JSONB, nullable=False, default={})
    status = Column(String(20), default="inactive")
    last_sync_at = Column(DateTime(timezone=True))
    last_sync_status = Column(String(20))
    last_sync_message = Column(Text)
    is_active = Column(Boolean, default=True)
    demo_stream_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        config_safe = dict(self.config) if self.config else {}
        sensitive_keys = ['password', 'api_key', 'client_secret', 'private_key', 'token', 'secret']
        for key in sensitive_keys:
            if key in config_safe:
                config_safe[key] = '***'
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "integration_type": self.integration_type,
            "config": config_safe,
            "status": self.status,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_sync_status": self.last_sync_status,
            "is_active": self.is_active,
            "demo_stream_active": self.demo_stream_active
        }

class ExternalSignalMapping(Base):
    __tablename__ = "external_signal_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    integration_id = Column(Integer, ForeignKey("tenant_integrations.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    component_id = Column(Integer, ForeignKey("asset_components.id"))
    external_tag = Column(String(255), nullable=False)
    internal_metric_name = Column(String(100), nullable=False)
    unit = Column(String(50))
    scaling_factor = Column(Numeric(15, 6), default=1.0)
    offset_value = Column(Numeric(15, 6), default=0.0)
    extra_data = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "integration_id": self.integration_id,
            "asset_id": self.asset_id,
            "component_id": self.component_id,
            "external_tag": self.external_tag,
            "internal_metric_name": self.internal_metric_name,
            "unit": self.unit,
            "scaling_factor": float(self.scaling_factor) if self.scaling_factor else 1.0,
            "offset_value": float(self.offset_value) if self.offset_value else 0.0,
            "extra_data": self.extra_data or {},
            "is_active": self.is_active
        }

class TenantIdentityProvider(Base):
    __tablename__ = "tenant_identity_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    provider_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255))
    client_id = Column(String(255))
    client_secret = Column(Text)
    issuer_url = Column(String(500))
    authority_url = Column(String(500))
    token_url = Column(String(500))
    auth_url = Column(String(500))
    jwks_url = Column(String(500))
    redirect_uri = Column(String(500))
    scopes = Column(String(500), default="openid profile email")
    domain_allowlist = Column(JSONB, default=[])
    config = Column(JSONB, nullable=False, default={})
    is_active = Column(Boolean, default=False)
    last_sync_at = Column(DateTime(timezone=True))
    last_sync_status = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "provider_type": self.provider_type,
            "name": self.name,
            "display_name": self.display_name,
            "client_id": self.client_id,
            "client_secret": "***" if self.client_secret else None,
            "issuer_url": self.issuer_url,
            "authority_url": self.authority_url,
            "redirect_uri": self.redirect_uri,
            "scopes": self.scopes,
            "domain_allowlist": self.domain_allowlist or [],
            "is_active": self.is_active,
            "last_sync_status": self.last_sync_status
        }

class TenantOnboardingProgress(Base):
    __tablename__ = "tenant_onboarding_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    steps = Column(JSONB, default={
        "tenant_profile": {"status": "pending", "completed_at": None},
        "configure_integration": {"status": "pending", "completed_at": None},
        "test_connections": {"status": "pending", "completed_at": None},
        "map_signals": {"status": "pending", "completed_at": None},
        "configure_cost_model": {"status": "pending", "completed_at": None},
        "run_first_optimization": {"status": "pending", "completed_at": None}
    })
    status = Column(String(20), default="in_progress")
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        steps = self.steps or {}
        completed_steps = sum(1 for s in steps.values() if s.get("status") == "completed")
        total_steps = len(steps)
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "steps": steps,
            "status": self.status,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress_percent": int((completed_steps / total_steps) * 100) if total_steps > 0 else 0,
            "completed_steps": completed_steps,
            "total_steps": total_steps
        }

class TenantCostModel(Base):
    __tablename__ = "tenant_cost_models"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), default="Default Cost Model")
    description = Column(Text)
    default_downtime_cost_per_hour = Column(Numeric(15, 2), default=10000)
    risk_appetite = Column(String(20), default="medium")
    cost_per_asset_family = Column(JSONB, default={
        "pump": 5000,
        "compressor": 15000,
        "valve": 2000,
        "motor": 8000,
        "turbine": 25000,
        "heat_exchanger": 10000
    })
    production_value_per_unit = Column(Numeric(15, 2))
    production_value_per_site = Column(JSONB, default={})
    criticality_thresholds = Column(JSONB, default={
        "critical": 90,
        "high": 70,
        "medium": 50,
        "low": 30
    })
    currency = Column(String(10), default="SAR")
    valid_from = Column(DateTime(timezone=True))
    valid_to = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "default_downtime_cost_per_hour": float(self.default_downtime_cost_per_hour) if self.default_downtime_cost_per_hour else 10000,
            "risk_appetite": self.risk_appetite,
            "cost_per_asset_family": self.cost_per_asset_family or {},
            "production_value_per_unit": float(self.production_value_per_unit) if self.production_value_per_unit else None,
            "production_value_per_site": self.production_value_per_site or {},
            "criticality_thresholds": self.criticality_thresholds or {},
            "currency": self.currency,
            "is_active": self.is_active
        }

class IntegrationActionLog(Base):
    __tablename__ = "integration_action_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    integration_id = Column(Integer, ForeignKey("tenant_integrations.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    message = Column(Text)
    details = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "integration_id": self.integration_id,
            "action": self.action,
            "status": self.status,
            "message": self.message,
            "details": self.details or {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50))
    entity_id = Column(Integer)
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
