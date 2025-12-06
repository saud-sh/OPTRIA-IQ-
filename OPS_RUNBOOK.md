# OPTRIA IQ - Operations Runbook

This document provides operational procedures for deploying, maintaining, and troubleshooting OPTRIA IQ.

## Table of Contents
1. [Deployment](#deployment)
2. [Secrets Management](#secrets-management)
3. [Health Checks](#health-checks)
4. [Smoke Tests](#smoke-tests)
5. [Incident Response](#incident-response)
6. [Database Operations](#database-operations)
7. [Monitoring](#monitoring)

## Deployment

### Replit Deployment

1. **Pre-deployment Checklist**
   - [ ] Dependencies synced (`uv sync` on Replit)
   - [ ] All smoke tests pass (`python scripts/smoke_test_e2e.py`)
   - [ ] Required secrets are configured
   - [ ] Database migrations applied (if any)
   - [ ] No critical application errors

2. **Deploy Steps**
   - Navigate to the Replit Deployments tab
   - Click "Deploy" to publish to production
   - Monitor the deployment logs for errors
   - Verify health endpoints after deployment

3. **Post-deployment Verification**
   ```bash
   # Check health endpoint
   curl https://your-app.replit.app/health
   
   # Check readiness
   curl https://your-app.replit.app/health/ready
   ```

### Environment Configuration

Production deployments require these secrets in Replit:

| Secret | Required | Description |
|--------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SESSION_SECRET` | Yes | JWT signing key (32+ characters) |
| `APP_ENV` | No | Set to `production` for production |

## Secrets Management

### Viewing Current Secrets
- Navigate to Replit > Tools > Secrets
- Secrets are encrypted at rest and in transit

### Rotating Secrets

#### SESSION_SECRET Rotation
1. Generate a new secret: `python -c "import secrets; print(secrets.token_hex(32))"`
2. Update the secret in Replit Secrets
3. Redeploy the application
4. Note: All active sessions will be invalidated

#### DATABASE_URL Rotation
1. Create new database credentials in Neon
2. Update DATABASE_URL in Replit Secrets
3. Verify connectivity: `python scripts/smoke_test_e2e.py`
4. Redeploy the application

### Adding New Secrets
1. Go to Replit > Tools > Secrets
2. Click "New Secret"
3. Enter key and value
4. Update `config.py` to reference the new secret
5. Redeploy

## Health Checks

### Available Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Basic health status |
| `GET /health/live` | Liveness probe (is the app running?) |
| `GET /health/ready` | Readiness probe (can it serve traffic?) |
| `GET /health/internal/config/status` | Configuration diagnostics (authenticated) |

### Health Check Responses

**Healthy Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-12-06T12:00:00Z"
}
```

**Unhealthy Response:**
```json
{
  "status": "unhealthy",
  "database": "disconnected",
  "error": "Connection refused"
}
```

## Smoke Tests

### Running Smoke Tests

```bash
# Run full E2E test suite
python scripts/smoke_test_e2e.py

# Expected output shows:
# ✓ Database connection successful
# ✓ All CRUD operations completed successfully!
# ✓ Tenant isolation verified!
# ✓ RBAC verified!
```

### Test Coverage

The smoke test validates:
1. Database connectivity
2. Tenant CRUD operations
3. User management (RBAC)
4. Asset management (Sites, Assets)
5. Alert management
6. Work order management
7. Tenant isolation (security)
8. Role-based access control

### Scheduled Testing (Replit Workflows)

Configure a scheduled workflow for daily smoke tests:

1. Create a workflow in Replit
2. Set schedule (e.g., daily at 06:00 UTC)
3. Command: `python scripts/smoke_test_e2e.py`
4. Configure notifications for failures

## Incident Response

### Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| P1 - Critical | Platform down, data loss risk | Immediate |
| P2 - High | Major feature broken | < 1 hour |
| P3 - Medium | Minor feature impacted | < 4 hours |
| P4 - Low | Cosmetic/UX issues | < 24 hours |

### Common Issues and Resolutions

#### Database Connection Failures
**Symptoms:** 500 errors, health check shows "disconnected"

**Resolution:**
1. Check DATABASE_URL is correctly configured
2. Verify Neon database is accessible
3. Check connection pool limits
4. Review database logs in Neon console

#### Authentication Failures
**Symptoms:** 401 errors, users cannot log in

**Resolution:**
1. Verify SESSION_SECRET is configured
2. Check JWT token expiration settings
3. Clear browser cookies and retry
4. Check user account status (is_active flag)

#### Performance Degradation
**Symptoms:** Slow response times, timeouts

**Resolution:**
1. Check database query performance
2. Review optimization engine load
3. Check for N+1 query issues
4. Consider scaling resources

### Rollback Procedure

1. Navigate to Replit Deployments
2. Find the previous stable deployment
3. Click "Rollback to this version"
4. Verify health checks pass
5. Document the rollback reason

## Database Operations

### Viewing Database Status

```bash
# Check database connection via health endpoint
curl https://your-app.replit.app/health
```

### Safe Schema Changes

CRITICAL RULES:
- NO destructive migrations (DROP TABLE, DROP COLUMN)
- Additive changes only (ADD COLUMN, CREATE TABLE)
- Always test migrations in development first
- Backup data before any schema change

### Backup Recommendations

- Neon provides automatic point-in-time recovery
- For manual backups, use pg_dump
- Test restore procedures quarterly

## Monitoring

### Key Metrics to Monitor

| Metric | Threshold | Action |
|--------|-----------|--------|
| Response time | > 2s | Investigate performance |
| Error rate | > 1% | Check logs, investigate |
| Database connections | > 80% pool | Consider scaling |
| Memory usage | > 90% | Restart, investigate leaks |

### Log Access

- Application logs: Replit console output
- Database logs: Neon dashboard
- Deployment logs: Replit Deployments tab

### Alerting Setup

Configure alerts in Replit or external monitoring:
1. Health endpoint monitoring (every 5 minutes)
2. Error rate threshold alerts
3. Deployment failure notifications

## Contact

For escalation or support:
- Platform Owner: admin@optria.io
- Technical Issues: Create a ticket in the issue tracker
