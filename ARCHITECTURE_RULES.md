# OPTRIA IQ Architecture Rules

This document defines the hard constraints that govern the OPTRIA IQ codebase. These are non-negotiable architectural decisions that protect data integrity, multi-tenancy, security, and operational stability.

## Core Technology Stack

- **Backend**: FastAPI (Python 3.11)
- **Templates**: Jinja2 HTML + Tailwind CSS + Alpine.js
- **Database**: PostgreSQL (Neon-backed via Replit)
- **ORM**: SQLAlchemy 2.0
- **Authentication**: JWT tokens with bcrypt password hashing

## Hard Constraints

### 1. No Destructive Database Migrations

**RULE**: All schema changes must be additive only.

- ❌ NEVER use `DROP TABLE`, `DROP COLUMN`, or `CASCADE DELETE`
- ❌ NEVER ALTER existing column types
- ❌ NEVER DELETE or rename existing columns
- ✅ DO use `ALTER TABLE ADD COLUMN` for new fields
- ✅ DO create new tables instead of modifying existing ones
- ✅ DO deprecate columns by leaving them but not using them

**Why**: Neon's recovery tools and user data depend on schema integrity. Breaking changes cannot be safely rolled back.

### 2. Multi-Tenant Architecture

**RULE**: All business data tables MUST include `tenant_id`.

#### Table Requirements

Every business data table (except system tables like users sessions, etc.) must have:

```python
tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
```

#### Current Tables with tenant_id

- Tenants: `tenants` (root level)
- Users: `users` (tenant_id required for regular users)
- Assets: `sites`, `assets`, `asset_components`, `asset_failure_modes`, `asset_metrics_snapshots`, `asset_ai_scores`, `alerts`
- Optimization: `optimization_cost_models`, `optimization_runs`, `optimization_scenarios`, `optimization_recommendations`, `work_orders`
- Integrations: `tenant_integrations`, `external_signal_mappings`, `tenant_identity_providers`, `tenant_onboarding_progress`, `tenant_cost_models`, `integration_action_logs`
- Black Box: `blackbox_events`, `blackbox_incidents`, `blackbox_incident_events`, `blackbox_rca_rules`
- Digital Twin: `twin_layouts`, `twin_nodes`
- Audit: `audit_logs`

#### Query-Level Tenant Isolation

All queries must filter by `tenant_id` at the query level (not post-fetch):

```python
# ✅ CORRECT: Filter in query
asset = db.query(Asset).filter(
    Asset.id == asset_id,
    Asset.tenant_id == tenant_id
).first()

# ❌ WRONG: Fetch then filter
asset = db.query(Asset).filter(Asset.id == asset_id).first()
if asset and asset.tenant_id == tenant_id:
    ...
```

### 3. Role-Based Access Control (RBAC)

**RULE**: All endpoints must respect RBAC and tenant isolation.

#### Standard RBAC Roles

| Role | Capabilities |
|------|--------------|
| `platform_owner` | Full system access, manages all tenants |
| `tenant_admin` | Manages users and settings within their tenant |
| `optimization_engineer` | Runs optimizations, manages assets, creates work orders |
| `engineer` | Field operations, views assets, manages work orders |
| `viewer` | Read-only access to dashboards and reports |

#### Router Requirements

Every router must:

1. Import `has_capability` and `require_tenant_access` from `core.rbac`
2. Check permissions on every endpoint:

```python
from core.rbac import has_capability, require_tenant_access

@router.get("/...")
async def endpoint(current_user: User = Depends(get_current_user)):
    if not has_capability(current_user, "required_capability"):
        raise HTTPException(status_code=403, detail="Not authorized")
```

3. Always filter queries by `current_user.tenant_id` (except platform_owner)
4. Platform owners accessing tenant data must explicitly specify tenant_id

### 4. Feature Flags

**RULE**: All new modules must respect these environment variable flags.

| Flag | Default | Purpose |
|------|---------|---------|
| `DEMO_MODE` | `true` | Enable demo data connector and sample data |
| `OPTIMIZATION_ENGINE_ENABLED` | `true` | Enable optimization engine and runs |
| `EXTERNAL_DB_ENABLE` | `true` | Enable external database integrations |
| `APP_ENV` | `development` | Environment level (development/staging/production) |

Usage pattern:

```python
from config import settings

if settings.demo_mode:
    # Use demo connector
    pass

if settings.optimization_engine_enabled:
    # Run optimization
    pass

if settings.external_db_enable:
    # Enable integrations
    pass
```

### 5. Black Box and Digital Twin Modules

**RULE**: These are read-only observation and analysis layers. No control commands.

#### Black Box Layer

- **Purpose**: Event collection, incident detection, RCA
- **Data Sources**: Alerts, work orders, AI engine outputs, external integrations
- **Constraint**: READ-ONLY w.r.t OT/SCADA systems. No control commands to assets.
- **Tables**: `blackbox_events`, `blackbox_incidents`, `blackbox_incident_events`, `blackbox_rca_rules`
- **Router**: `routers/blackbox.py`

#### Digital Twin Layer

- **Purpose**: Asset visualization and connectivity monitoring
- **Data Sources**: Asset definitions, AI scores, signal mappings, connectivity status
- **Constraint**: READ-ONLY visualization. No control commands to assets or PLCs.
- **Tables**: `twin_layouts`, `twin_nodes`
- **Router**: `routers/twin.py`

Both modules observe the state of the industrial system but do not command it.

## Validation Checklist

### Before Adding a New Table

- [ ] Does it represent tenant business data? → Add `tenant_id`
- [ ] Does it need RBAC? → Add to `core/rbac.py` capabilities
- [ ] Can it be queried in isolation? → Verify no cross-tenant data leakage
- [ ] Does it have an index on `tenant_id`? → Critical for multi-tenant performance

### Before Adding a New Router

- [ ] Does it import `has_capability` from `core.rbac`?
- [ ] Does every endpoint check permissions?
- [ ] Do all queries filter by `tenant_id` or `current_user.tenant_id`?
- [ ] Does it respect all RBAC roles?
- [ ] Are any feature flags required? → Update docstring

### Before Deployment

- [ ] All E2E smoke tests pass: `python scripts/smoke_test_e2e.py`
- [ ] Tenant isolation verified (smoke tests include this)
- [ ] RBAC verified (smoke tests include this)
- [ ] No destructive migrations pending
- [ ] All required secrets configured: `DATABASE_URL`, `SESSION_SECRET`

## Historical Context

This architecture was established to support:
1. **Enterprise SaaS**: Multiple industrial customers with strict data isolation
2. **Regulatory Compliance**: Tenant data never visible to other tenants
3. **Operational Stability**: Non-destructive migrations allow safe schema evolution
4. **Security First**: RBAC on every endpoint, tenant_id on every query
5. **Safety**: Black Box and Digital Twin are observation-only, no control capability

## Questions?

If you encounter a situation that seems to violate these rules, document the exception and discuss with the platform owner (Ziyad) before proceeding.
