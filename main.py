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
from models.blackbox import BlackBoxEvent, BlackBoxIncident, BlackBoxIncidentEvent, BlackBoxRCARule, TwinLayout, TwinNode
from models.integration import TenantIntegration, ExternalSignalMapping, TenantCostModel
from core.auth import get_current_user_optional, get_password_hash
from translations import get_translation, t

from routers.auth import router as auth_router
from routers.tenants import router as tenants_router
from routers.assets import router as assets_router
from routers.optimization import router as optimization_router
from routers.integrations import router as integrations_router
from routers.health import router as health_router
from routers.work_orders import router as work_orders_router
from routers.blackbox import router as blackbox_router
from routers.twin import router as twin_router
from routers.tenant_users import router as tenant_users_router

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
            seed_existing_demo_tenant(db)
    finally:
        db.close()

def seed_existing_demo_tenant(db: Session):
    """Seed integrations for existing ARAMCO_DEMO tenant if it exists but has no integrations"""
    demo_tenant = db.query(Tenant).filter(Tenant.code == "ARAMCO_DEMO").first()
    if not demo_tenant:
        print("ARAMCO_DEMO tenant not found, skipping integration seeding")
        return
    
    existing_integrations = db.query(TenantIntegration).filter(
        TenantIntegration.tenant_id == demo_tenant.id
    ).count()
    
    if existing_integrations == 0:
        print(f"Seeding demo integrations for existing tenant {demo_tenant.code}...")
        seed_demo_integrations(db, demo_tenant)

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
    
    seed_demo_integrations(db, demo_tenant)

def seed_demo_integrations(db: Session, tenant: Tenant):
    """Seed demo integrations for a tenant - idempotent"""
    existing_opcua = db.query(TenantIntegration).filter(
        TenantIntegration.tenant_id == tenant.id,
        TenantIntegration.integration_type == "opcua"
    ).first()
    
    existing_pi = db.query(TenantIntegration).filter(
        TenantIntegration.tenant_id == tenant.id,
        TenantIntegration.integration_type == "pi"
    ).first()
    
    existing_demo = db.query(TenantIntegration).filter(
        TenantIntegration.tenant_id == tenant.id,
        TenantIntegration.integration_type == "demo"
    ).first()
    
    if not existing_opcua:
        opcua_integration = TenantIntegration(
            tenant_id=tenant.id,
            name="Demo OPC-UA - ARAMCO",
            integration_type="opcua",
            status="active",
            config={
                "endpoint_url": settings.opcua_endpoint_url or "opc.tcp://demo-server:4840",
                "security_mode": "None",
                "security_policy": "None",
                "auth_type": "Anonymous",
                "namespace_filter": "ns=2;s=",
                "sampling_interval_ms": 1000,
                "max_tags_per_scan": 500,
                "time_zone": "Asia/Riyadh",
                "is_demo": True
            },
            is_active=True,
            demo_stream_active=True
        )
        db.add(opcua_integration)
        print(f"  Created Demo OPC-UA integration for {tenant.code}")
    
    if not existing_pi:
        pi_integration = TenantIntegration(
            tenant_id=tenant.id,
            name="Demo PI System - ARAMCO",
            integration_type="pi",
            status="active",
            config={
                "pi_webapi_url": settings.pi_base_url or "https://demo-pi-server/piwebapi",
                "auth_type": "Basic",
                "username": "",
                "password": "",
                "af_database_path": "\\\\PI-Server\\ARAMCO-Demo",
                "tag_filter": "ARAMCO.*",
                "sync_mode": "last_24h",
                "time_zone": "Asia/Riyadh",
                "is_demo": True
            },
            is_active=True,
            demo_stream_active=True
        )
        db.add(pi_integration)
        print(f"  Created Demo PI System integration for {tenant.code}")
    
    if not existing_demo:
        demo_integration = TenantIntegration(
            tenant_id=tenant.id,
            name="Demo Data Generator - ARAMCO",
            integration_type="demo",
            status="active",
            config={
                "data_frequency_seconds": 30,
                "num_tags": 50,
                "anomaly_probability": 0.05,
                "is_demo": True
            },
            is_active=True,
            demo_stream_active=True
        )
        db.add(demo_integration)
        print(f"  Created Demo Data Generator for {tenant.code}")
    
    existing_cost_model = db.query(TenantCostModel).filter(
        TenantCostModel.tenant_id == tenant.id,
        TenantCostModel.is_active == True
    ).first()
    
    if not existing_cost_model:
        cost_model = TenantCostModel(
            tenant_id=tenant.id,
            name="ARAMCO Default Cost Model",
            description="Standard cost model for oil & gas operations",
            default_downtime_cost_per_hour=25000,
            risk_appetite="medium",
            cost_per_asset_family={
                "pump": 8000,
                "compressor": 20000,
                "valve": 3000,
                "motor": 12000,
                "turbine": 35000,
                "heat_exchanger": 15000,
                "separator": 18000
            },
            production_value_per_unit=50000,
            currency="SAR",
            is_active=True
        )
        db.add(cost_model)
        print(f"  Created default cost model for {tenant.code}")
    
    db.commit()
    
    seed_demo_signal_mappings(db, tenant)
    seed_demo_ai_scores(db, tenant)
    seed_demo_blackbox_data(db, tenant)

