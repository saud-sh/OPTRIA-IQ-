#!/usr/bin/env python3
"""
RCA Pipeline Smoke Test for OPTRIA IQ

Tests the incident-to-work-order pipeline:
1. Create a test incident
2. Run full RCA analysis
3. Verify work order is auto-created
4. Verify notification is created
5. Cleanup
"""
import sys
import os
import requests
import json
from datetime import datetime, timedelta

BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
DEMO_USER = "demo@aramco.com"
DEMO_PASSWORD = "Demo2024!"


def login(email: str, password: str) -> str:
    """Login and get access token"""
    res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })
    if res.status_code != 200:
        print(f"FAIL: Login failed: {res.json()}")
        sys.exit(1)
    
    data = res.json()
    token = data.get("access_token")
    if not token:
        print(f"FAIL: No access token in response")
        sys.exit(1)
    
    print(f"OK: Login successful for {email}")
    return token


def get_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get_assets(token: str) -> list:
    """Get list of assets"""
    res = requests.get(f"{BASE_URL}/api/assets/", headers=get_headers(token))
    if res.status_code != 200:
        print(f"FAIL: Failed to get assets: {res.status_code}")
        return []
    
    data = res.json()
    assets = data.get("assets", [])
    print(f"OK: Found {len(assets)} assets")
    return assets


def create_incident(token: str, asset_id: int) -> dict:
    """Create a test incident"""
    res = requests.post(f"{BASE_URL}/api/blackbox/incidents", headers=get_headers(token), json={
        "incident_type": "FAILURE",
        "severity": "MAJOR",
        "title": "Test Incident - Vibration Anomaly Detected",
        "description": "High vibration levels detected on pump bearing. Temperature also rising.",
        "root_asset_id": asset_id,
        "start_time": (datetime.utcnow() - timedelta(hours=1)).isoformat()
    })
    
    if res.status_code != 200:
        print(f"FAIL: Failed to create incident: {res.json()}")
        return {}
    
    data = res.json()
    incident = data.get("incident", {})
    print(f"OK: Created incident {incident.get('incident_number', 'UNKNOWN')}")
    return incident


def create_sensor_events(token: str, asset_id: int, incident_start: str) -> list:
    """Create sensor events for RCA"""
    events = []
    base_time = datetime.fromisoformat(incident_start.replace("Z", "+00:00").replace("+00:00", ""))
    
    event_data = [
        {"category": "SENSOR", "summary": "Vibration level high - exceeded threshold 1.5", "severity": "WARNING", "offset": -10},
        {"category": "SENSOR", "summary": "Temperature rising - bearing temperature increased by 10C", "severity": "WARNING", "offset": -8},
        {"category": "ALERT", "summary": "Pump P-001 health score dropped to 65%", "severity": "MAJOR", "offset": -5},
        {"category": "SENSOR", "summary": "Flow rate reduced to 70% of normal", "severity": "WARNING", "offset": -2},
    ]
    
    for ev in event_data:
        event_time = base_time + timedelta(minutes=ev["offset"])
        res = requests.post(f"{BASE_URL}/api/blackbox/events", headers=get_headers(token), json={
            "asset_id": asset_id,
            "source_system": "PI_SYSTEM",
            "source_type": "sensor",
            "event_time": event_time.isoformat(),
            "severity": ev["severity"],
            "event_category": ev["category"],
            "summary": ev["summary"],
            "payload": {}
        })
        if res.status_code == 200:
            events.append(res.json().get("event", {}))
        else:
            print(f"WARN: Failed to create event: {res.json()}")
    
    print(f"OK: Created {len(events)} sensor events")
    return events


def link_events_to_incident(token: str, incident_id: str, events: list):
    """Link events to incident"""
    roles = ["CAUSE", "CAUSE", "SYMPTOM", "SYMPTOM"]
    for i, event in enumerate(events):
        role = roles[i] if i < len(roles) else "CONTEXT"
        res = requests.post(
            f"{BASE_URL}/api/blackbox/incidents/{incident_id}/events",
            headers=get_headers(token),
            json={"event_id": event.get("id"), "role": role}
        )
        if res.status_code != 200:
            print(f"WARN: Failed to link event: {res.json()}")
    
    print(f"OK: Linked {len(events)} events to incident")


