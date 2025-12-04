from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from models.base import get_db
from models.user import User
from models.integration import AuditLog
from core.auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, get_current_user_optional, set_auth_cookie, clear_auth_cookie
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    user: dict = None
    redirect_url: str = None

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str = None

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    token = create_access_token(data={"sub": str(user.id)})
    set_auth_cookie(response, token)
    
    audit_log = AuditLog(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="login",
        ip_address=request.client.host if request.client else None,
        new_values={"email": user.email}
    )
    db.add(audit_log)
    db.commit()
    
    redirect_url = "/dashboard"
    if user.role == "platform_owner":
        redirect_url = "/admin/tenants"
    
    return LoginResponse(
        success=True,
        message="Login successful",
        user=user.to_dict(),
        redirect_url=redirect_url
    )

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if current_user:
        audit_log = AuditLog(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            action="logout",
            ip_address=request.client.host if request.client else None
        )
        db.add(audit_log)
        db.commit()
    
    clear_auth_cookie(response)
    return {"success": True, "message": "Logged out successfully"}

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user.to_dict()

@router.get("/check")
async def check_auth(current_user: User = Depends(get_current_user_optional)):
    if current_user:
        return {"authenticated": True, "user": current_user.to_dict()}
    return {"authenticated": False, "user": None}
