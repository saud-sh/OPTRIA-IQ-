# OPTRIA IQ - Industrial Operations Optimization Platform

## Overview
OPTRIA IQ is an enterprise-grade Industrial Operations Optimization Platform targeting major industrial players (ARAMCO, SABIC, SEC). The platform combines AI and quantitative optimization to help industrial companies optimize maintenance, reduce costs, minimize production risk, and optimize workforce dispatch.

**Status**: ✅ FINAL VERIFICATION PHASE COMPLETE

## Technology Stack
- **Backend**: FastAPI with Python 3.11
- **Frontend**: Jinja2 templates with Tailwind CSS (CDN) + Alpine.js
- **Database**: PostgreSQL (Neon-backed via Replit)
- **Authentication**: JWT tokens with bcrypt password hashing
- **Optimization**: PuLP for linear programming optimization

## Project Structure
```
├── main.py                 # FastAPI application entry point
├── config.py               # Application configuration with secret management
├── models/                 # SQLAlchemy database models
│   ├── base.py             # Database engine and session
│   ├── tenant.py           # Multi-tenant model
│   ├── user.py             # User model with RBAC
│   ├── asset.py            # Asset, Site, Component models
│   ├── optimization.py     # Optimization models
│   └── integration.py      # Integration, mapping, SSO models
├── core/                   # Core business logic
│   ├── auth.py             # Authentication utilities
│   ├── rbac.py             # Role-based access control
│   ├── ai_service.py       # AI scoring and predictions
│   ├── optimization_engine.py  # Optimization algorithms
│   └── connectors/         # Industrial data connectors
│       ├── base.py         # Base connector class
│       ├── demo.py         # Demo data connector
│       ├── opcua.py        # OPC-UA connector
│       ├── pi.py           # PI Historian connector
│       ├── sap.py          # SAP PM connector
│       └── sql.py          # SQL database connector
├── routers/                # API endpoints
│   ├── auth.py             # Authentication endpoints
│   ├── tenants.py          # Tenant management
│   ├── assets.py           # Asset management
│   ├── optimization.py     # Optimization runs
│   ├── integrations.py     # Integration management
│   ├── work_orders.py      # Work order management
│   └── health.py           # Health check & diagnostics
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Base template
│   ├── app_base.html       # Authenticated app layout
│   ├── landing.html        # Public landing page
│   ├── auth/               # Authentication pages
│   ├── dashboard/          # Dashboard views
│   ├── optimization/       # Optimization pages
│   ├── assets/             # Asset management pages
│   ├── integrations/       # Integration management with 4 tabs
│   ├── onboarding/         # Setup wizard pages
│   ├── work_orders/        # Work order pages
│   └── admin/              # Admin pages
├── scripts/                # Utility scripts
│   └── smoke_test_e2e.py   # E2E CRUD verification tests
├── translations/           # Bilingual support
│   ├── ar.py               # Arabic translations
│   └── en.py               # English translations
└── static/                 # Static assets
```

## Key Features

### 1. Multi-Tenant Architecture
- Complete tenant isolation with `tenant_id` on all business tables
- Tenant-specific settings and configurations
- Platform owner can manage multiple tenants
- Verified with `require_tenant_access` decorator on all endpoints

### 2. RBAC (Role-Based Access Control)
Roles and their capabilities:
- **platform_owner**: Full platform access, manage tenants, access diagnostics
- **tenant_admin**: Full tenant access, manage users, setup integrations
- **optimization_engineer**: Run optimizations, manage assets
- **engineer**: View optimizations, manage work orders
- **viewer**: Read-only access

### 3. Four Optimization Models
1. **Maintenance Prioritization**: Ranks assets by maintenance urgency
2. **Deferral Cost Analysis**: Calculates cost of deferring maintenance
3. **Production Risk Optimization**: Minimizes production risk
4. **Workforce Dispatch**: Optimizes engineer scheduling

### 4. AI Services
- Health score calculation
- Failure probability prediction
- Remaining useful life estimation
- Anomaly detection
- Production risk assessment

### 5. Industrial Integrations
- **OPC-UA Connector**: Real-time industrial automation protocol
- **PI System Connector**: OSIsoft PI System / PI WebAPI
- **SAP PM / Oracle EAM**: Enterprise asset management systems
- **SQL Database Connector**: PostgreSQL, MySQL, SQL Server, Oracle
- **Demo Connector**: Simulated data for testing

### 6. Integration Management UI
- **Data Sources Tab**: View, create, test, and manage all integrations
- **Signal Mappings Tab**: Map external tags/signals to internal assets/metrics
- **SSO/Identity Tab**: Configure Azure AD, Okta, or Google SSO providers
- **Cost & Risk Model Tab**: Configure optimization parameters

### 7. Onboarding Wizard
- 6-step guided setup for tenant admins
- Auto-detection of completed steps based on actual data
- Integration setup verification
- Signal mapping guidance
- Cost model configuration

### 8. Bilingual Support
- Arabic (default, RTL layout)
- English (LTR layout)

## Environment Variables & Secret Management

### Required Secrets (Fail-Fast)
- `DATABASE_URL` - PostgreSQL connection (Neon-backed)
- `SESSION_SECRET` - JWT signing key
- `OPENAI_API_KEY` - AI/ML service access

