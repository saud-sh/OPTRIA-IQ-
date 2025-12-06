#!/usr/bin/env python3
"""
OPTRIA IQ - Integration Smoke Test
Tests integration endpoints and config status.
"""
import os
import sys
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")

def print_header(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

def print_step(step: str):
    print(f"\n{step}")
    print("-" * 70)

def login(email: str, password: str) -> str:
    """Login and return JWT token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token", "")
    return ""

def test_config_status(token: str) -> dict:
    """Test the /internal/config/status endpoint"""
    print_step("Testing /health/internal/config/status (platform_owner only)")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/health/internal/config/status",
        headers=headers
    )
    
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

def test_integrations_list(token: str) -> list:
    """Test listing integrations"""
    print_step("Testing /api/integrations/ (list integrations)")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/integrations/",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        integrations = data.get("integrations", [])
        print(f"  Found {len(integrations)} integration(s)")
        
        for i, integ in enumerate(integrations[:5]):
            status = integ.get("status", "unknown")
            icon = "✓" if status == "active" else "○"
            print(f"  {icon} [{integ.get('id')}] {integ.get('name')} ({integ.get('integration_type')}) - {status}")
        
        return integrations
    else:
        print(f"  ✗ Failed: {response.status_code}")
        try:
            print(f"    Error: {response.json()}")
        except:
            pass
        return []

def test_integration_connection(token: str, integration_id: int, integration_name: str) -> bool:
    """Test a specific integration connection"""
    print(f"\n  Testing connection for [{integration_id}] {integration_name}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/api/integrations/{integration_id}/test",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        success = data.get("success", False)
        message = data.get("message", "No message")
        icon = "✓" if success else "✗"
        print(f"    {icon} {message}")
        return success
    else:
        print(f"    ✗ HTTP {response.status_code}")
        try:
            print(f"      Error: {response.json().get('detail', 'Unknown')}")
        except:
            pass
        return False

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
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    
    health_results = test_health_endpoints()
    all_healthy = all(health_results.values())
    
    if not all_healthy:
        print("\n✗ Health checks failed. Server may not be running.")
        print("  Run: python main.py")
        return 1
    
    print_step("Authenticating as Platform Owner")
    owner_token = login("admin@optria.io", "OptriA2024!")
    if owner_token:
        print("  ✓ Platform owner authenticated")
    else:
        print("  ✗ Failed to authenticate platform owner")
        print("  Make sure demo data is seeded")
        return 1
    
    config_status = test_config_status(owner_token)
    
    print_step("Authenticating as Tenant Admin (Demo ARAMCO)")
    tenant_token = login("demo@aramco.com", "Demo2024!")
    if tenant_token:
        print("  ✓ Tenant admin authenticated")
    else:
        print("  ○ Tenant admin not found (demo mode may be off)")
        tenant_token = owner_token
    
    integrations = test_integrations_list(tenant_token)
    
    opcua_tested = False
    pi_tested = False
    
    if integrations:
        print_step("Testing Integration Connections")
        
        for integ in integrations:
            integ_type = integ.get("integration_type", "")
            integ_id = integ.get("id")
            integ_name = integ.get("name")
            
            if integ_type == "opcua" and not opcua_tested:
                test_integration_connection(tenant_token, integ_id, integ_name)
                opcua_tested = True
            elif integ_type == "pi" and not pi_tested:
                test_integration_connection(tenant_token, integ_id, integ_name)
                pi_tested = True
            
            if opcua_tested and pi_tested:
                break
    
    print_header("INTEGRATION SMOKE TEST SUMMARY")
    print(f"Health Endpoints:   {'✓ All passed' if all_healthy else '✗ Some failed'}")
    print(f"Config Status:      {'✓ Retrieved' if config_status else '✗ Failed'}")
    print(f"Integrations List:  {'✓ ' + str(len(integrations)) + ' found' if integrations else '○ None found'}")
    print(f"OPC-UA Test:        {'✓ Tested' if opcua_tested else '○ No OPC-UA integration'}")
    print(f"PI System Test:     {'✓ Tested' if pi_tested else '○ No PI integration'}")
    
    subsystems = config_status.get("subsystems", {})
    opcua_endpoint = subsystems.get("opcua_endpoint", {})
    pi_config = subsystems.get("pi_default_config", {})
    
    print("\nGlobal Integration Defaults:")
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