def seed_demo_signal_mappings(db: Session, tenant: Tenant):
    """Seed demo signal mappings connecting assets to integrations"""
    demo_integration = db.query(TenantIntegration).filter(
        TenantIntegration.tenant_id == tenant.id,
        TenantIntegration.integration_type == "demo",
        TenantIntegration.is_active == True
    ).first()
    
    if not demo_integration:
        return
    
    assets = db.query(Asset).filter(Asset.tenant_id == tenant.id).all()
    
    for asset in assets:
        existing_mapping = db.query(ExternalSignalMapping).filter(
            ExternalSignalMapping.tenant_id == tenant.id,
            ExternalSignalMapping.asset_id == asset.id,
            ExternalSignalMapping.integration_id == demo_integration.id
        ).first()
        
        if not existing_mapping:
            metrics = [
                {"tag": f"{asset.code}.Temperature", "metric": "temperature", "unit": "°C"},
                {"tag": f"{asset.code}.Pressure", "metric": "pressure", "unit": "bar"},
                {"tag": f"{asset.code}.Vibration", "metric": "vibration", "unit": "mm/s"},
                {"tag": f"{asset.code}.Current", "metric": "current", "unit": "A"},
            ]
            
            for m in metrics:
                mapping = ExternalSignalMapping(
                    tenant_id=tenant.id,
                    integration_id=demo_integration.id,
                    asset_id=asset.id,
                    external_tag=m["tag"],
                    internal_metric_name=m["metric"],
                    unit=m["unit"],
                    scaling_factor=1.0,
                    offset_value=0.0,
                    is_active=True
                )
                db.add(mapping)
    
    db.commit()
    print(f"  Created signal mappings for {len(assets)} assets in {tenant.code}")

def seed_demo_ai_scores(db: Session, tenant: Tenant):
    """Generate demo AI scores for assets"""
    import random
    from datetime import datetime
    
    assets = db.query(Asset).filter(Asset.tenant_id == tenant.id).all()
    
    for asset in assets:
        existing_score = db.query(AssetAIScore).filter(
            AssetAIScore.tenant_id == tenant.id,
            AssetAIScore.asset_id == asset.id
        ).first()
        
        if not existing_score:
            if asset.criticality == "critical":
                health = random.uniform(60, 85)
                failure_prob = random.uniform(0.05, 0.15)
                rul = random.randint(30, 90)
            elif asset.criticality == "high":
                health = random.uniform(70, 92)
                failure_prob = random.uniform(0.02, 0.08)
                rul = random.randint(60, 180)
            else:
                health = random.uniform(80, 98)
                failure_prob = random.uniform(0.01, 0.04)
                rul = random.randint(120, 365)
            
            ai_score = AssetAIScore(
                tenant_id=tenant.id,
                asset_id=asset.id,
                health_score=round(health, 2),
                failure_probability=round(failure_prob, 4),
                remaining_useful_life_days=rul,
                production_risk_index=round(random.uniform(10, 50), 2),
                anomaly_detected=random.random() < 0.1,
                anomaly_details={"type": "vibration_spike", "severity": "low"} if random.random() < 0.1 else None,
                model_version="v1.0-demo"
            )
            db.add(ai_score)
    
    db.commit()
    print(f"  Created AI scores for {len(assets)} assets in {tenant.code}")

