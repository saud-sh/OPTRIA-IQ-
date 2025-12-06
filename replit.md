# OPTRIA IQ - Industrial Operations Optimization Platform

## Overview
OPTRIA IQ is an enterprise-grade Industrial Operations Optimization Platform targeting major industrial players (ARAMCO, SABIC, SEC). The platform combines AI and quantitative optimization to help industrial companies optimize maintenance, reduce costs, minimize production risk, and optimize workforce dispatch.

**Status**: PRODUCTION READY

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI with Python 3.11 |
| Frontend | Jinja2 templates + Tailwind CSS (CDN) + Alpine.js |
| Database | PostgreSQL (Neon-backed via Replit) |
| Authentication | JWT tokens with bcrypt password hashing |
| Optimization | PuLP for linear programming |
| ORM | SQLAlchemy 2.0 |

## Python Dependencies
apscheduler, bcrypt, email-validator, fastapi, flask-dance, flask-login, httpx, itsdangerous, jinja2, oauthlib, passlib, psycopg2-binary, pulp, pydantic, pydantic-settings, pyjwt, python-jose, python-multipart, sqlalchemy, uvicorn

## Project Structure
```
main.py                     - FastAPI application entry point
config.py                   - Application configuration & secrets
models/                     - SQLAlchemy database models
  base.py, tenant.py, user.py, asset.py, optimization.py, integration.py, blackbox.py
core/                       - Core business logic
  auth.py, rbac.py, ai_service.py, optimization_engine.py, blackbox_engine.py
  connectors/ (base.py, demo.py, opcua.py, pi.py, sap.py, sql.py)
routers/                    - API endpoints
  auth.py, tenants.py, assets.py, optimization.py, integrations.py, work_orders.py, blackbox.py, twin.py, health.py
templates/                  - Jinja2 HTML templates
  base.html, app_base.html, landing.html, auth/, dashboard/, optimization/, assets/, integrations/, onboarding/, work_orders/, blackbox/, twins/, admin/
translations/               - ar.py (Arabic), en.py (English)
scripts/smoke_test_e2e.py   - E2E verification tests
```

## Database Schema (22 Tables)

### Core Tables
- **tenants**: id, code, name, name_ar, industry, status, settings
- **users**: id, tenant_id, email, username, password_hash, role, full_name, is_active

### Asset Tables
- **sites**: id, tenant_id, code, name, location, site_type, latitude, longitude
- **assets**: id, tenant_id, site_id, code, name, asset_type, manufacturer, criticality, status
- **asset_components**: id, tenant_id, asset_id, code, name, component_type
- **asset_failure_modes**: id, tenant_id, asset_id, code, severity, occurrence, detection
- **asset_metrics_snapshots**: id, tenant_id, asset_id, metric_name, metric_value, recorded_at
- **asset_ai_scores**: id, tenant_id, asset_id, health_score, failure_probability, remaining_useful_life_days
- **alerts**: id, tenant_id, asset_id, alert_type, severity, title, status

### Optimization Tables
- **optimization_cost_models**: id, tenant_id, cost_per_hour_downtime, cost_per_failure
- **optimization_runs**: id, tenant_id, run_type, status, input_parameters, output_summary
- **optimization_scenarios**: id, tenant_id, run_id, name, total_cost, total_risk_score
- **optimization_recommendations**: id, tenant_id, asset_id, priority_score, action_title
- **work_orders**: id, tenant_id, asset_id, code, title, work_type, priority, status

### Integration Tables
- **tenant_integrations**: id, tenant_id, name, integration_type, config, status
- **external_signal_mappings**: id, tenant_id, integration_id, asset_id, external_tag, internal_metric_name
- **tenant_identity_providers**: id, tenant_id, provider_type, client_id, issuer_url
- **tenant_onboarding_progress**: id, tenant_id, steps, status
- **tenant_cost_models**: id, tenant_id, default_downtime_cost_per_hour, risk_appetite
- **integration_action_logs**: id, tenant_id, integration_id, action, status
- **audit_logs**: id, tenant_id, user_id, action, entity_type, entity_id

