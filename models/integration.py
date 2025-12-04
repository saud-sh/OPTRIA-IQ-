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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        config_safe = dict(self.config) if self.config else {}
        if 'password' in config_safe:
            config_safe['password'] = '***'
        if 'api_key' in config_safe:
            config_safe['api_key'] = '***'
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "integration_type": self.integration_type,
            "config": config_safe,
            "status": self.status,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_sync_status": self.last_sync_status,
            "is_active": self.is_active
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
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "integration_id": self.integration_id,
            "asset_id": self.asset_id,
            "external_tag": self.external_tag,
            "internal_metric_name": self.internal_metric_name,
            "unit": self.unit,
            "scaling_factor": float(self.scaling_factor) if self.scaling_factor else 1.0,
            "offset_value": float(self.offset_value) if self.offset_value else 0.0,
            "is_active": self.is_active
        }

class TenantIdentityProvider(Base):
    __tablename__ = "tenant_identity_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    provider_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    config = Column(JSONB, nullable=False, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

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
