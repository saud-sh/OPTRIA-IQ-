"""
Notifications API Router
In-app notification management for OPTRIA IQ.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from pydantic import BaseModel

from models.base import get_db
from models.user import User
from models.notification import Notification
from core.auth import get_current_user
from core.rbac import has_capability

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationCreate(BaseModel):
    user_id: int
    notification_type: str
    title: str
    title_ar: Optional[str] = None
    body: Optional[str] = None
    body_ar: Optional[str] = None
    severity: str = "INFO"
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    action_url: Optional[str] = None
    payload: Optional[dict] = {}


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    is_dismissed: Optional[bool] = None


class BulkNotificationAction(BaseModel):
    notification_ids: List[str]
    action: str


@router.get("")
async def list_notifications(
    is_read: Optional[bool] = None,
    notification_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List notifications for the current user"""
    if not has_capability(current_user, "view_notifications"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(Notification).filter(
        Notification.tenant_id == current_user.tenant_id,
        Notification.user_id == current_user.id,
        Notification.is_dismissed == False
    )
    
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    if notification_type:
        query = query.filter(Notification.notification_type == notification_type)
    if severity:
        query = query.filter(Notification.severity == severity)
    
    total = query.count()
    notifications = query.order_by(desc(Notification.created_at)).offset(offset).limit(limit).all()
    
    return {
        "notifications": [n.to_dict() for n in notifications],
        "total": total,
        "unread_count": db.query(func.count(Notification.id)).filter(
            Notification.tenant_id == current_user.tenant_id,
            Notification.user_id == current_user.id,
            Notification.is_read == False,
            Notification.is_dismissed == False
        ).scalar() or 0,
        "limit": limit,
        "offset": offset
    }


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get unread notification count for the current user"""
    if not has_capability(current_user, "view_notifications"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    count = db.query(func.count(Notification.id)).filter(
        Notification.tenant_id == current_user.tenant_id,
        Notification.user_id == current_user.id,
        Notification.is_read == False,
        Notification.is_dismissed == False
    ).scalar() or 0
    
    return {"unread_count": count}


@router.get("/{notification_id}")
async def get_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific notification"""
    if not has_capability(current_user, "view_notifications"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.tenant_id == current_user.tenant_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return notification.to_dict()


@router.put("/{notification_id}")
async def update_notification(
    notification_id: str,
    data: NotificationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a notification (mark as read, dismissed, etc.)"""
    if not has_capability(current_user, "view_notifications"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.tenant_id == current_user.tenant_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if data.is_read is not None:
        notification.is_read = data.is_read
        if data.is_read:
            notification.read_at = datetime.utcnow()
    
    if data.is_dismissed is not None:
        notification.is_dismissed = data.is_dismissed
        if data.is_dismissed:
            notification.dismissed_at = datetime.utcnow()
    
    db.commit()
    
    return notification.to_dict()


@router.post("/mark-all-read")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read for the current user"""
    if not has_capability(current_user, "view_notifications"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    count = db.query(Notification).filter(
        Notification.tenant_id == current_user.tenant_id,
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({
        "is_read": True,
        "read_at": datetime.utcnow()
    })
    
    db.commit()
    
    return {"marked_read": count}


@router.post("/dismiss-all")
async def dismiss_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Dismiss all notifications for the current user"""
    if not has_capability(current_user, "view_notifications"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    count = db.query(Notification).filter(
        Notification.tenant_id == current_user.tenant_id,
        Notification.user_id == current_user.id,
        Notification.is_dismissed == False
    ).update({
        "is_dismissed": True,
        "dismissed_at": datetime.utcnow()
    })
    
    db.commit()
    
    return {"dismissed": count}


@router.post("/bulk-action")
async def bulk_action(
    data: BulkNotificationAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Perform bulk actions on notifications"""
    if not has_capability(current_user, "view_notifications"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = db.query(Notification).filter(
        Notification.id.in_(data.notification_ids),
        Notification.tenant_id == current_user.tenant_id,
        Notification.user_id == current_user.id
    )
    
    if data.action == "mark_read":
        count = query.update({
            "is_read": True,
            "read_at": datetime.utcnow()
        }, synchronize_session=False)
    elif data.action == "mark_unread":
        count = query.update({
            "is_read": False,
            "read_at": None
        }, synchronize_session=False)
    elif data.action == "dismiss":
        count = query.update({
            "is_dismissed": True,
            "dismissed_at": datetime.utcnow()
        }, synchronize_session=False)
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    db.commit()
    
    return {"updated": count}


@router.post("")
async def create_notification(
    data: NotificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a notification (admin only)"""
    if not has_capability(current_user, "manage_notifications"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    target_user = db.query(User).filter(
        User.id == data.user_id,
        User.tenant_id == current_user.tenant_id
    ).first()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    notification = Notification(
        tenant_id=current_user.tenant_id,
        user_id=data.user_id,
        notification_type=data.notification_type,
        title=data.title,
        title_ar=data.title_ar,
        body=data.body,
        body_ar=data.body_ar,
        severity=data.severity,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        action_url=data.action_url,
        payload=data.payload or {}
    )
    
    db.add(notification)
    db.commit()
    
    return notification.to_dict()
