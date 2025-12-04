from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric, Date, Text, Computed
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from models.base import Base

class Site(Base):
    __tablename__ = "sites"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    location = Column(String(255))
    site_type = Column(String(50))
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "code": self.code,
            "name": self.name,
            "name_ar": self.name_ar,
            "location": self.location,
            "site_type": self.site_type,
            "is_active": self.is_active
        }

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), index=True)
    parent_asset_id = Column(Integer, ForeignKey("assets.id"))
    code = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    asset_type = Column(String(100))
    manufacturer = Column(String(255))
    model = Column(String(255))
    serial_number = Column(String(255))
    criticality = Column(String(20), default="medium")
    production_capacity = Column(Numeric(15, 2))
    production_unit = Column(String(50))
    install_date = Column(Date)
    status = Column(String(50), default="operational")
    is_active = Column(Boolean, default=True)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "site_id": self.site_id,
            "parent_asset_id": self.parent_asset_id,
            "code": self.code,
            "name": self.name,
            "name_ar": self.name_ar,
            "asset_type": self.asset_type,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial_number": self.serial_number,
            "criticality": self.criticality,
            "production_capacity": float(self.production_capacity) if self.production_capacity else None,
            "production_unit": self.production_unit,
            "status": self.status,
            "is_active": self.is_active
        }

class AssetComponent(Base):
    __tablename__ = "asset_components"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    parent_component_id = Column(Integer, ForeignKey("asset_components.id"))
    code = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    component_type = Column(String(100))
    criticality = Column(String(20), default="medium")
    is_active = Column(Boolean, default=True)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class AssetFailureMode(Base):
    __tablename__ = "asset_failure_modes"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    component_id = Column(Integer, ForeignKey("asset_components.id"))
    code = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    description = Column(Text)
    failure_effect = Column(Text)
    severity = Column(Integer)
    occurrence = Column(Integer)
    detection = Column(Integer)
    mitigation_action = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    @property
    def rpn(self):
        if self.severity and self.occurrence and self.detection:
            return self.severity * self.occurrence * self.detection
        return None

class AssetMetricsSnapshot(Base):
    __tablename__ = "asset_metrics_snapshot"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    component_id = Column(Integer, ForeignKey("asset_components.id"))
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Numeric(20, 6))
    unit = Column(String(50))
    quality = Column(String(20), default="good")
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AssetAIScore(Base):
    __tablename__ = "asset_ai_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    health_score = Column(Numeric(5, 2))
    failure_probability = Column(Numeric(5, 4))
    remaining_useful_life_days = Column(Integer)
    production_risk_index = Column(Numeric(5, 2))
    anomaly_detected = Column(Boolean, default=False)
    anomaly_details = Column(JSONB)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())
    model_version = Column(String(50))
    
    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "health_score": float(self.health_score) if self.health_score else None,
            "failure_probability": float(self.failure_probability) if self.failure_probability else None,
            "remaining_useful_life_days": self.remaining_useful_life_days,
            "production_risk_index": float(self.production_risk_index) if self.production_risk_index else None,
            "anomaly_detected": self.anomaly_detected,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None
        }

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    component_id = Column(Integer, ForeignKey("asset_components.id"))
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    title = Column(String(255), nullable=False)
    title_ar = Column(String(255))
    description = Column(Text)
    status = Column(String(20), default="open")
    acknowledged_by = Column(Integer, ForeignKey("users.id"))
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