### Black Box Tables
- **blackbox_events**: id (UUID), tenant_id, asset_id, source_system, event_time, severity, summary, payload
- **blackbox_incidents**: id (UUID), tenant_id, incident_number, incident_type, severity, status, rca_status, rca_summary
- **blackbox_incident_events**: id, tenant_id, incident_id, event_id, role (CAUSE/SYMPTOM/CONTEXT)
- **blackbox_rca_rules**: id, tenant_id, name, pattern, root_cause_category, confidence

### Digital Twin Tables
- **twin_layouts**: id, tenant_id, site_id, name, description, config (JSONB), width, height, background_color, is_active, is_default
- **twin_nodes**: id, tenant_id, layout_id, asset_id, node_type, label, position_x, position_y, width, height, rotation, color, style (JSONB), data_bindings (JSONB)

## RBAC Capabilities

| Resource | platform_owner | tenant_admin | optimization_engineer | engineer | viewer |
|----------|----------------|--------------|----------------------|----------|--------|
| Tenants | CRUD | Read own | - | - | - |
| Users | CRUD all | CRUD tenant | - | - | - |
| Sites/Assets | CRUD | CRUD | CRUD | Read | Read |
| Alerts | CRUD | CRUD | CRUD | Read | Read |
| Work Orders | CRUD | CRUD | CRUD | CRUD | Read |
| Optimization | CRUD | CRUD | CRUD | Read | Read |
| Integrations | CRUD | CRUD | Read | - | - |
| Black Box | CRUD | CRUD | CRUD | Read | - |
| Diagnostics | Full | - | - | - | - |

## UI Pages

### Public
- `/` - Landing page
- `/login` - Login page

### Authenticated (Sidebar)
- `/dashboard` - Main dashboard with KPIs
- `/optimization` - Optimization runs & recommendations
- `/assets` - Asset management
- `/integrations` - Integration management (4 tabs: Data Sources, Signal Mappings, SSO/Identity, Cost Model)
- `/work-orders` - Work order management
- `/blackbox/incidents` - Industrial Black Box (engineer+)
- `/blackbox/incidents/{id}` - Incident detail with timeline
- `/blackbox/incidents/{id}/report` - Printable report
- `/twins` - Digital Twin layouts & visualization (optimization_engineer+)
- `/onboarding` - Setup wizard (tenant_admin+)
- `/admin/tenants` - Tenant management (platform_owner)

## API Endpoints

### Health: GET /health, /health/live, /health/ready, /health/internal/config/status
### Auth: POST /api/auth/login, /api/auth/logout, GET /api/auth/me, GET /api/auth/check
### Tenants: GET/POST /api/tenants/, GET/PUT /api/tenants/{id}, GET /api/tenants/{id}/users
### Assets: GET/POST /api/assets/sites, GET/POST /api/assets/, GET /api/assets/{id}, GET /api/assets/{id}/metrics, GET /api/assets/{id}/ai-scores
### Optimization: POST /api/optimization/run, GET /api/optimization/runs, /api/optimization/recommendations
### Integrations: GET/POST /api/integrations/, POST /api/integrations/{id}/test, /api/integrations/{id}/demo-stream/{action}, GET/POST /api/integrations/mappings, /api/integrations/identity-providers, GET /api/integrations/cost-models/active
### Work Orders: GET/POST /api/work-orders/, GET/PUT /api/work-orders/{id}, POST /api/work-orders/{id}/start, POST /api/work-orders/{id}/complete
### Black Box: GET /api/blackbox/events, /api/blackbox/incidents, PUT /api/blackbox/incidents/{id}, POST /api/blackbox/incidents/{id}/rca, GET /api/blackbox/stats, POST /api/blackbox/engine/collect, /api/blackbox/engine/detect, /api/blackbox/engine/run, GET /api/blackbox/reports/{id}
### Digital Twin: GET/POST /api/twins/layouts, GET/PUT/DELETE /api/twins/layouts/{id}, POST /api/twins/layouts/{id}/nodes, PUT/DELETE /api/twins/nodes/{id}, GET /api/twins/layouts/{id}/nodes

## Key Features

