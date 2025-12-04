# OPTRIA IQ - Industrial Operations Optimization Platform

## Overview
OPTRIA IQ is an enterprise-grade Industrial Operations Optimization Platform targeting major industrial players (ARAMCO, SABIC, SEC). The platform combines AI and quantitative optimization to help industrial companies optimize maintenance, reduce costs, minimize production risk, and optimize workforce dispatch.

## Technology Stack
- **Backend**: FastAPI with Python 3.11
- **Frontend**: Jinja2 templates with Tailwind CSS (CDN) + Alpine.js
- **Database**: PostgreSQL (Neon-backed via Replit)
- **Authentication**: JWT tokens with bcrypt password hashing
- **Optimization**: PuLP for linear programming optimization

## Project Structure
```
├── main.py                 # FastAPI application entry point
├── config.py               # Application configuration
├── models/                 # SQLAlchemy database models
│   ├── base.py             # Database engine and session
│   ├── tenant.py           # Multi-tenant model
│   ├── user.py             # User model with RBAC
│   ├── asset.py            # Asset, Site, Component models
│   ├── optimization.py     # Optimization models
│   └── integration.py      # Integration and audit models
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
│   ├── integrations.py     # Data integrations
│   ├── work_orders.py      # Work order management
│   └── health.py           # Health check endpoints
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Base template
│   ├── app_base.html       # Authenticated app layout
│   ├── landing.html        # Public landing page
│   ├── auth/               # Authentication pages
│   ├── dashboard/          # Dashboard views
│   ├── optimization/       # Optimization pages
│   ├── assets/             # Asset management pages
│   ├── integrations/       # Integration pages
│   ├── work_orders/        # Work order pages
│   └── admin/              # Admin pages
├── translations/           # Bilingual support
│   ├── ar.py               # Arabic translations
│   └── en.py               # English translations
└── static/                 # Static assets
    ├── js/                 # JavaScript files
    └── css/                # CSS files
```

## Key Features

### 1. Multi-Tenant Architecture
- Complete tenant isolation with `tenant_id` on all business tables
- Tenant-specific settings and configurations
- Platform owner can manage multiple tenants

### 2. RBAC (Role-Based Access Control)
Roles and their capabilities:
- **platform_owner**: Full platform access, manage tenants
- **tenant_admin**: Full tenant access, manage users
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
- OPC-UA connector
- PI Historian connector
- SAP PM connector
- SQL database connector
- Demo data connector

### 6. Bilingual Support
- Arabic (default)
- English
- RTL layout support

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

## API Endpoints

### Health
- `GET /health/live` - Liveness check
- `GET /health/ready` - Readiness check with component status

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

### Work Orders
- `GET /api/work-orders/` - List work orders
- `POST /api/work-orders/` - Create work order
- `PUT /api/work-orders/{id}` - Update work order

## Running the Application
The application runs on port 5000:
```bash
python main.py
```

## Environment Variables
- `DATABASE_URL` - PostgreSQL connection string
- `SESSION_SECRET` - JWT secret key

## Recent Changes
- 2024-12-04: Initial platform build with complete feature set
- Multi-tenant architecture with RBAC
- Four optimization models implemented
- Bilingual support (Arabic/English)
- Industrial data connectors (OPC-UA, PI, SAP, SQL)
- AI scoring and predictions
