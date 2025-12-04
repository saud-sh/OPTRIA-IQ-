from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric, Date, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from models.base import Base

class OptimizationCostModel(Base):
    __tablename__ = "optimization_cost_models"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    site_id = Column(Integer, ForeignKey("sites.id"))
    cost_per_hour_downtime = Column(Numeric(15, 2))
    cost_per_failure = Column(Numeric(15, 2))
    maintenance_cost_preventive = Column(Numeric(15, 2))
    maintenance_cost_corrective = Column(Numeric(15, 2))
    energy_cost_per_unit = Column(Numeric(15, 4))
    production_value_per_unit = Column(Numeric(15, 4))
    currency = Column(String(10), default="SAR")
    valid_from = Column(Date)
    valid_to = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class OptimizationRun(Base):
    __tablename__ = "optimization_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    run_type = Column(String(50), nullable=False)
    status = Column(String(20), default="pending")
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    input_parameters = Column(JSONB, nullable=False)
    output_summary = Column(JSONB)
    error_message = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "run_type": self.run_type,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "input_parameters": self.input_parameters,
            "output_summary": self.output_summary,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class OptimizationScenario(Base):
    __tablename__ = "optimization_scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("optimization_runs.id"))
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    description = Column(Text)
    scenario_type = Column(String(50))
    parameters = Column(JSONB, nullable=False)
    results = Column(JSONB)
    total_cost = Column(Numeric(15, 2))
    total_risk_score = Column(Numeric(10, 4))
    is_recommended = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "run_id": self.run_id,
            "name": self.name,
            "name_ar": self.name_ar,
            "description": self.description,
            "scenario_type": self.scenario_type,
            "parameters": self.parameters,
            "results": self.results,
            "total_cost": float(self.total_cost) if self.total_cost else None,
            "total_risk_score": float(self.total_risk_score) if self.total_risk_score else None,
            "is_recommended": self.is_recommended,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class OptimizationRecommendation(Base):
    __tablename__ = "optimization_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("optimization_runs.id"), nullable=False)
    scenario_id = Column(Integer, ForeignKey("optimization_scenarios.id"))
    asset_id = Column(Integer, ForeignKey("assets.id"))
    recommendation_type = Column(String(50), nullable=False)
    priority_score = Column(Numeric(10, 4))
    deferral_cost = Column(Numeric(15, 2))
    risk_reduction = Column(Numeric(10, 4))
    action_title = Column(String(255), nullable=False)
    action_title_ar = Column(String(255))
    action_description = Column(Text)
    recommended_date = Column(Date)
    assigned_to = Column(Integer, ForeignKey("users.id"))
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "run_id": self.run_id,
            "asset_id": self.asset_id,
            "recommendation_type": self.recommendation_type,
            "priority_score": float(self.priority_score) if self.priority_score else None,
            "deferral_cost": float(self.deferral_cost) if self.deferral_cost else None,
            "risk_reduction": float(self.risk_reduction) if self.risk_reduction else None,
            "action_title": self.action_title,
            "action_title_ar": self.action_title_ar,
            "action_description": self.action_description,
            "recommended_date": self.recommended_date.isoformat() if self.recommended_date else None,
            "status": self.status
        }

class WorkOrder(Base):
    __tablename__ = "work_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    recommendation_id = Column(Integer, ForeignKey("optimization_recommendations.id"))
    code = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    title_ar = Column(String(255))
    description = Column(Text)
    work_type = Column(String(50))
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="open")
    assigned_to = Column(Integer, ForeignKey("users.id"))
    scheduled_date = Column(Date)
    due_date = Column(Date)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    estimated_hours = Column(Numeric(8, 2))
    actual_hours = Column(Numeric(8, 2))
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "asset_id": self.asset_id,
            "code": self.code,
            "title": self.title,
            "title_ar": self.title_ar,
            "description": self.description,
            "work_type": self.work_type,
            "priority": self.priority,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "estimated_hours": float(self.estimated_hours) if self.estimated_hours else None
        }
