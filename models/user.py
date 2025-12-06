from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    full_name = Column(String(255))
    full_name_ar = Column(String(255))
    is_active = Column(Boolean, default=True)
    auth_source = Column(String(20), default="local")  # "local" or "sso"
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self, include_tenant=False):
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "email": self.email,
            "username": self.username,
            "role": self.role,
            "full_name": self.full_name,
            "full_name_ar": self.full_name_ar,
            "is_active": self.is_active,
            "auth_source": self.auth_source or "local",
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        return data
