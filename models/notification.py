"""
Notification Model for OPTRIA IQ
Stores in-app notifications for users.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from models.base import Base


class Notification(Base):
    """
    In-app notification for users.
    Supports various notification types and entity linking.
    """
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    notification_type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    title_ar = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    body_ar = Column(Text, nullable=True)
    
    severity = Column(String(20), default="INFO")
    
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(255), nullable=True)
    
    action_url = Column(String(500), nullable=True)
    
    payload = Column(JSONB, default={})
    
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    is_dismissed = Column(Boolean, default=False)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index('ix_notifications_user_unread', 'user_id', 'is_read'),
        Index('ix_notifications_tenant_user', 'tenant_id', 'user_id'),
        Index('ix_notifications_entity', 'entity_type', 'entity_id'),
    )
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "notification_type": self.notification_type,
            "title": self.title,
            "title_ar": self.title_ar,
            "body": self.body,
            "body_ar": self.body_ar,
            "severity": self.severity,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action_url": self.action_url,
            "payload": self.payload or {},
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "is_dismissed": self.is_dismissed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


NOTIFICATION_TYPES = [
    "INCIDENT_CREATED",
    "INCIDENT_ASSIGNED",
    "INCIDENT_RESOLVED",
    "WORK_ORDER_CREATED",
    "WORK_ORDER_ASSIGNED",
    "WORK_ORDER_COMPLETED",
    "RCA_COMPLETED",
    "ALERT_CRITICAL",
    "SYSTEM_MESSAGE"
]
