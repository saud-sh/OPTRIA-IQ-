import os
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc

from config import settings
from models.base import Base, engine, get_db, SessionLocal
from models.tenant import Tenant
from models.user import User
from models.asset import Asset, Site, AssetAIScore
from models.optimization import OptimizationRun, OptimizationRecommendation, WorkOrder
from core.auth import get_current_user_optional, get_password_hash
from translations import get_translation, t

from routers.auth import router as auth_router
from routers.tenants import router as tenants_router
from routers.assets import router as assets_router
from routers.optimization import router as optimization_router
from routers.integrations import router as integrations_router
from routers.health import router as health_router
from routers.work_orders import router as work_orders_router

def init_db():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        platform_owner = db.query(User).filter(User.role == "platform_owner").first()
        if not platform_owner:
            platform_owner = User(
                email="admin@optria.io",
                username="admin",
                password_hash=get_password_hash("OptriA2024!"),
                role="platform_owner",
                full_name="Platform Administrator",
                full_name_ar="مدير المنصة",
                is_active=True
            )
            db.add(platform_owner)
            db.commit()
            print("Created platform owner: admin@optria.io / OptriA2024!")
        
        if settings.demo_mode:
            seed_demo_data(db)
    finally:
        db.close()

def seed_demo_data(db: Session):
    demo_tenant = db.query(Tenant).filter(Tenant.code == "ARAMCO_DEMO").first()
    if demo_tenant:
        return
    
    demo_tenant = Tenant(
        code="ARAMCO_DEMO",
        name="ARAMCO Demo Tenant",
        name_ar="مستأجر أرامكو التجريبي",
        industry="Oil & Gas",
        status="active"
    )
    db.add(demo_tenant)
    db.flush()
    
    demo_admin = User(
        tenant_id=demo_tenant.id,
        email="demo@aramco.com",
        username="demo_admin",
        password_hash=get_password_hash("Demo2024!"),
        role="tenant_admin",
        full_name="Demo Administrator",
        full_name_ar="المدير التجريبي",
        is_active=True
    )
    db.add(demo_admin)
    
    demo_engineer = User(
        tenant_id=demo_tenant.id,
        email="engineer@aramco.com",
        username="demo_engineer",
        password_hash=get_password_hash("Engineer2024!"),
        role="engineer",
        full_name="Demo Engineer",
        full_name_ar="المهندس التجريبي",
        is_active=True
    )
    db.add(demo_engineer)
    db.flush()
    
    site1 = Site(
        tenant_id=demo_tenant.id,
        code="PLANT-A",
        name="Ras Tanura Refinery",
        name_ar="مصفاة رأس تنورة",
        location="Ras Tanura, Saudi Arabia",
        site_type="Refinery"
    )
    db.add(site1)
    
    site2 = Site(
        tenant_id=demo_tenant.id,
        code="PLANT-B",
        name="Abqaiq Processing Plant",
        name_ar="معمل بقيق للمعالجة",
        location="Abqaiq, Saudi Arabia",
        site_type="Processing"
    )
    db.add(site2)
    db.flush()
    
    assets_data = [
        {"code": "PUMP-001", "name": "Main Cooling Water Pump", "name_ar": "مضخة مياه التبريد الرئيسية", "type": "Pump", "criticality": "critical", "site_id": site1.id},
        {"code": "PUMP-002", "name": "Secondary Feed Pump", "name_ar": "مضخة التغذية الثانوية", "type": "Pump", "criticality": "high", "site_id": site1.id},
        {"code": "COMP-001", "name": "Gas Compressor Unit 1", "name_ar": "وحدة ضاغط الغاز 1", "type": "Compressor", "criticality": "critical", "site_id": site1.id},
        {"code": "TURB-001", "name": "Steam Turbine Generator", "name_ar": "مولد التوربينات البخارية", "type": "Turbine", "criticality": "critical", "site_id": site1.id},
        {"code": "HX-001", "name": "Heat Exchanger A", "name_ar": "المبادل الحراري أ", "type": "Heat Exchanger", "criticality": "high", "site_id": site1.id},
        {"code": "PUMP-003", "name": "Oil Transfer Pump", "name_ar": "مضخة نقل الزيت", "type": "Pump", "criticality": "medium", "site_id": site2.id},
        {"code": "SEP-001", "name": "Gas Oil Separator", "name_ar": "فاصل زيت الغاز", "type": "Separator", "criticality": "high", "site_id": site2.id},
        {"code": "COMP-002", "name": "Boost Compressor", "name_ar": "ضاغط التعزيز", "type": "Compressor", "criticality": "high", "site_id": site2.id},
    ]
    
    for asset_data in assets_data:
        asset = Asset(
            tenant_id=demo_tenant.id,
            site_id=asset_data["site_id"],
            code=asset_data["code"],
            name=asset_data["name"],
            name_ar=asset_data["name_ar"],
            asset_type=asset_data["type"],
            criticality=asset_data["criticality"],
            status="operational"
        )
        db.add(asset)
    
    db.commit()
    print("Demo data seeded successfully")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="OPTRIA IQ",
    description="Industrial Operations Optimization Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)
app.include_router(tenants_router)
app.include_router(assets_router)
app.include_router(optimization_router)
app.include_router(integrations_router)
app.include_router(health_router)
app.include_router(work_orders_router)

def get_lang(request: Request) -> str:
    return request.query_params.get("lang", "ar")

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page - renders instantly without DB operations"""
    lang = get_lang(request)
    trans = get_translation(lang)
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "t": trans,
        "lang": lang,
        "rtl": lang == "ar"
    })

@app.get("/health")
async def health_check():
    """Fast health check endpoint for deployment monitoring"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "app": settings.app_name,
        "version": settings.app_version
    }

