#!/usr/bin/env python3
"""
OPTRIA IQ - Integration Smoke Test
Tests integration endpoints, Digital Twin assets, and Black Box.
Read-only verification script - does not modify data.
"""
import os
import sys
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
TENANT_CODE = os.getenv("TENANT_CODE", "ARAMCO_DEMO")

def print_header(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

def print_step(step: str):
    print(f"\n{step}")
    print("-" * 70)

def create_session_and_login(email: str, password: str) -> requests.Session:
    """Create session and login to get authentication cookie"""
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        data = response.json()
        if data.get("access_token") or len(session.cookies) > 0:
            return session
    return None

def test_config_status(session: requests.Session) -> dict:
    """Test the /internal/config/status endpoint"""
    print_step("Testing /health/internal/config/status (platform_owner only)")
    
    response = session.get(f"{BASE_URL}/health/internal/config/status")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  Timestamp: {data.get('timestamp', 'N/A')}")
        
        subsystems = data.get("subsystems", {})
        for name, info in subsystems.items():
            status = info.get("status", "unknown")
            icon = "✓" if status in ["ok", "configured", "enabled"] else "○"
            print(f"  {icon} {name}: {status}")
        
        flags = data.get("feature_flags", {})
        print("\n  Feature Flags:")
        for flag, value in flags.items():
            print(f"    - {flag}: {value}")
        
        return data
    else:
        print(f"  ✗ Failed: {response.status_code}")
        return {}

def test_blackbox_incidents(session: requests.Session) -> list:
    """Test Black Box incidents endpoint"""
    print_step("Testing /api/blackbox/incidents (Black Box Incidents)")
    
    response = session.get(f"{BASE_URL}/api/blackbox/incidents?limit=10")
    
    if response.status_code == 200:
        data = response.json()
        incidents = data.get("incidents", [])
        print(f"  Found {len(incidents)} incident(s)")
        
        for incident in incidents[:5]:
            status = incident.get("status", "unknown")
            severity = incident.get("severity", "unknown")
            print(f"  • [{incident.get('incident_number')}] {incident.get('title')} ({severity}, {status})")
        
        return incidents
    else:
        print(f"  ✗ Failed: {response.status_code}")
        return []

def test_integrations_list(session: requests.Session) -> list:
    """Test listing integrations"""
    print_step("Testing /api/integrations/ (list integrations)")
    
    response = session.get(f"{BASE_URL}/api/integrations/")
    
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list):
            integrations = data
        else:
            integrations = data.get("integrations", [])
        print(f"  Found {len(integrations)} integration(s)")
        
        for i, integ in enumerate(integrations[:10]):
            status = integ.get("status", "unknown")
            is_demo = integ.get("config", {}).get("is_demo", False)
            demo_badge = " [Demo]" if is_demo else ""
            icon = "✓" if status == "active" else "○"
            print(f"  {icon} [{integ.get('id')}] {integ.get('name')}{demo_badge} ({integ.get('integration_type')}) - {status}")
        
        return integrations
    else:
        print(f"  ✗ Failed: {response.status_code}")
        try:
            print(f"    Error: {response.json()}")
        except:
            pass
        return []

def test_integration_connection(session: requests.Session, integration_id: int, integration_name: str) -> bool:
    """Test a specific integration connection"""
    print(f"\n  Testing connection for [{integration_id}] {integration_name}...")
    
    response = session.post(f"{BASE_URL}/api/integrations/{integration_id}/test")
    
    if response.status_code == 200:
        data = response.json()
        success = data.get("success", False)
        message = data.get("message", "No message")
        icon = "✓" if success else "○"
        print(f"    {icon} {message}")
        return success
    else:
        print(f"    ✗ HTTP {response.status_code}")
        try:
            print(f"      Error: {response.json().get('detail', 'Unknown')}")
        except:
            pass
        return False

