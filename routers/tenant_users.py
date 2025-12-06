"""
Tenant User Management API
Allows tenant admins to manage users within their tenant
Platform owners can manage users across all tenants
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import secrets
import string
from pydantic import BaseModel, EmailStr
from models.user import User
from models.tenant import Tenant
from core.auth import get_current_user, get_password_hash
from core.rbac import has_capability
from models.base import get_db

router = APIRouter(prefix="/api/tenant-users", tags=["tenant-users"])

VALID_ROLES = ["tenant_admin", "optimization_engineer", "engineer", "viewer"]

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    full_name_ar: Optional[str] = None
    role: str
    password: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    full_name_ar: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class PasswordReset(BaseModel):
    new_password: Optional[str] = None

def generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@router.get("/")
async def list_tenant_users(
    tenant_id: Optional[int] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_tenant_users"):
        raise HTTPException(status_code=403, detail="Not authorized to manage users")
    
    if current_user.role == "platform_owner":
        if tenant_id:
            query = db.query(User).filter(User.tenant_id == tenant_id)
        else:
            query = db.query(User)
    else:
        query = db.query(User).filter(User.tenant_id == current_user.tenant_id)
    
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_term)) |
            (User.username.ilike(search_term)) |
            (User.full_name.ilike(search_term))
        )
    
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "users": [u.to_dict() for u in users],
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.post("/")
async def create_tenant_user(
    user_data: UserCreate,
    tenant_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_tenant_users"):
        raise HTTPException(status_code=403, detail="Not authorized to create users")
    
    if current_user.role == "platform_owner":
        target_tenant_id = tenant_id or current_user.tenant_id
    else:
        target_tenant_id = current_user.tenant_id
    
    if not target_tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID is required")
    
    tenant = db.query(Tenant).filter(Tenant.id == target_tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if user_data.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {VALID_ROLES}")
    
    if current_user.role != "platform_owner" and user_data.role == "tenant_admin":
        existing_admins = db.query(User).filter(
            User.tenant_id == target_tenant_id,
            User.role == "tenant_admin",
            User.is_active == True
        ).count()
        if existing_admins >= 3:
            raise HTTPException(status_code=400, detail="Maximum tenant admins reached")
    
    password = user_data.password or generate_password()
    password_hash = get_password_hash(password)
    
    new_user = User(
        tenant_id=target_tenant_id,
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        full_name_ar=user_data.full_name_ar,
        role=user_data.role,
        password_hash=password_hash,
        auth_source="local",
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    result = new_user.to_dict()
    if not user_data.password:
        result["generated_password"] = password
    
    return result

@router.get("/{user_id}")
async def get_tenant_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_tenant_users"):
        raise HTTPException(status_code=403, detail="Not authorized to view user details")
    
    query = db.query(User).filter(User.id == user_id)
    if current_user.role != "platform_owner":
        query = query.filter(User.tenant_id == current_user.tenant_id)
    
    user = query.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user.to_dict()

@router.put("/{user_id}")
async def update_tenant_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_tenant_users"):
        raise HTTPException(status_code=403, detail="Not authorized to update users")
    
    query = db.query(User).filter(User.id == user_id)
    if current_user.role != "platform_owner":
        query = query.filter(User.tenant_id == current_user.tenant_id)
    
    user = query.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_id == current_user.id and user_data.is_active == False:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    
    if user_data.role and user_data.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {VALID_ROLES}")
    
    if user.auth_source == "sso" and user_data.role:
        pass
    
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.full_name_ar is not None:
        user.full_name_ar = user_data.full_name_ar
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return user.to_dict()

@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    password_data: Optional[PasswordReset] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_tenant_users"):
        raise HTTPException(status_code=403, detail="Not authorized to reset passwords")
    
    query = db.query(User).filter(User.id == user_id)
    if current_user.role != "platform_owner":
        query = query.filter(User.tenant_id == current_user.tenant_id)
    
    user = query.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.auth_source == "sso":
        raise HTTPException(status_code=400, detail="Cannot reset password for SSO users")
    
    if password_data and password_data.new_password:
        new_password = password_data.new_password
    else:
        new_password = generate_password()
    
    user.password_hash = get_password_hash(new_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Password reset successfully",
        "user_id": user_id,
        "new_password": new_password
    }

@router.delete("/{user_id}")
async def delete_tenant_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_tenant_users"):
        raise HTTPException(status_code=403, detail="Not authorized to delete users")
    
    query = db.query(User).filter(User.id == user_id)
    if current_user.role != "platform_owner":
        query = query.filter(User.tenant_id == current_user.tenant_id)
    
    user = query.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "User deactivated successfully", "user_id": user_id}

@router.get("/roles/available")
async def get_available_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_tenant_users"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    roles = []
    if current_user.role == "platform_owner":
        roles = ["platform_owner", "tenant_admin", "optimization_engineer", "engineer", "viewer"]
    else:
        roles = VALID_ROLES
    
    return {"roles": roles}
