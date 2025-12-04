from typing import List, Optional
from functools import wraps
from fastapi import HTTPException, status, Depends
from models.user import User

CAPABILITIES = {
    "platform_owner": [
        "manage_tenants",
        "manage_all_users",
        "manage_tenant_users",
        "manage_integrations",
        "run_optimization",
        "approve_optimization",
        "view_optimization",
        "manage_assets",
        "view_assets",
        "manage_work_orders",
        "view_work_orders",
        "view_audit_logs",
        "manage_cost_models",
        "view_all_tenants"
    ],
    "tenant_admin": [
        "manage_tenant_users",
        "manage_integrations",
        "run_optimization",
        "approve_optimization",
        "view_optimization",
        "manage_assets",
        "view_assets",
        "manage_work_orders",
        "view_work_orders",
        "view_audit_logs",
        "manage_cost_models"
    ],
    "optimization_engineer": [
        "run_optimization",
        "view_optimization",
        "manage_assets",
        "view_assets",
        "manage_work_orders",
        "view_work_orders"
    ],
    "engineer": [
        "view_optimization",
        "view_assets",
        "manage_work_orders",
        "view_work_orders"
    ],
    "viewer": [
        "view_optimization",
        "view_assets",
        "view_work_orders"
    ]
}

def has_capability(user: User, capability: str) -> bool:
    if not user or not user.role:
        return False
    role_caps = CAPABILITIES.get(user.role, [])
    return capability in role_caps

def get_user_capabilities(user: User) -> List[str]:
    if not user or not user.role:
        return []
    return CAPABILITIES.get(user.role, [])

def require_capability(capability: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break
            
            if not current_user or not has_capability(current_user, capability):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required capability: {capability}"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_platform_owner(current_user: User = Depends()):
    if not current_user or current_user.role != "platform_owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform owner access required"
        )
    return current_user

def require_tenant_admin(current_user: User = Depends()):
    if not current_user or current_user.role not in ["platform_owner", "tenant_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin access required"
        )
    return current_user

def require_optimization_access(current_user: User = Depends()):
    if not current_user or current_user.role not in ["platform_owner", "tenant_admin", "optimization_engineer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Optimization access required"
        )
    return current_user

def check_tenant_access(user: User, tenant_id: int) -> bool:
    if user.role == "platform_owner":
        return True
    if user.tenant_id is None:
        return False
    return user.tenant_id == tenant_id

def require_tenant_access(user: User, tenant_id: int):
    if not check_tenant_access(user, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this tenant is not allowed"
        )
