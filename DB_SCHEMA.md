# OPTRIA IQ - Database Schema

## Design Principles

1. **Additive Only**: No DROP TABLE, DROP COLUMN, or destructive migrations
2. **Multi-Tenant**: All business tables include `tenant_id` foreign key
3. **Indexed**: Common query patterns optimized with indexes
4. **Audit-Ready**: Created/updated timestamps on all tables

---

## Core Tables

### tenants
Primary tenant/organization table.

```sql
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    name_ar VARCHAR(255),
    industry VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### users
User accounts with tenant association.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    full_name VARCHAR(255),
    full_name_ar VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
```

### sites
Physical locations/facilities.

```sql
CREATE TABLE sites (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    name_ar VARCHAR(255),
    location VARCHAR(255),
    site_type VARCHAR(50),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, code)
);
CREATE INDEX idx_sites_tenant ON sites(tenant_id);
```

### assets
Industrial assets/equipment.

```sql
CREATE TABLE assets (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    site_id INTEGER REFERENCES sites(id),
    parent_asset_id INTEGER REFERENCES assets(id),
    code VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    name_ar VARCHAR(255),
    asset_type VARCHAR(100),
    manufacturer VARCHAR(255),
    model VARCHAR(255),
    serial_number VARCHAR(255),
    criticality VARCHAR(20) DEFAULT 'medium',
    production_capacity DECIMAL(15, 2),
    production_unit VARCHAR(50),
    install_date DATE,
    status VARCHAR(50) DEFAULT 'operational',
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, code)
);
CREATE INDEX idx_assets_tenant ON assets(tenant_id);
CREATE INDEX idx_assets_site ON assets(site_id);
CREATE INDEX idx_assets_criticality ON assets(tenant_id, criticality);
```

### asset_components
Hierarchical components within assets.

```sql
CREATE TABLE asset_components (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    asset_id INTEGER REFERENCES assets(id) NOT NULL,
    parent_component_id INTEGER REFERENCES asset_components(id),
    code VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    name_ar VARCHAR(255),
    component_type VARCHAR(100),
    criticality VARCHAR(20) DEFAULT 'medium',
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_components_tenant ON asset_components(tenant_id);
CREATE INDEX idx_components_asset ON asset_components(asset_id);
```

### asset_failure_modes
FMECA failure mode definitions.

```sql
CREATE TABLE asset_failure_modes (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    asset_id INTEGER REFERENCES assets(id) NOT NULL,
    component_id INTEGER REFERENCES asset_components(id),
    code VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    name_ar VARCHAR(255),
    description TEXT,
    failure_effect TEXT,
    severity INTEGER CHECK (severity BETWEEN 1 AND 10),
    occurrence INTEGER CHECK (occurrence BETWEEN 1 AND 10),
    detection INTEGER CHECK (detection BETWEEN 1 AND 10),
    rpn INTEGER GENERATED ALWAYS AS (severity * occurrence * detection) STORED,
    mitigation_action TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_failure_modes_tenant ON asset_failure_modes(tenant_id);
CREATE INDEX idx_failure_modes_asset ON asset_failure_modes(asset_id);
```

---

## AI & Telemetry Tables

### asset_metrics_snapshot
Time-series metrics storage (mini-historian).

```sql
CREATE TABLE asset_metrics_snapshot (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    asset_id INTEGER REFERENCES assets(id) NOT NULL,
    component_id INTEGER REFERENCES asset_components(id),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(20, 6),
    unit VARCHAR(50),
    quality VARCHAR(20) DEFAULT 'good',
    recorded_at TIMESTAMP NOT NULL,
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_metrics_tenant_asset ON asset_metrics_snapshot(tenant_id, asset_id);
CREATE INDEX idx_metrics_recorded ON asset_metrics_snapshot(recorded_at DESC);
CREATE INDEX idx_metrics_name ON asset_metrics_snapshot(metric_name);
```

### asset_ai_scores
AI-computed health and risk scores.

```sql
CREATE TABLE asset_ai_scores (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    asset_id INTEGER REFERENCES assets(id) NOT NULL,
    health_score DECIMAL(5, 2),
    failure_probability DECIMAL(5, 4),
    remaining_useful_life_days INTEGER,
    production_risk_index DECIMAL(5, 2),
    anomaly_detected BOOLEAN DEFAULT FALSE,
    anomaly_details JSONB,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_version VARCHAR(50)
);
CREATE INDEX idx_ai_scores_tenant_asset ON asset_ai_scores(tenant_id, asset_id);
CREATE INDEX idx_ai_scores_computed ON asset_ai_scores(computed_at DESC);
```

### alerts
Event-level alerts and notifications.

```sql
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    asset_id INTEGER REFERENCES assets(id),
    component_id INTEGER REFERENCES asset_components(id),
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    title_ar VARCHAR(255),
    description TEXT,
    status VARCHAR(20) DEFAULT 'open',
    acknowledged_by INTEGER REFERENCES users(id),
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_alerts_tenant ON alerts(tenant_id);
CREATE INDEX idx_alerts_status ON alerts(tenant_id, status);
CREATE INDEX idx_alerts_asset ON alerts(asset_id);
```

---

## Optimization Tables

### optimization_cost_models
Cost parameters for optimization calculations.

