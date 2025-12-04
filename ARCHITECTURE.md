# OPTRIA IQ - Industrial Operations Optimization Platform

## Architecture Document

**Version:** 1.0.0  
**Date:** December 2024  
**Status:** Production-Ready Blueprint

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OPTRIA IQ PLATFORM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    FRONTEND LAYER (Jinja2 SSR)                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │  Landing    │  │  Dashboard  │  │ Optimization│  │ Integrations│  │   │
│  │  │  Page (AR/EN)│  │  (per role) │  │  Scenarios  │  │  Management │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    BACKEND LAYER (FastAPI)                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │    Auth     │  │    RBAC     │  │  Tenancy    │  │    APIs     │  │   │
│  │  │   (JWT)     │  │ Capabilities│  │  Isolation  │  │  (REST)     │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│         ┌──────────────────────────┼──────────────────────────┐             │
│         ▼                          ▼                          ▼             │
│  ┌─────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐     │
│  │   AI SERVICE    │  │ OPTIMIZATION ENGINE │  │ INTEGRATIONS LAYER  │     │
│  │  ┌───────────┐  │  │  ┌───────────────┐  │  │  ┌───────────────┐  │     │
│  │  │ Health    │  │  │  │ Maintenance   │  │  │  │ OPC-UA        │  │     │
│  │  │ Score     │  │  │  │ Prioritization│  │  │  │ Connector     │  │     │
│  │  ├───────────┤  │  │  ├───────────────┤  │  │  ├───────────────┤  │     │
│  │  │ Failure   │  │  │  │ Deferral Cost │  │  │  │ PI Historian  │  │     │
│  │  │ Probability│  │  │  │ Analysis      │  │  │  │ Connector     │  │     │
│  │  ├───────────┤  │  │  ├───────────────┤  │  │  ├───────────────┤  │     │
│  │  │ RUL       │  │  │  │ Production    │  │  │  │ SAP PM        │  │     │
│  │  │ Estimation│  │  │  │ Risk Optim.   │  │  │  │ Connector     │  │     │
│  │  ├───────────┤  │  │  ├───────────────┤  │  │  ├───────────────┤  │     │
│  │  │ Anomaly   │  │  │  │ Workforce     │  │  │  │ Oracle EAM    │  │     │
│  │  │ Detection │  │  │  │ Dispatch      │  │  │  │ Connector     │  │     │
│  │  └───────────┘  │  │  └───────────────┘  │  │  └───────────────┘  │     │
│  └─────────────────┘  └─────────────────────┘  └─────────────────────┘     │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    DATABASE LAYER (PostgreSQL/Neon)                   │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │   Core      │  │    AI &     │  │Optimization │  │ Integration │  │   │
│  │  │   Schema    │  │  Telemetry  │  │   Results   │  │   Configs   │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Multi-Tenant & RBAC Model

### 2.1 Tenant Structure

Each tenant represents an organization (e.g., ARAMCO, SABIC, SEC) with:
- Isolated data (all business tables have `tenant_id`)
- Separate integrations configuration
- Role-based user access within tenant

### 2.2 User Roles

| Role | Description |
|------|-------------|
| `platform_owner` | Super admin - manages all tenants, platform-wide settings |
| `tenant_admin` | Tenant administrator - full access within their tenant |
| `optimization_engineer` | Runs and manages optimization scenarios |
| `engineer` | Field engineer - views assigned work, optimization suggestions |
| `viewer` | Read-only access to dashboards and reports |

### 2.3 RBAC Capability Matrix

| Capability | platform_owner | tenant_admin | optimization_engineer | engineer | viewer |
|------------|:--------------:|:------------:|:---------------------:|:--------:|:------:|
| manage_tenants | ✓ | - | - | - | - |
| manage_all_users | ✓ | - | - | - | - |
| manage_tenant_users | ✓ | ✓ | - | - | - |
| manage_integrations | ✓ | ✓ | - | - | - |
| run_optimization | ✓ | ✓ | ✓ | - | - |
| approve_optimization | ✓ | ✓ | - | - | - |
| view_optimization | ✓ | ✓ | ✓ | ✓ | ✓ |
| manage_assets | ✓ | ✓ | ✓ | - | - |
| view_assets | ✓ | ✓ | ✓ | ✓ | ✓ |
| manage_work_orders | ✓ | ✓ | ✓ | ✓ | - |
| view_work_orders | ✓ | ✓ | ✓ | ✓ | ✓ |
| view_audit_logs | ✓ | ✓ | - | - | - |

### 2.4 Tenant Isolation Enforcement

1. **Database Layer**: All queries include `WHERE tenant_id = :current_tenant_id`
2. **API Layer**: Middleware validates tenant access before route execution
3. **UI Layer**: Template context includes only tenant-scoped data

---

## 3. Technology Stack

### Backend
- **Framework**: Python 3.11 + FastAPI
- **ORM**: SQLAlchemy 2.0
- **Auth**: python-jose (JWT) + passlib (bcrypt)
- **Validation**: Pydantic v2

### Frontend
- **Templating**: Jinja2 (SSR)
- **Styling**: TailwindCSS
- **Interactivity**: Alpine.js + HTMX (minimal JS)
- **Charts**: Chart.js

### Database
- **PostgreSQL** via Neon (cloud-hosted)
- **Migrations**: Additive only (no destructive operations)

### Optimization
- **Solver**: PuLP (linear/integer programming)
- **Fallback**: Heuristic algorithms for Replit CPU constraints

---

## 4. Security Measures

1. **Authentication**: JWT tokens in HTTPOnly cookies
2. **CSRF Protection**: Token-based for all POST/PUT/DELETE
3. **Rate Limiting**: In-memory rate limiter on auth endpoints
4. **Password Security**: bcrypt hashing with salt
5. **Input Validation**: Pydantic schemas for all inputs
6. **SQL Injection Prevention**: SQLAlchemy parameterized queries
7. **CSP Headers**: Strict Content Security Policy
8. **Audit Logging**: All critical actions logged with user/tenant context

---

## 5. Bilingual Support (Arabic/English)

- Arabic is the default language (RTL layout)
- English toggle via `?lang=en` query parameter
- All UI strings stored in translation dictionaries
- Date/number formatting localized

---

## 6. Deployment on Replit

- Single process runs FastAPI with Uvicorn
- Background tasks via APScheduler (in-process)
- Database connection via `DATABASE_URL` environment variable
- Demo mode for showcasing without real integrations

---

## 7. Assumptions

1. **No GPU required**: AI models are statistical/heuristic (CPU-only)
2. **Demo mode default**: Real industrial connectors (OPC-UA, PI) are stubbed
3. **Single timezone**: Server timezone used for all scheduling
4. **No file uploads**: Asset data comes from integrations, not manual uploads
