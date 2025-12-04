from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional
from models.base import get_db
from models.user import User
from models.optimization import WorkOrder
from models.asset import Asset
from core.auth import get_current_user
from core.rbac import has_capability, require_tenant_access

router = APIRouter(prefix="/api/work-orders", tags=["Work Orders"])

class WorkOrderCreate(BaseModel):
    asset_id: Optional[int] = None
    code: str
    title: str
    title_ar: Optional[str] = None
    description: Optional[str] = None
    work_type: Optional[str] = None
    priority: str = "medium"
    assigned_to: Optional[int] = None
    scheduled_date: Optional[str] = None
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None

class WorkOrderUpdate(BaseModel):
    title: Optional[str] = None
    title_ar: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[int] = None
    scheduled_date: Optional[str] = None
    due_date: Optional[str] = None
    notes: Optional[str] = None

@router.get("/")
async def list_work_orders(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    asset_id: Optional[int] = None,
    assigned_to: Optional[int] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "view_work_orders"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(WorkOrder)
    
    if current_user.role != "platform_owner":
        query = query.filter(WorkOrder.tenant_id == current_user.tenant_id)
    
    if current_user.role == "engineer":
        query = query.filter(WorkOrder.assigned_to == current_user.id)
    
    if status:
        query = query.filter(WorkOrder.status == status)
    if priority:
        query = query.filter(WorkOrder.priority == priority)
    if asset_id:
        query = query.filter(WorkOrder.asset_id == asset_id)
    if assigned_to:
        query = query.filter(WorkOrder.assigned_to == assigned_to)
    
    query = query.order_by(desc(WorkOrder.created_at))
    
    total = query.count()
    work_orders = query.offset(offset).limit(limit).all()
    
    return {"total": total, "work_orders": [wo.to_dict() for wo in work_orders]}

@router.get("/{work_order_id}")
async def get_work_order(
    work_order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "view_work_orders"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    wo = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    
    require_tenant_access(current_user, wo.tenant_id)
    
    result = wo.to_dict()
    
    if wo.asset_id:
        asset = db.query(Asset).filter(Asset.id == wo.asset_id).first()
        if asset:
            result["asset"] = {"id": asset.id, "code": asset.code, "name": asset.name}
    
    if wo.assigned_to:
        user = db.query(User).filter(User.id == wo.assigned_to).first()
        if user:
            result["assigned_user"] = {"id": user.id, "name": user.full_name or user.username}
    
    return result

@router.post("/")
async def create_work_order(
    wo_data: WorkOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_work_orders"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    tenant_id = current_user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    from datetime import date as date_type
    
    scheduled = None
    if wo_data.scheduled_date:
        scheduled = date_type.fromisoformat(wo_data.scheduled_date)
    
    due = None
    if wo_data.due_date:
        due = date_type.fromisoformat(wo_data.due_date)
    
    wo = WorkOrder(
        tenant_id=tenant_id,
        asset_id=wo_data.asset_id,
        code=wo_data.code,
        title=wo_data.title,
        title_ar=wo_data.title_ar,
        description=wo_data.description,
        work_type=wo_data.work_type,
        priority=wo_data.priority,
        status="open",
        assigned_to=wo_data.assigned_to,
        scheduled_date=scheduled,
        due_date=due,
        estimated_hours=wo_data.estimated_hours,
        created_by=current_user.id
    )
    db.add(wo)
    db.commit()
    
    return {"success": True, "work_order": wo.to_dict()}

@router.put("/{work_order_id}")
async def update_work_order(
    work_order_id: int,
    update_data: WorkOrderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_work_orders"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    wo = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    
    require_tenant_access(current_user, wo.tenant_id)
    
    from datetime import date as date_type
    
    if update_data.title is not None:
        wo.title = update_data.title
    if update_data.title_ar is not None:
        wo.title_ar = update_data.title_ar
    if update_data.description is not None:
        wo.description = update_data.description
    if update_data.priority is not None:
        wo.priority = update_data.priority
    if update_data.status is not None:
        old_status = wo.status
        wo.status = update_data.status
        if update_data.status == "in_progress" and old_status != "in_progress":
            wo.started_at = datetime.utcnow()
        elif update_data.status == "completed" and old_status != "completed":
            wo.completed_at = datetime.utcnow()
    if update_data.assigned_to is not None:
        wo.assigned_to = update_data.assigned_to
    if update_data.scheduled_date is not None:
        wo.scheduled_date = date_type.fromisoformat(update_data.scheduled_date)
    if update_data.due_date is not None:
        wo.due_date = date_type.fromisoformat(update_data.due_date)
    if update_data.notes is not None:
        wo.notes = update_data.notes
    
    wo.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "work_order": wo.to_dict()}

@router.post("/{work_order_id}/start")
async def start_work_order(
    work_order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_work_orders"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    wo = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    
    require_tenant_access(current_user, wo.tenant_id)
    
    wo.status = "in_progress"
    wo.started_at = datetime.utcnow()
    wo.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "work_order": wo.to_dict()}

@router.post("/{work_order_id}/complete")
async def complete_work_order(
    work_order_id: int,
    actual_hours: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_work_orders"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    wo = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    
    require_tenant_access(current_user, wo.tenant_id)
    
    wo.status = "completed"
    wo.completed_at = datetime.utcnow()
    if actual_hours:
        wo.actual_hours = actual_hours
    wo.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "work_order": wo.to_dict()}
