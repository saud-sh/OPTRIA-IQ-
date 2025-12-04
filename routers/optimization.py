from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from models.base import get_db
from models.user import User
from models.optimization import OptimizationRun, OptimizationScenario, OptimizationRecommendation, OptimizationCostModel
from core.auth import get_current_user
from core.rbac import has_capability, require_tenant_access
from core.optimization_engine import get_optimization_engine

router = APIRouter(prefix="/api/optimization", tags=["Optimization"])

class OptimizationRequest(BaseModel):
    optimization_type: str
    parameters: Dict[str, Any] = {}

class CostModelCreate(BaseModel):
    asset_id: Optional[int] = None
    site_id: Optional[int] = None
    cost_per_hour_downtime: Optional[float] = None
    cost_per_failure: Optional[float] = None
    maintenance_cost_preventive: Optional[float] = None
    maintenance_cost_corrective: Optional[float] = None
    energy_cost_per_unit: Optional[float] = None
    production_value_per_unit: Optional[float] = None
    currency: str = "SAR"

@router.post("/run")
async def run_optimization(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "run_optimization"):
        raise HTTPException(status_code=403, detail="Not authorized to run optimization")
    
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    engine = get_optimization_engine(db)
    
    valid_types = ["maintenance_priority", "deferral_cost", "production_risk", "workforce_dispatch"]
    if request.optimization_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid optimization type. Valid types: {valid_types}")
    
    if request.optimization_type == "maintenance_priority":
        run = engine.run_maintenance_prioritization(tenant_id, current_user.id, request.parameters)
    elif request.optimization_type == "deferral_cost":
        run = engine.run_deferral_cost_analysis(tenant_id, current_user.id, request.parameters)
    elif request.optimization_type == "production_risk":
        run = engine.run_production_risk_optimization(tenant_id, current_user.id, request.parameters)
    elif request.optimization_type == "workforce_dispatch":
        run = engine.run_workforce_dispatch_optimization(tenant_id, current_user.id, request.parameters)
    
    return {"success": True, "run": run.to_dict()}

@router.get("/runs")
async def list_optimization_runs(
    run_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "view_optimization"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(OptimizationRun)
    
    if current_user.role != "platform_owner":
        query = query.filter(OptimizationRun.tenant_id == current_user.tenant_id)
    
    if run_type:
        query = query.filter(OptimizationRun.run_type == run_type)
    if status:
        query = query.filter(OptimizationRun.status == status)
    
    query = query.order_by(desc(OptimizationRun.created_at))
    
    total = query.count()
    runs = query.offset(offset).limit(limit).all()
    
    return {"total": total, "runs": [r.to_dict() for r in runs]}

@router.get("/runs/{run_id}")
async def get_optimization_run(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "view_optimization"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    run = db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Optimization run not found")
    
    require_tenant_access(current_user, run.tenant_id)
    
    result = run.to_dict()
    
    scenarios = db.query(OptimizationScenario).filter(
        OptimizationScenario.run_id == run_id
    ).all()
    result["scenarios"] = [s.to_dict() for s in scenarios]
    
    recommendations = db.query(OptimizationRecommendation).filter(
        OptimizationRecommendation.run_id == run_id
    ).order_by(desc(OptimizationRecommendation.priority_score)).all()
    result["recommendations"] = [r.to_dict() for r in recommendations]
    
    return result

@router.get("/recommendations")
async def list_recommendations(
    status: Optional[str] = None,
    asset_id: Optional[int] = None,
    recommendation_type: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "view_optimization"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(OptimizationRecommendation)
    
    if current_user.role != "platform_owner":
        query = query.filter(OptimizationRecommendation.tenant_id == current_user.tenant_id)
    
    if status:
        query = query.filter(OptimizationRecommendation.status == status)
    if asset_id:
        query = query.filter(OptimizationRecommendation.asset_id == asset_id)
    if recommendation_type:
        query = query.filter(OptimizationRecommendation.recommendation_type == recommendation_type)
    
    query = query.order_by(desc(OptimizationRecommendation.priority_score))
    
    total = query.count()
    recommendations = query.offset(offset).limit(limit).all()
    
    return {"total": total, "recommendations": [r.to_dict() for r in recommendations]}

@router.put("/recommendations/{recommendation_id}/status")
async def update_recommendation_status(
    recommendation_id: int,
    status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "run_optimization"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    rec = db.query(OptimizationRecommendation).filter(
        OptimizationRecommendation.id == recommendation_id
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    require_tenant_access(current_user, rec.tenant_id)
    
    valid_statuses = ["pending", "approved", "rejected", "in_progress", "completed"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {valid_statuses}")
    
    rec.status = status
    db.commit()
    
    return {"success": True, "recommendation": rec.to_dict()}

@router.get("/cost-models")
async def list_cost_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "view_optimization"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(OptimizationCostModel).filter(OptimizationCostModel.is_active == True)
    
    if current_user.role != "platform_owner":
        query = query.filter(OptimizationCostModel.tenant_id == current_user.tenant_id)
    
    models = query.all()
    
    return [{
        "id": m.id,
        "tenant_id": m.tenant_id,
        "asset_id": m.asset_id,
        "site_id": m.site_id,
        "cost_per_hour_downtime": float(m.cost_per_hour_downtime) if m.cost_per_hour_downtime else None,
        "cost_per_failure": float(m.cost_per_failure) if m.cost_per_failure else None,
        "maintenance_cost_preventive": float(m.maintenance_cost_preventive) if m.maintenance_cost_preventive else None,
        "maintenance_cost_corrective": float(m.maintenance_cost_corrective) if m.maintenance_cost_corrective else None,
        "currency": m.currency
    } for m in models]

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
    
    cost_model = OptimizationCostModel(
        tenant_id=tenant_id,
        asset_id=model_data.asset_id,
        site_id=model_data.site_id,
        cost_per_hour_downtime=model_data.cost_per_hour_downtime,
        cost_per_failure=model_data.cost_per_failure,
        maintenance_cost_preventive=model_data.maintenance_cost_preventive,
        maintenance_cost_corrective=model_data.maintenance_cost_corrective,
        energy_cost_per_unit=model_data.energy_cost_per_unit,
        production_value_per_unit=model_data.production_value_per_unit,
        currency=model_data.currency
    )
    db.add(cost_model)
    db.commit()
    
    return {"success": True, "cost_model_id": cost_model.id}

@router.get("/maintenance-priority")
async def get_maintenance_priority(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "view_optimization"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tenant_id = current_user.tenant_id
    
    latest_run = db.query(OptimizationRun).filter(
        OptimizationRun.tenant_id == tenant_id,
        OptimizationRun.run_type == "maintenance_priority",
        OptimizationRun.status == "completed"
    ).order_by(desc(OptimizationRun.completed_at)).first()
    
    if not latest_run:
        return {"message": "No maintenance priority analysis available. Run optimization first."}
    
    scenario = db.query(OptimizationScenario).filter(
        OptimizationScenario.run_id == latest_run.id
    ).first()
    
    recommendations = db.query(OptimizationRecommendation).filter(
        OptimizationRecommendation.run_id == latest_run.id
    ).order_by(desc(OptimizationRecommendation.priority_score)).limit(20).all()
    
    return {
        "run": latest_run.to_dict(),
        "scenario": scenario.to_dict() if scenario else None,
        "recommendations": [r.to_dict() for r in recommendations]
    }
