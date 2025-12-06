# OPTRIA IQ - Industrial Operations Optimization Platform

OPTRIA IQ is an enterprise-grade Industrial Operations Optimization Platform targeting major industrial players (ARAMCO, SABIC, SEC). The platform combines AI and quantitative optimization to help industrial companies optimize maintenance, reduce costs, minimize production risk, and optimize workforce dispatch.

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI with Python 3.11 |
| Frontend | Jinja2 templates + Tailwind CSS + Alpine.js |
| Database | PostgreSQL (Neon-backed via Replit) |
| Authentication | JWT tokens with bcrypt password hashing |
| Optimization | PuLP for linear programming |
| ORM | SQLAlchemy 2.0 |

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL database
- Required environment variables (see Configuration section)

### Running Locally

```bash
# On Replit: Dependencies are installed automatically via pyproject.toml
# The application will start automatically using the configured workflow

# Manual start (if needed)
python main.py
```

### Installing Dependencies Manually

```bash
# Using uv (recommended on Replit)
uv sync

# Or using pip with pyproject.toml
pip install .
```

The application will start on `http://0.0.0.0:5000`

### Running Tests

```bash
# Run E2E smoke tests
python scripts/smoke_test_e2e.py
```

## Configuration

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SESSION_SECRET` | JWT signing key (min 32 characters) |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEMO_MODE` | `true` | Enable demo data connector |
| `APP_ENV` | `development` | Environment level (development/staging/production) |
| `OPTIMIZATION_ENGINE_ENABLED` | `true` | Enable optimization engine |
| `PI_BASE_URL` | - | PI System connector base URL |
| `SAP_BASE_URL` | - | SAP PM connector base URL |
| `OPCUA_USERNAME` | - | OPC-UA connector username |
| `OPCUA_PASSWORD` | - | OPC-UA connector password |

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Platform Owner | admin@optria.io | OptriA2024! |
| Tenant Admin (ARAMCO) | demo@aramco.com | Demo2024! |
| Engineer (ARAMCO) | engineer@aramco.com | Engineer2024! |

## Project Structure

```
main.py                     - FastAPI application entry point
config.py                   - Application configuration & secrets
models/                     - SQLAlchemy database models
core/                       - Core business logic
  auth.py                   - Authentication & JWT handling
  rbac.py                   - Role-based access control
  ai_service.py             - AI/ML services
  optimization_engine.py    - PuLP optimization models
  blackbox_engine.py        - Industrial Black Box engine
  connectors/               - Data source connectors
routers/                    - API endpoints
templates/                  - Jinja2 HTML templates
translations/               - Bilingual support (Arabic/English)
scripts/                    - Utility scripts and tests
```

## Key Features

1. **Multi-Tenant Architecture**: Complete tenant isolation with tenant_id enforcement
2. **Four Optimization Models**: Maintenance Prioritization, Deferral Cost Analysis, Production Risk, Workforce Dispatch
3. **AI Services**: Health scores, failure probability, RUL, anomaly detection
4. **Industrial Integrations**: OPC-UA, PI System, SAP PM, SQL databases
5. **Industrial Black Box**: Event collection, incident detection, RCA, timeline replay
6. **Digital Twin Visualization**: Asset health monitoring with connectivity status
7. **Bilingual Support**: Arabic (RTL) and English (LTR)

## Application Routes

### Public Routes
- `/` - Landing page
- `/login` - Authentication

### Authenticated Routes (Sidebar Navigation)
- `/dashboard` - Main dashboard with KPIs
- `/optimization` - Optimization runs & recommendations
- `/assets` - Asset management
- `/integrations` - Integration management (4 tabs)
- `/work-orders` - Work order management
- `/blackbox/incidents` - Industrial Black Box
- `/digital-twin` - Digital Twin visualization
- `/twins` - Digital Twin configuration
- `/users` - User management (tenant_admin+)
- `/onboarding` - Setup wizard (tenant_admin+)
- `/admin/tenants` - Tenant management (platform_owner)

## API Documentation

API endpoints are available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when the application is running.

## RBAC Roles

| Role | Description |
|------|-------------|
| `platform_owner` | Full system access, manages all tenants |
| `tenant_admin` | Manages users and settings within their tenant |
| `optimization_engineer` | Runs optimizations, manages assets and work orders |
| `engineer` | Views data, manages work orders |
| `viewer` | Read-only access to dashboards |

## Deployment

See [OPS_RUNBOOK.md](OPS_RUNBOOK.md) for deployment instructions.

## Support

For technical support or questions, contact the platform administrator.
