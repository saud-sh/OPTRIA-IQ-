# OPTRIA IQ - Tenant Onboarding Guide

This guide explains how to create and onboard a new tenant in OPTRIA IQ.

## Overview

Tenant onboarding follows a structured 6-step wizard that guides administrators through:
1. Company Information
2. Site Configuration
3. Asset Import
4. Integration Setup
5. User Management
6. Go-Live Checklist

## Prerequisites

Before onboarding a new tenant:
- [ ] Platform owner account access
- [ ] Tenant company details (name, industry, contact)
- [ ] Site information (locations, coordinates)
- [ ] Asset inventory (or sample data for demo)
- [ ] Integration credentials (if connecting to external systems)

## Step 1: Create Tenant

### Via Platform Owner Console

1. Log in as platform owner (admin@optria.io)
2. Navigate to `/admin/tenants`
3. Click "Create New Tenant"
4. Fill in tenant details:
   - **Code**: Unique identifier (e.g., `ARAMCO`, `SABIC`)
   - **Name (English)**: Company name
   - **Name (Arabic)**: Arabic company name
   - **Industry**: Select industry type
   - **Status**: Set to `active`

### Via API

```bash
POST /api/tenants/
{
  "code": "NEW_TENANT",
  "name": "New Tenant Company",
  "name_ar": "الشركة الجديدة",
  "industry": "oil_gas",
  "status": "active",
  "settings": {}
}
```

## Step 2: Create Tenant Admin

1. Navigate to `/users` (as platform owner)
2. Select the new tenant from the dropdown
3. Click "Add User"
4. Create the tenant admin:
   - **Email**: Primary admin email
   - **Username**: Admin username
   - **Full Name**: Admin's full name
   - **Role**: `tenant_admin`
   - **Active**: Yes

5. Share the generated password securely with the admin

## Step 3: Tenant Admin Onboarding Wizard

The tenant admin logs in and completes the onboarding wizard:

### 3.1 Company Profile
- Update company details
- Set timezone and preferences
- Configure language (Arabic/English)

### 3.2 Site Configuration
Navigate to the Sites tab:

1. Click "Add Site"
2. Enter site details:
   - **Code**: Site identifier (e.g., `DHAHRAN-01`)
   - **Name**: Site name
   - **Location**: City/region
   - **Site Type**: `plant`, `refinery`, `powerstation`, etc.
   - **Coordinates**: Latitude/Longitude (optional)

3. Repeat for all operational sites

### 3.3 Asset Import

#### Manual Asset Entry
1. Navigate to `/assets`
2. Click "Add Asset"
3. Enter asset details:
   - **Code**: Asset tag (e.g., `COMP-001`)
   - **Name**: Asset description
   - **Type**: `compressor`, `pump`, `turbine`, etc.
   - **Site**: Select the parent site
   - **Criticality**: `critical`, `high`, `medium`, `low`
   - **Manufacturer**: Equipment manufacturer

#### Bulk Import (Future Feature)
- CSV upload capability
- SAP PM sync via integration

### 3.4 Integration Setup

Navigate to `/integrations` to configure data sources:

#### Tab 1: Data Sources
Connect to industrial data systems:

| Integration Type | Use Case |
|-----------------|----------|
| Demo Connector | Testing with simulated data |
| OPC-UA | Real-time sensor data |
| PI System | OSIsoft PI historian |
| SAP PM | Work orders and maintenance data |
| SQL Database | Custom data sources |

1. Click "Add Integration"
2. Select integration type
3. Enter connection details
4. Click "Test Connection"
5. Save if successful

#### Tab 2: Signal Mappings
Map external signals to assets:

1. Select an asset
2. Add signal mappings:
   - **External Tag**: Source system tag name
   - **Internal Metric**: OPTRIA metric name
   - **Unit**: Engineering unit

#### Tab 3: SSO Configuration (Optional)
Configure Single Sign-On:

1. Select provider (Azure AD, Okta, etc.)
2. Enter provider details:
   - Client ID
   - Client Secret
   - Issuer URL

#### Tab 4: Cost Models
Configure optimization parameters:

1. Set default downtime cost ($/hour)
2. Set failure cost assumptions
3. Configure risk appetite (conservative/balanced/aggressive)

### 3.5 User Management

Create additional users as needed:

1. Navigate to `/users`
2. Add users for each role:
   - **optimization_engineer**: Run optimizations, manage assets
   - **engineer**: Field operations, work orders
   - **viewer**: Read-only dashboards

### 3.6 Go-Live Checklist

Before going live, verify:

- [ ] All sites created
- [ ] Critical assets registered
- [ ] At least one integration active
- [ ] Signal mappings configured
- [ ] Cost model defined
- [ ] Users created and trained
- [ ] Test optimization run successful

## Post-Onboarding

### Verify Data Flow
1. Check `/digital-twin` for asset connectivity status
2. Verify metrics appear in asset details
3. Run a test optimization

### Enable Features
1. Industrial Black Box: Auto-enabled for tenant_admin+
2. Digital Twin: Configure layouts at `/twins`
3. Work Orders: Create initial work orders

### Training Resources
- Dashboard walkthrough
- Optimization workflow
- Black Box incident management
- Report generation

## Troubleshooting

### No Data Appearing
1. Check integration status (should be "connected")
2. Verify signal mappings exist
3. Check integration logs for errors

### Optimization Fails
1. Verify at least 3 assets exist
2. Check cost model is configured
3. Review optimization engine logs

### Users Cannot Log In
1. Verify user is active
2. Check email/password
3. Ensure tenant is active

## API Reference

### Tenant Endpoints
```
GET    /api/tenants/           - List tenants (platform_owner)
POST   /api/tenants/           - Create tenant
GET    /api/tenants/{id}       - Get tenant details
PUT    /api/tenants/{id}       - Update tenant
```

### User Endpoints
```
GET    /api/tenant-users/      - List tenant users
POST   /api/tenant-users/      - Create user
PUT    /api/tenant-users/{id}  - Update user
DELETE /api/tenant-users/{id}  - Deactivate user
POST   /api/tenant-users/{id}/reset-password - Reset password
```

### Site/Asset Endpoints
```
GET    /api/assets/sites       - List sites
POST   /api/assets/sites       - Create site
GET    /api/assets/            - List assets
POST   /api/assets/            - Create asset
```

## Support

For onboarding assistance:
- Technical Issues: Check OPS_RUNBOOK.md
- Platform Questions: Contact platform owner
- Feature Requests: Submit via issue tracker