1. **Multi-Tenant Architecture**: Complete tenant isolation with tenant_id on all tables
2. **Four Optimization Models**: Maintenance Prioritization, Deferral Cost Analysis, Production Risk, Workforce Dispatch
3. **AI Services**: Health scores, failure probability, RUL, anomaly detection
4. **Industrial Integrations**: OPC-UA, PI System, SAP PM, SQL databases, Demo connector
5. **Integration Management UI**: 4 tabs for data sources, signal mappings, SSO, cost models
6. **Onboarding Wizard**: 6-step guided setup with auto-detection
7. **Industrial Black Box**: Event collection, incident detection, RCA, timeline replay, printable reports
8. **Digital Twin Visualization**: Layout management with asset-to-node binding, configurable node types and styling
9. **Bilingual Support**: Arabic (RTL) and English (LTR)

## Environment Variables

### Required
- `DATABASE_URL` - PostgreSQL connection string
- `SESSION_SECRET` - JWT signing key

### Optional
- `DEMO_MODE` (true) - Enable demo connector
- `APP_ENV` (development) - Environment level
- `OPTIMIZATION_ENGINE_ENABLED` (true) - Enable optimization
- `PI_BASE_URL`, `SAP_BASE_URL`, `OPCUA_USERNAME`, `OPCUA_PASSWORD` - Connector defaults

## Demo Credentials
- **Platform Owner**: admin@optria.io / OptriA2024!
- **Tenant Admin (ARAMCO)**: demo@aramco.com / Demo2024!
- **Engineer (ARAMCO)**: engineer@aramco.com / Engineer2024!

## Running
```bash
python main.py              # Start on port 5000
python scripts/smoke_test_e2e.py  # Run tests
```

## Recent Changes

### 2025-12-06: Integration Data Flow & Bug Fixes
- Added BASE_URL to config.py for global integration defaults
- Enhanced /health/internal/config/status with PI, SAP, OPC-UA default configuration visibility
- Created seed_existing_demo_tenant() for auto-provisioning integrations on startup
- Fixed Digital Twin asset detail endpoint field references (root_asset_id, start_time, computed_at)
- Fixed integration smoke test authentication (checks access_token instead of success flag)
- Integration smoke test now handles API list response format correctly
- All smoke tests pass (E2E and integration)

### 2025-12-06: Production Documentation & Final Polish
- Created README.md with quick start and project overview
- Created OPS_RUNBOOK.md with deployment and operations procedures
- Created TENANT_ONBOARDING.md with onboarding workflow guide
- Created SUMMARY.md with complete feature summary
- Fixed Alpine.js null reference errors in Digital Twin UI
- All templates responsive and polished

### 2025-12-06: Tenant User Management & Digital Twin Enhancement
- Tenant User Management API (routers/tenant_users.py) with full CRUD, password reset
- User Management UI at /users for tenant_admin and platform_owner roles
- auth_source field added to User model (local vs SSO)
- Query-level tenant isolation (filter before fetch, not after)
- Digital Twin Visualization at /digital-twin with asset connectivity status
- Assets API (GET /api/twins/assets, /api/twins/assets/{id}) with health and data status
- Data connectivity shows live/demo/disconnected based on signal mappings
- Digital Twin configuration remains at /twins for layout management

### 2025-12-06: Digital Twin Configuration
- Database models (TwinLayout, TwinNode) for visualization and asset binding
- Complete CRUD API endpoints with multi-tenant isolation
- Digital Twin UI at /twins with layout management and configuration
- Configurable node types, styling, positioning, and data bindings
- RBAC enforcement (optimization_engineer+ for management)

### 2025-12-05: Industrial Black Box
- Database models (BlackBoxEvent, BlackBoxIncident, BlackBoxIncidentEvent, BlackBoxRCARule)
- Event collection from alerts, work orders, AI outputs
- Incident detection engine with severity thresholds
- Rule-based RCA engine with pattern matching
- Black Box API endpoints with RBAC
- UI templates (incidents, detail, report)
- Sidebar navigation, bilingual support

### 2025-12-04: Final Verification
- Enhanced config.py with secret management
- Diagnostics endpoint /internal/config/status
- E2E smoke tests, onboarding wizard
- Integrations UI with 4 tabs

### 2025-12-04: Platform Build
- Multi-tenant architecture with RBAC
- Four optimization models
- Bilingual support, industrial connectors

## User Preferences
- Stack: FastAPI + Jinja2 + PostgreSQL (NO JS framework migration)
- Database: Additive changes only
- Multi-Tenancy: tenant_id enforcement on ALL tables
- RBAC: Strict role-based access control
- Quality: Production-ready with full verification