def test_digital_twin_assets(session: requests.Session) -> dict:
    """Test Digital Twin assets endpoint"""
    print_step("Testing /api/twins/assets (Digital Twin)")
    
    response = session.get(f"{BASE_URL}/api/twins/assets")
    
    if response.status_code == 200:
        data = response.json()
        assets = data.get("assets", [])
        summary = data.get("summary", {})
        
        print(f"  Total Assets: {summary.get('total_assets', 0)}")
        print(f"  Live Data: {summary.get('live_data', 0)}")
        print(f"  Demo/Simulated: {summary.get('demo_data', 0)}")
        print(f"  Disconnected: {summary.get('disconnected', 0)}")
        print(f"  Health - Normal: {summary.get('normal', 0)}, Warning: {summary.get('warning', 0)}, Critical: {summary.get('critical', 0)}")
        
        if assets:
            print("\n  Sample Assets:")
            for asset in assets[:5]:
                health = asset.get('health_score')
                health_str = f"{health:.1f}%" if health else "N/A"
                status_icon = "🟢" if asset.get('data_status') == 'live' else "🟡" if asset.get('data_status') == 'demo' else "⚪"
                print(f"    {status_icon} {asset.get('code')} - {asset.get('name')} (Health: {health_str}, Data: {asset.get('data_status')})")
        
        return data
    else:
        print(f"  ✗ Failed: {response.status_code}")
        try:
            print(f"    Error: {response.json()}")
        except:
            pass
        return {}

def test_blackbox_stats(session: requests.Session) -> dict:
    """Test Black Box stats endpoint"""
    print_step("Testing /api/blackbox/stats (Black Box)")
    
    response = session.get(f"{BASE_URL}/api/blackbox/stats")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  Total Incidents: {data.get('total_incidents', 0)}")
        print(f"  Open Incidents: {data.get('open_incidents', 0)}")
        print(f"  Critical Incidents: {data.get('critical_incidents', 0)}")
        print(f"  Events (24h): {data.get('events_24h', 0)}")
        return data
    else:
        print(f"  ✗ Failed: {response.status_code}")
        return {}

def test_blackbox_incidents(session: requests.Session) -> list:
    """Test Black Box incidents list"""
    print_step("Testing /api/blackbox/incidents (Black Box Incidents)")
    
    response = session.get(f"{BASE_URL}/api/blackbox/incidents?limit=10")
    
    if response.status_code == 200:
        data = response.json()
        incidents = data.get("incidents", [])
        total = data.get("total", 0)
        
        print(f"  Found {total} incident(s)")
        
        if incidents:
            print("\n  Recent Incidents:")
            for inc in incidents[:5]:
                severity_icon = "🔴" if inc.get('severity') == 'CRITICAL' else "🟠" if inc.get('severity') == 'MAJOR' else "🟡"
                print(f"    {severity_icon} {inc.get('incident_number', inc.get('id')[:8])} - {inc.get('title', 'Untitled')} ({inc.get('status')})")
        
        return incidents
    else:
        print(f"  ✗ Failed: {response.status_code}")
        return []

