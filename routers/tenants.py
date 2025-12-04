import secrets
import string
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from models.base import get_db
from models.tenant import Tenant
from models.user import User
from models.integration import AuditLog
from core.auth import get_current_user, get_password_hash
from core.rbac import has_capability, require_tenant_access

router = APIRouter(prefix="/api/tenants", tags=["Tenants"])

class TenantCreate(BaseModel):
    code: str
    name: str
    name_ar: Optional[str] = None
    industry: Optional[str] = None
    admin_email: EmailStr
    admin_name: str

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    name_ar: Optional[str] = None
    industry: Optional[str] = None
    status: Optional[str] = None

class TenantResponse(BaseModel):
    id: int
    code: str
    name: str
    name_ar: Optional[str]
    industry: Optional[str]
    status: str

def generate_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@router.get("/", response_model=List[TenantResponse])
async def list_tenants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "platform_owner":
        tenants = db.query(Tenant).filter(Tenant.status != "deleted").all()
    elif current_user.tenant_id:
        tenants = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).all()
    else:
        tenants = []
    
    return [TenantResponse(**t.to_dict()) for t in tenants]

@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    require_tenant_access(current_user, tenant_id)
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return tenant.to_dict()

@router.post("/")
async def create_tenant(
    request: Request,
    tenant_data: TenantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_tenants"):
        raise HTTPException(status_code=403, detail="Not authorized to create tenants")
    
    existing = db.query(Tenant).filter(Tenant.code == tenant_data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tenant code already exists")
    
    tenant = Tenant(
        code=tenant_data.code,
        name=tenant_data.name,
        name_ar=tenant_data.name_ar,
        industry=tenant_data.industry,
        status="active"
    )
    db.add(tenant)
    db.flush()
    
    admin_password = generate_password()
    admin_user = User(
        tenant_id=tenant.id,
        email=tenant_data.admin_email,
        username=tenant_data.admin_name.lower().replace(" ", "_"),
        password_hash=get_password_hash(admin_password),
        role="tenant_admin",
        full_name=tenant_data.admin_name,
        is_active=True
    )
    db.add(admin_user)
    
    audit_log = AuditLog(
        tenant_id=tenant.id,
        user_id=current_user.id,
        action="create_tenant",
        entity_type="tenant",
        entity_id=tenant.id,
        new_values={"code": tenant.code, "name": tenant.name},
        ip_address=request.client.host if request.client else None
    )
    db.add(audit_log)
    
    db.commit()
    
    return {
        "success": True,
        "tenant": tenant.to_dict(),
        "admin_credentials": {
            "email": tenant_data.admin_email,
            "password": admin_password,
            "note": "Please save this password securely. It will only be shown once."
        }
    }

@router.put("/{tenant_id}")
async def update_tenant(
    request: Request,
    tenant_id: int,
    tenant_data: TenantUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_capability(current_user, "manage_tenants") and not (
        has_capability(current_user, "manage_tenant_users") and current_user.tenant_id == tenant_id
    ):
        raise HTTPException(status_code=403, detail="Not authorized to update tenant")
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    old_values = tenant.to_dict()
    
    if tenant_data.name is not None:
        tenant.name = tenant_data.name
    if tenant_data.name_ar is not None:
        tenant.name_ar = tenant_data.name_ar
    if tenant_data.industry is not None:
        tenant.industry = tenant_data.industry
    if tenant_data.status is not None and current_user.role == "platform_owner":
        tenant.status = tenant_data.status
    
    tenant.updated_at = datetime.utcnow()
    
    audit_log = AuditLog(
        tenant_id=tenant.id,
        user_id=current_user.id,
        action="update_tenant",
        entity_type="tenant",
        entity_id=tenant.id,
        old_values=old_values,
        new_values=tenant.to_dict(),
        ip_address=request.client.host if request.client else None
    )
    db.add(audit_log)
    
    db.commit()
    
    return {"success": True, "tenant": tenant.to_dict()}

@router.get("/{tenant_id}/users")
async def list_tenant_users(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    require_tenant_access(current_user, tenant_id)
    
    if not has_capability(current_user, "manage_tenant_users"):
        raise HTTPException(status_code=403, detail="Not authorized to view users")
    
    users = db.query(User).filter(User.tenant_id == tenant_id).all()
    return [u.to_dict() for u in users]
