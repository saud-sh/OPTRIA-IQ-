# OPTRIA IQ - Project Implementation Plan

## Overview

This document outlines the phased implementation approach for OPTRIA IQ, the Industrial Operations Optimization Platform.

---

## Phase 1: Foundation (Core Infrastructure)

### Scope
- Project structure and configuration
- Database schema and models
- Authentication system (JWT + cookies)
- RBAC capabilities framework
- Multi-tenant isolation

### Deliverables
- FastAPI application structure
- SQLAlchemy models for all core entities
- Auth endpoints (login, logout, session management)
- RBAC decorators and middleware
- Tenant management for platform_owner

### Tests
- [ ] Database connection verified
- [ ] User registration/login works
- [ ] JWT tokens issued correctly
- [ ] Role-based access enforced
- [ ] Tenant isolation verified

### Done Checklist
- [ ] All core models created with tenant_id
- [ ] Auth flow complete with HTTPOnly cookies
- [ ] Platform owner can create tenants
- [ ] Tenant admin auto-created per tenant

---

## Phase 2: Integrations & Data Ingestion

### Scope
- BaseConnector abstraction
- Connector implementations (OPC-UA, PI, SAP, Oracle, SQL, REST)
- Demo connectors with simulated data
- Integration management API and UI
- Signal/tag mapping to internal assets

### Deliverables
- Connector framework with health checks
- CRUD API for integrations
- Data mapping configuration
- Demo data generator (background task)

### Tests
- [ ] Demo connector generates data
- [ ] Integration CRUD works per tenant
- [ ] Test connection endpoint responds
- [ ] Signal mappings stored correctly

### Done Checklist
- [ ] All connector types defined
- [ ] Integration UI functional
- [ ] Demo mode active without real systems

---

## Phase 3: AI Service Layer

### Scope
- Health score computation
- Failure probability estimation
- Remaining Useful Life (RUL) calculation
- Anomaly detection
- Production risk indexing

### Deliverables
- `core/ai_service.py` module
- Background processor for AI metrics
- API endpoints for AI results
- Asset detail pages with AI data

### Tests
- [ ] Health scores computed for assets
- [ ] Failure probability within [0,1]
- [ ] RUL expressed in days/hours
- [ ] Anomaly flags generated

### Done Checklist
- [ ] AI service fully functional
- [ ] Background processor running
- [ ] Results stored in database

---

## Phase 4: Optimization Engine

### Scope
- Maintenance Prioritization optimizer
- Deferral Cost analysis
- Production Risk optimization
- Workforce Dispatch optimization
- Optimization run management

### Deliverables
- `core/optimization_engine.py` module
- Optimization problem classes
- API endpoints under `/api/optimization/`
- Optimization results storage

### Tests
- [ ] Each optimizer produces valid output
- [ ] Results stored in database
- [ ] API returns recommendations
- [ ] Tenant isolation maintained

### Done Checklist
- [ ] All 4 optimizers implemented
- [ ] Optimization runs tracked
- [ ] Recommendations persisted

---

## Phase 5: Frontend & UX

### Scope
- Bilingual landing page (Arabic/English)
- App layout with responsive sidebar
- Role-based dashboards
- Optimization scenario UI
- Assets, Work Orders, Integrations pages
- Audit logs viewer

### Deliverables
- Jinja2 templates for all pages
- TailwindCSS styling
- Chart.js visualizations
- Alpine.js interactivity

### Tests
- [ ] Landing page renders in AR/EN
- [ ] Dashboard shows role-specific content
- [ ] Optimization UI triggers runs
- [ ] All pages responsive

### Done Checklist
- [ ] All templates created
- [ ] Bilingual support complete
- [ ] Modern, professional design

---

## Phase 6: Polish & Production Readiness

### Scope
- Demo tenant seeding
- Health endpoints (/health/ready, /health/live)
- Security hardening
- Final testing and validation
- Documentation

### Deliverables
- Demo tenants (ARAMCO_DEMO, POWER_DEMO, WATER_DEMO)
- Seeded assets, sites, failure modes
- Health check endpoints
- Security scan results

### Tests
- [ ] Health endpoints return 200
- [ ] No route returns 500 in normal flow
- [ ] No secrets in logs
- [ ] RBAC enforced everywhere

### Done Checklist
- [ ] Demo ready for client presentation
- [ ] All documentation complete
- [ ] Platform fully operational

---

## Environment Variables Required

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `SESSION_SECRET` | Secret for session encryption | Yes |
| `DEMO_MODE` | Enable demo data generation | Optional (default: true) |

---

## Success Criteria

1. Multi-tenant SaaS fully operational
2. All 4 optimization types functional
3. Bilingual UI (Arabic default)
4. Demo mode works without external systems
5. Enterprise-ready for ARAMCO/SABIC presentations