def seed_demo_blackbox_data(db: Session, tenant: Tenant):
    """Seed demo Black Box events and incidents"""
    import random
    import uuid
    from datetime import timedelta
    
    existing_events = db.query(BlackBoxEvent).filter(
        BlackBoxEvent.tenant_id == tenant.id
    ).count()
    
    if existing_events > 0:
        return
    
    assets = db.query(Asset).filter(Asset.tenant_id == tenant.id).all()
    if not assets:
        return
    
    event_templates = [
        {"source": "OPC-UA", "source_type": "SENSOR", "category": "THRESHOLD", "severity": "WARNING", "summary": "Temperature above threshold"},
        {"source": "OPC-UA", "source_type": "SENSOR", "category": "ANOMALY", "severity": "CRITICAL", "summary": "Vibration spike detected"},
        {"source": "PI_SYSTEM", "source_type": "HISTORIAN", "category": "ALERT", "severity": "INFO", "summary": "Maintenance scheduled"},
        {"source": "PI_SYSTEM", "source_type": "HISTORIAN", "category": "THRESHOLD", "severity": "WARNING", "summary": "Pressure deviation"},
        {"source": "AI_ENGINE", "source_type": "AI", "category": "PREDICTION", "severity": "CRITICAL", "summary": "Predicted failure in 7 days"},
        {"source": "CMMS", "source_type": "WORK_ORDER", "category": "MAINTENANCE", "severity": "INFO", "summary": "PM completed"},
    ]
    
    now = datetime.utcnow()
    events_created = []
    
    for i in range(20):
        template = random.choice(event_templates)
        asset = random.choice(assets)
        event_time = now - timedelta(hours=random.randint(1, 72))
        
        event = BlackBoxEvent(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            asset_id=asset.id,
            source_system=template["source"],
            source_type=template["source_type"],
            event_category=template["category"],
            event_time=event_time,
            severity=template["severity"],
            summary=template["summary"],
            payload={
                "asset_code": asset.code,
                "asset_name": asset.name,
                "raw_value": round(random.uniform(50, 150), 2),
                "threshold": 100,
                "is_demo": True
            }
        )
        db.add(event)
        events_created.append(event)
    
    db.flush()
    
    critical_events = [e for e in events_created if e.severity == "CRITICAL"]
    if critical_events:
        incident = BlackBoxIncident(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            incident_number=f"INC-{tenant.code[:3]}-001",
            root_asset_id=critical_events[0].asset_id,
            incident_type="FAILURE",
            severity="MAJOR",
            status="INVESTIGATING",
            title="Critical Asset Health Alert",
            description="Multiple critical events detected on asset requiring investigation",
            start_time=critical_events[0].event_time,
            rca_status="PENDING"
        )
        db.add(incident)
        db.flush()
        
        for event in critical_events[:3]:
            incident_event = BlackBoxIncidentEvent(
                tenant_id=tenant.id,
                incident_id=incident.id,
                event_id=event.id,
                role="CAUSE" if event == critical_events[0] else "SYMPTOM"
            )
            db.add(incident_event)
    
    db.commit()
    print(f"  Created {len(events_created)} Black Box events and 1 incident for {tenant.code}")

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
app.include_router(blackbox_router)
app.include_router(twin_router)
app.include_router(tenant_users_router)

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

@app.get("/blackbox/incidents", response_class=HTMLResponse)
async def blackbox_incidents_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    if current_user.role not in ["platform_owner", "tenant_admin", "optimization_engineer", "engineer"]:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    lang = get_lang(request)
    trans = get_translation(lang)
    
    return templates.TemplateResponse("blackbox/incidents.html", {
        "request": request,
        "t": trans,
        "lang": lang,
        "rtl": lang == "ar",
        "user": current_user
    })

@app.get("/blackbox/incidents/{incident_id}", response_class=HTMLResponse)
async def blackbox_incident_detail_page(
    incident_id: str,
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    if current_user.role not in ["platform_owner", "tenant_admin", "optimization_engineer", "engineer"]:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    lang = get_lang(request)
    trans = get_translation(lang)
    
    return templates.TemplateResponse("blackbox/incident_detail.html", {
        "request": request,
        "t": trans,
        "lang": lang,
        "rtl": lang == "ar",
        "user": current_user,
        "incident_id": incident_id
    })

@app.get("/blackbox/incidents/{incident_id}/report", response_class=HTMLResponse)
async def blackbox_incident_report_page(
    incident_id: str,
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    if current_user.role not in ["platform_owner", "tenant_admin", "optimization_engineer", "engineer"]:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    lang = get_lang(request)
    trans = get_translation(lang)
    
    return templates.TemplateResponse("blackbox/report.html", {
        "request": request,
        "t": trans,
        "lang": lang,
        "rtl": lang == "ar",
        "user": current_user,
        "incident_id": incident_id
    })

@app.get("/digital-twin", response_class=HTMLResponse)
async def digital_twin_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    lang = get_lang(request)
    trans = get_translation(lang)
    
    return templates.TemplateResponse("twins/index.html", {
        "request": request,
        "t": trans,
        "lang": lang,
        "rtl": lang == "ar",
        "user": current_user
    })

@app.get("/twins", response_class=HTMLResponse)
async def twins_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    if current_user.role not in ["platform_owner", "tenant_admin", "optimization_engineer"]:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    lang = get_lang(request)
    trans = get_translation(lang)
    
    return templates.TemplateResponse("twins/layouts.html", {
        "request": request,
        "t": trans,
        "lang": lang,
        "rtl": lang == "ar",
        "user": current_user
    })

@app.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    if current_user.role not in ["platform_owner", "tenant_admin"]:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    lang = get_lang(request)
    trans = get_translation(lang)
    
    return templates.TemplateResponse("users/index.html", {
        "request": request,
        "t": trans,
        "lang": lang,
        "rtl": lang == "ar",
        "user": current_user
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