### Optional Secrets (With Defaults)
- `DEMO_MODE` - Enable demo connector (default: true)
- `APP_ENV` - Environment level (default: development)
- `OPTIMIZATION_ENGINE_ENABLED` - Feature flag (default: true)
- `EXTERNAL_DB_ENABLE` - External DB integrations (default: true)
- `PI_BASE_URL` - PI System default endpoint (default: empty)
- `SAP_BASE_URL` - SAP PM default endpoint (default: empty)
- `OPCUA_USERNAME` - OPC-UA default username (default: empty)
- `OPCUA_PASSWORD` - OPC-UA default password (default: empty)

### Secret Usage
1. **Backend**: Read from `os.getenv()` in `config.py` with validation
2. **Integrations**: Used as global defaults, tenant configs override
3. **Feature Flags**: Control optimization and demo mode behavior
4. **Diagnostics**: `/internal/config/status` (platform_owner only) shows configuration without exposing secrets

## API Endpoints

### Health & Diagnostics
- `GET /health/live` - Liveness check
- `GET /health/ready` - Readiness with component status
- `GET /internal/config/status` - Configuration diagnostics (platform_owner only)

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Current user info

### Tenants
- `GET /api/tenants/` - List tenants
- `POST /api/tenants/` - Create tenant
- `GET /api/tenants/{id}` - Get tenant
- `PUT /api/tenants/{id}` - Update tenant

### Assets
- `GET /api/assets/` - List assets
- `POST /api/assets/` - Create asset
- `GET /api/assets/{id}` - Get asset details
- `GET /api/assets/{id}/metrics` - Asset metrics
- `GET /api/assets/{id}/ai-scores` - AI scores

### Optimization
- `POST /api/optimization/run` - Run optimization
- `GET /api/optimization/runs` - List runs
- `GET /api/optimization/runs/{id}` - Get run details
- `GET /api/optimization/recommendations` - List recommendations

### Integrations
- `GET /api/integrations/` - List integrations
- `POST /api/integrations/` - Create integration
- `POST /api/integrations/{id}/test` - Test connection
- `POST /api/integrations/{id}/demo-stream/{action}` - Control demo stream
- `GET /api/integrations/mappings` - List signal mappings
- `POST /api/integrations/mappings` - Create mapping
- `GET /api/integrations/identity-providers` - List SSO providers
- `POST /api/integrations/identity-providers` - Create SSO provider
- `GET /api/integrations/cost-models/active` - Get cost model

### Work Orders
- `GET /api/work-orders/` - List work orders
- `POST /api/work-orders/` - Create work order
- `PUT /api/work-orders/{id}` - Update work order

## Demo Credentials

### Platform Owner
- Email: admin@optria.io
- Password: OptriA2024!

### Tenant Admin (ARAMCO Demo)
- Email: demo@aramco.com
- Password: Demo2024!

### Engineer (ARAMCO Demo)
- Email: engineer@aramco.com
- Password: Engineer2024!

## Running the Application
The application runs on port 5000:
```bash
python main.py
```

## Verification & Testing

### Run Smoke Tests
```bash
python scripts/smoke_test_e2e.py
```

Tests end-to-end CRUD operations:
- Tenant creation and management
- User creation with RBAC
- Site and asset creation
- Alert creation and management
- Work order creation and updates
- Tenant isolation verification
- RBAC capability verification

### Check Configuration Status
```bash
curl http://localhost:5000/internal/config/status \
  -H "Authorization: Bearer <token>" | python -m json.tool
```

Shows system configuration without exposing secrets:
- Database connectivity
- AI service configuration
- Optimization engine status
- Feature flag states
- Integration default configurations

## Final Verification Status

✅ **Secrets Wiring**: All environment variables properly read and validated
✅ **CRUD Operations**: End-to-end flows verified (create/read/update/delete)
✅ **Tenant Isolation**: Multi-tenant filtering enforced on all queries
✅ **RBAC**: Role-based access control working correctly
✅ **Integration Management**: UI with 4 tabs + global defaults/tenant overrides
✅ **Feature Flags**: Demo mode and optimization flags respected
✅ **Diagnostics**: Internal config status endpoint for debugging
✅ **Documentation**: OPS_INTEGRATION_VERIFICATION.md with complete guidelines

## Recent Changes

- 2025-12-04: FINAL VERIFICATION PHASE
  - Enhanced `config.py` with comprehensive secret management
  - Added `/internal/config/status` diagnostics endpoint
  - Created `scripts/smoke_test_e2e.py` for E2E verification
  - Built comprehensive `OPS_INTEGRATION_VERIFICATION.md` report
  - Added onboarding wizard with 6-step setup guidance
  - Enhanced integrations UI with 4 management tabs
  - Implemented tenant-specific integration overrides

- 2025-12-04: Integrations & Onboarding
  - Comprehensive integrations management UI
  - Signal mapping UI with bulk operations
  - SSO provider configuration
  - Cost & risk model settings
  - Onboarding wizard with progress tracking

- 2025-12-04: Platform build completion
  - Multi-tenant architecture with RBAC
  - Four optimization models implemented
  - Bilingual support (Arabic/English)
  - Industrial data connectors
  - AI scoring and predictions

## User Preferences
- EXACT existing stack: FastAPI + Jinja2 templates + PostgreSQL (Neon)
- NO JavaScript framework migration required
- Additive DB changes only (no destructive migrations)
- Multi-tenant isolation with `tenant_id` enforcement on ALL tables
- Strict RBAC implementation
- Comprehensive integration management
- Production-ready with full verification