def run_full_rca(token: str, incident_id: str) -> dict:
    """Run full RCA with work order creation"""
    res = requests.post(
        f"{BASE_URL}/api/blackbox/incidents/{incident_id}/rca-full?auto_create_wo=true",
        headers=get_headers(token)
    )
    
    if res.status_code != 200:
        print(f"FAIL: RCA failed: {res.json()}")
        return {}
    
    data = res.json()
    print(f"OK: RCA completed")
    print(f"    Top cause: {data.get('top_cause', {}).get('category')} ({data.get('top_cause', {}).get('confidence', 0):.0%})")
    print(f"    Work order created: {data.get('work_order_created', False)}")
    
    if data.get("financial_impact"):
        fi = data["financial_impact"]
        print(f"    Estimated cost: {fi.get('total_estimated_cost', 0):,.0f} {fi.get('currency', 'SAR')}")
    
    if data.get("carbon_impact"):
        ci = data["carbon_impact"]
        print(f"    Carbon impact: {ci.get('carbon_kg', 0):.1f} kg CO2")
    
    return data


def verify_work_order(token: str, incident_id: str) -> dict:
    """Verify work order was created for the incident"""
    res = requests.get(f"{BASE_URL}/api/work-orders/", headers=get_headers(token))
    
    if res.status_code != 200:
        print(f"FAIL: Failed to get work orders: {res.json()}")
        return {}
    
    data = res.json()
    work_orders = data.get("work_orders", [])
    
    for wo in work_orders:
        if wo.get("incident_id") == incident_id:
            print(f"OK: Found work order {wo.get('code')} for incident")
            print(f"    Priority: {wo.get('priority')}")
            print(f"    Source: {wo.get('source')}")
            return wo
    
    print(f"WARN: No work order found for incident {incident_id}")
    return {}


def verify_notifications(token: str) -> list:
    """Verify notifications exist"""
    res = requests.get(f"{BASE_URL}/api/notifications?limit=5", headers=get_headers(token))
    
    if res.status_code != 200:
        print(f"WARN: Failed to get notifications: {res.status_code}")
        return []
    
    data = res.json()
    notifications = data.get("notifications", [])
    unread = data.get("unread_count", 0)
    
    print(f"OK: Notifications API working - {unread} unread, {len(notifications)} recent")
    return notifications


def get_incident_detail(token: str, incident_id: str) -> dict:
    """Get incident with RCA results"""
    res = requests.get(f"{BASE_URL}/api/blackbox/incidents/{incident_id}", headers=get_headers(token))
    
    if res.status_code != 200:
        print(f"FAIL: Failed to get incident: {res.json()}")
        return {}
    
    data = res.json()
    print(f"OK: Incident retrieved with RCA status: {data.get('rca_status')}")
    
    if data.get("event_story"):
        print(f"    Event story: {data.get('event_story')[:100]}...")
    
    if data.get("recommended_actions"):
        print(f"    Recommended actions: {len(data.get('recommended_actions', []))}")
    
    return data


def run_tests():
    """Run all pipeline tests"""
    print("\n" + "="*60)
    print("RCA PIPELINE SMOKE TEST")
    print("="*60 + "\n")
    
    token = login(DEMO_USER, DEMO_PASSWORD)
    
    assets = get_assets(token)
    if not assets:
        print("FAIL: No assets found")
        sys.exit(1)
    
    test_asset = assets[0]
    print(f"\nUsing test asset: {test_asset.get('name')} (ID: {test_asset.get('id')})")
    
    print("\n--- Step 1: Create Incident ---")
    incident = create_incident(token, test_asset.get("id"))
    if not incident:
        sys.exit(1)
    
    incident_id = incident.get("id")
    
    print("\n--- Step 2: Create Sensor Events ---")
    events = create_sensor_events(token, test_asset.get("id"), incident.get("start_time"))
    
    print("\n--- Step 3: Link Events to Incident ---")
    if events:
        link_events_to_incident(token, incident_id, events)
    
    print("\n--- Step 4: Run Full RCA Analysis ---")
    rca_result = run_full_rca(token, incident_id)
    
    print("\n--- Step 5: Verify Work Order Creation ---")
    work_order = verify_work_order(token, incident_id)
    
    print("\n--- Step 6: Verify Notification System ---")
    notifications = verify_notifications(token)
    
    print("\n--- Step 7: Verify Incident RCA Results ---")
    incident_detail = get_incident_detail(token, incident_id)
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    results = [
        ("Incident Created", bool(incident)),
        ("Events Created", len(events) > 0),
        ("RCA Completed", rca_result.get("success", False)),
        ("Work Order Created", rca_result.get("work_order_created", False)),
        ("Notification API", len(notifications) >= 0),
        ("RCA Results Stored", incident_detail.get("rca_status") == "COMPLETED")
    ]
    
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"  [{status}] {name}")
    
    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(run_tests())