```sql
CREATE TABLE optimization_cost_models (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    asset_id INTEGER REFERENCES assets(id),
    site_id INTEGER REFERENCES sites(id),
    cost_per_hour_downtime DECIMAL(15, 2),
    cost_per_failure DECIMAL(15, 2),
    maintenance_cost_preventive DECIMAL(15, 2),
    maintenance_cost_corrective DECIMAL(15, 2),
    energy_cost_per_unit DECIMAL(15, 4),
    production_value_per_unit DECIMAL(15, 4),
    currency VARCHAR(10) DEFAULT 'SAR',
    valid_from DATE,
    valid_to DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_cost_models_tenant ON optimization_cost_models(tenant_id);
```

### optimization_runs
Optimization execution records.

```sql
CREATE TABLE optimization_runs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    run_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    input_parameters JSONB NOT NULL,
    output_summary JSONB,
    error_message TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_opt_runs_tenant ON optimization_runs(tenant_id);
CREATE INDEX idx_opt_runs_type ON optimization_runs(run_type);
CREATE INDEX idx_opt_runs_status ON optimization_runs(status);
```

### optimization_scenarios
Scenario definitions for comparison.

```sql
CREATE TABLE optimization_scenarios (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    run_id INTEGER REFERENCES optimization_runs(id),
    name VARCHAR(255) NOT NULL,
    name_ar VARCHAR(255),
    description TEXT,
    scenario_type VARCHAR(50),
    parameters JSONB NOT NULL,
    results JSONB,
    total_cost DECIMAL(15, 2),
    total_risk_score DECIMAL(10, 4),
    is_recommended BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_scenarios_tenant ON optimization_scenarios(tenant_id);
CREATE INDEX idx_scenarios_run ON optimization_scenarios(run_id);
```

### optimization_recommendations
Individual recommendations from optimization.

```sql
CREATE TABLE optimization_recommendations (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    run_id INTEGER REFERENCES optimization_runs(id) NOT NULL,
    scenario_id INTEGER REFERENCES optimization_scenarios(id),
    asset_id INTEGER REFERENCES assets(id),
    recommendation_type VARCHAR(50) NOT NULL,
    priority_score DECIMAL(10, 4),
    deferral_cost DECIMAL(15, 2),
    risk_reduction DECIMAL(10, 4),
    action_title VARCHAR(255) NOT NULL,
    action_title_ar VARCHAR(255),
    action_description TEXT,
    recommended_date DATE,
    assigned_to INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_recommendations_tenant ON optimization_recommendations(tenant_id);
CREATE INDEX idx_recommendations_run ON optimization_recommendations(run_id);
CREATE INDEX idx_recommendations_asset ON optimization_recommendations(asset_id);
```

---

## Work Orders Table

### work_orders
Lightweight work order tracking.

```sql
CREATE TABLE work_orders (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    asset_id INTEGER REFERENCES assets(id),
    recommendation_id INTEGER REFERENCES optimization_recommendations(id),
    code VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    title_ar VARCHAR(255),
    description TEXT,
    work_type VARCHAR(50),
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'open',
    assigned_to INTEGER REFERENCES users(id),
    scheduled_date DATE,
    due_date DATE,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    estimated_hours DECIMAL(8, 2),
    actual_hours DECIMAL(8, 2),
    notes TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, code)
);
CREATE INDEX idx_work_orders_tenant ON work_orders(tenant_id);
CREATE INDEX idx_work_orders_asset ON work_orders(asset_id);
CREATE INDEX idx_work_orders_status ON work_orders(tenant_id, status);
CREATE INDEX idx_work_orders_assigned ON work_orders(assigned_to);
```

---

## Integration Tables

### tenant_integrations
Integration configurations per tenant.

```sql
CREATE TABLE tenant_integrations (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    name VARCHAR(255) NOT NULL,
    integration_type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'inactive',
    last_sync_at TIMESTAMP,
    last_sync_status VARCHAR(20),
    last_sync_message TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_integrations_tenant ON tenant_integrations(tenant_id);
CREATE INDEX idx_integrations_type ON tenant_integrations(integration_type);
```

### external_signal_mappings
Map external tags/signals to internal assets.

```sql
CREATE TABLE external_signal_mappings (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    integration_id INTEGER REFERENCES tenant_integrations(id) NOT NULL,
    asset_id INTEGER REFERENCES assets(id),
    component_id INTEGER REFERENCES asset_components(id),
    external_tag VARCHAR(255) NOT NULL,
    internal_metric_name VARCHAR(100) NOT NULL,
    unit VARCHAR(50),
    scaling_factor DECIMAL(15, 6) DEFAULT 1.0,
    offset_value DECIMAL(15, 6) DEFAULT 0.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_mappings_tenant ON external_signal_mappings(tenant_id);
CREATE INDEX idx_mappings_integration ON external_signal_mappings(integration_id);
CREATE INDEX idx_mappings_asset ON external_signal_mappings(asset_id);
```

### tenant_identity_providers
SSO configuration per tenant.

```sql
CREATE TABLE tenant_identity_providers (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) NOT NULL,
    provider_type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_idp_tenant ON tenant_identity_providers(tenant_id);
```

---

## Audit & Logging Tables

### audit_logs
Security and action audit trail.

```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_audit_tenant ON audit_logs(tenant_id);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);
```

---

## Notes

1. All `tenant_id` columns enforce multi-tenant isolation
2. JSONB columns used for flexible metadata storage
3. Timestamps in UTC
4. Indexes optimized for common query patterns
5. No CASCADE deletes - maintain referential integrity