def test_health_endpoints() -> dict:
    """Test basic health endpoints"""
    print_step("Testing Health Endpoints")
    
    results = {}
    
    endpoints = [
        "/health",
        "/health/live",
        "/health/ready"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            status = response.status_code
            icon = "✓" if status == 200 else "✗"
            print(f"  {icon} {endpoint}: {status}")
            results[endpoint] = status == 200
        except Exception as e:
            print(f"  ✗ {endpoint}: {e}")
            results[endpoint] = False
    
    return results

def main():
    print_header("OPTRIA IQ - INTEGRATION SMOKE TEST")
    print(f"Base URL: {BASE_URL}")
    print(f"Target Tenant: {TENANT_CODE}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    
    health_results = test_health_endpoints()
    all_healthy = all(health_results.values())
    
    if not all_healthy:
        print("\n✗ Health checks failed. Server may not be running.")
        print("  Run: python main.py")
        return 1
    
    print_step("Authenticating as Platform Owner")
    owner_session = create_session_and_login("admin@optria.io", "OptriA2024!")
    if owner_session:
        print("  ✓ Platform owner authenticated")
    else:
        print("  ✗ Failed to authenticate platform owner")
        print("  Make sure demo data is seeded")
        return 1
    
    config_status = test_config_status(owner_session)
    
    print_step(f"Authenticating as Tenant Admin ({TENANT_CODE})")
    tenant_session = create_session_and_login("demo@aramco.com", "Demo2024!")
    if tenant_session:
        print("  ✓ Tenant admin authenticated")
    else:
        print("  ○ Tenant admin not found (demo mode may be off)")
        tenant_session = owner_session
    
    integrations = test_integrations_list(tenant_session)
    
    incidents = test_blackbox_incidents(tenant_session)
    
    opcua_tested = False
    pi_tested = False
    demo_tested = False
    
    if integrations:
        print_step("Testing Integration Connections")
        
        for integ in integrations:
            integ_type = integ.get("integration_type", "")
            integ_id = integ.get("id")
            integ_name = integ.get("name")
            
            if integ_type == "opcua" and not opcua_tested:
                test_integration_connection(tenant_session, integ_id, integ_name)
                opcua_tested = True
            elif integ_type == "pi" and not pi_tested:
                test_integration_connection(tenant_session, integ_id, integ_name)
                pi_tested = True
            elif integ_type == "demo" and not demo_tested:
                test_integration_connection(tenant_session, integ_id, integ_name)
                demo_tested = True
    
    twin_data = test_digital_twin_assets(tenant_session)
    
    bb_stats = test_blackbox_stats(tenant_session)
    bb_incidents = test_blackbox_incidents(tenant_session)
    
    print_header("INTEGRATION SMOKE TEST SUMMARY")
    print(f"Health Endpoints:   {'✓ All passed' if all_healthy else '✗ Some failed'}")
    print(f"Config Status:      {'✓ Retrieved' if config_status else '✗ Failed'}")
    print(f"Integrations List:  {'✓ ' + str(len(integrations)) + ' found' if integrations else '○ None found'}")
    print(f"OPC-UA Test:        {'✓ Tested' if opcua_tested else '○ No OPC-UA integration'}")
    print(f"PI System Test:     {'✓ Tested' if pi_tested else '○ No PI integration'}")
    print(f"Demo Connector:     {'✓ Tested' if demo_tested else '○ No Demo integration'}")
    
    twin_assets = twin_data.get("summary", {}).get("total_assets", 0)
    print(f"Digital Twin:       {'✓ ' + str(twin_assets) + ' assets' if twin_assets else '○ No assets'}")
    print(f"Black Box Events:   {'✓ ' + str(bb_stats.get('events_24h', 0)) + ' events (24h)' if bb_stats else '○ No data'}")
    print(f"Black Box Incidents:{'✓ ' + str(len(bb_incidents)) + ' incidents' if bb_incidents else '○ No incidents'}")
    
    subsystems = config_status.get("subsystems", {})
    opcua_endpoint = subsystems.get("opcua_endpoint", {})
    pi_config = subsystems.get("pi_default_config", {})
    base_url_config = subsystems.get("base_url", {})
    
    print("\nGlobal Integration Defaults:")
    print(f"  Base URL:         {'✓ Configured' if base_url_config.get('base_url_configured') else '○ Not configured'}")
    print(f"  OPC-UA Endpoint:  {'✓ Configured' if opcua_endpoint.get('has_opcua_endpoint') else '○ Not configured'}")
    print(f"  OPC-UA Creds:     {'✓ Configured' if subsystems.get('opcua_default_creds', {}).get('has_creds') else '○ Not configured'}")
    print(f"  PI Base URL:      {'✓ Configured' if pi_config.get('has_url') else '○ Not configured'}")
    
    print("\n" + "=" * 70)
    print("Integration smoke test completed.")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