@app.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional)
):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    lang = get_lang(request)
    trans = get_translation(lang)
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "t": trans,
        "lang": lang,
        "rtl": lang == "ar"
    })

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    lang = get_lang(request)
    trans = get_translation(lang)
    
    tenant_id = current_user.tenant_id
    
    if current_user.role == "platform_owner":
        total_assets = db.query(Asset).filter(Asset.is_active == True).count()
        total_tenants = db.query(Tenant).filter(Tenant.status == "active").count()
    else:
        total_assets = db.query(Asset).filter(
            Asset.tenant_id == tenant_id,
            Asset.is_active == True
        ).count()
        total_tenants = 1
    
    pending_recommendations = db.query(OptimizationRecommendation).filter(
        OptimizationRecommendation.tenant_id == tenant_id,
        OptimizationRecommendation.status == "pending"
    ).count() if tenant_id else 0
    
    recent_runs = db.query(OptimizationRun).filter(
        OptimizationRun.tenant_id == tenant_id
    ).order_by(desc(OptimizationRun.created_at)).limit(5).all() if tenant_id else []
    
    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "t": trans,
        "lang": lang,
        "rtl": lang == "ar",
        "user": current_user,
        "total_assets": total_assets,
        "total_tenants": total_tenants,
        "pending_recommendations": pending_recommendations,
        "recent_runs": recent_runs
    })

@app.get("/optimization", response_class=HTMLResponse)
async def optimization_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    lang = get_lang(request)
    trans = get_translation(lang)
    
    return templates.TemplateResponse("optimization/index.html", {
        "request": request,
        "t": trans,
        "lang": lang,
        "rtl": lang == "ar",
        "user": current_user
    })

@app.get("/assets", response_class=HTMLResponse)
async def assets_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    lang = get_lang(request)
    trans = get_translation(lang)
    
    tenant_id = current_user.tenant_id
    
    if current_user.role == "platform_owner":
        assets = db.query(Asset).filter(Asset.is_active == True).limit(100).all()
        sites = db.query(Site).filter(Site.is_active == True).all()
    else:
        assets = db.query(Asset).filter(
            Asset.tenant_id == tenant_id,
            Asset.is_active == True
        ).limit(100).all()
        sites = db.query(Site).filter(
            Site.tenant_id == tenant_id,
            Site.is_active == True
        ).all()
    
    assets_with_scores = []
    for asset in assets:
        ai_score = db.query(AssetAIScore).filter(
            AssetAIScore.asset_id == asset.id
        ).order_by(desc(AssetAIScore.computed_at)).first()
        assets_with_scores.append({
            "asset": asset,
            "ai_score": ai_score
        })
    
    return templates.TemplateResponse("assets/index.html", {
        "request": request,
        "t": trans,
        "lang": lang,
        "rtl": lang == "ar",
        "user": current_user,
        "assets": assets_with_scores,
        "sites": sites
    })

@app.get("/integrations", response_class=HTMLResponse)
async def integrations_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    lang = get_lang(request)
    trans = get_translation(lang)
    
    from models.integration import TenantIntegration
    
    tenant_id = current_user.tenant_id
    
    if current_user.role == "platform_owner":
        integrations = db.query(TenantIntegration).all()
    else:
        integrations = db.query(TenantIntegration).filter(
            TenantIntegration.tenant_id == tenant_id
        ).all()
    
    return templates.TemplateResponse("integrations/index.html", {
        "request": request,
        "t": trans,
        "lang": lang,
        "rtl": lang == "ar",
        "user": current_user,
        "integrations": integrations
    })

@app.get("/work-orders", response_class=HTMLResponse)
async def work_orders_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    lang = get_lang(request)
    trans = get_translation(lang)
    
    tenant_id = current_user.tenant_id
    
    if current_user.role == "platform_owner":
        work_orders = db.query(WorkOrder).order_by(desc(WorkOrder.created_at)).limit(100).all()
    elif current_user.role == "engineer":
        work_orders = db.query(WorkOrder).filter(
            WorkOrder.tenant_id == tenant_id,
            WorkOrder.assigned_to == current_user.id
        ).order_by(desc(WorkOrder.created_at)).limit(100).all()
    else:
        work_orders = db.query(WorkOrder).filter(
            WorkOrder.tenant_id == tenant_id
        ).order_by(desc(WorkOrder.created_at)).limit(100).all()
    
    return templates.TemplateResponse("work_orders/index.html", {
        "request": request,
        "t": trans,
        "lang": lang,
        "rtl": lang == "ar",
        "user": current_user,
        "work_orders": work_orders
    })

@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    if current_user.role not in ["tenant_admin", "platform_owner"]:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    lang = get_lang(request)
    trans = get_translation(lang)
    
    return templates.TemplateResponse("onboarding/index.html", {
        "request": request,
        "t": trans,
        "lang": lang,
        "rtl": lang == "ar",
        "user": current_user
    })

@app.get("/admin/tenants", response_class=HTMLResponse)
async def admin_tenants_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not current_user or current_user.role != "platform_owner":
        return RedirectResponse(url="/dashboard", status_code=302)
    
    lang = get_lang(request)
    trans = get_translation(lang)
    
    tenants = db.query(Tenant).filter(Tenant.status != "deleted").all()
    
    return templates.TemplateResponse("admin/tenants.html", {
        "request": request,
        "t": trans,
        "lang": lang,
        "rtl": lang == "ar",
        "user": current_user,
        "tenants": tenants
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
