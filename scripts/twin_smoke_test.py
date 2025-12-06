#!/usr/bin/env python3
"""
Digital Twin Smoke Test
Tests the Digital Twin API endpoints including time-series and metrics.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from datetime import datetime

BASE_URL = "http://localhost:5000"


def login(email: str, password: str) -> dict:
    """Login and get session cookies"""
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password}
    )
    if resp.status_code != 200:
        print(f"  ERROR: Login failed - {resp.status_code}")
        return None
    return resp.cookies


def test_twin_assets(cookies) -> list:
    """Test /api/twins/assets endpoint"""
    print("\nTesting /api/twins/assets")
    print("-" * 50)
    
    resp = requests.get(f"{BASE_URL}/api/twins/assets", cookies=cookies)
    if resp.status_code != 200:
        print(f"  ERROR: {resp.status_code}")
        return []
    
    data = resp.json()
    assets = data.get("assets", [])
    summary = data.get("summary", {})
    
    print(f"  Total Assets: {summary.get('total_assets', 0)}")
    print(f"  Normal: {summary.get('normal', 0)}")
    print(f"  Warning: {summary.get('warning', 0)}")
    print(f"  Critical: {summary.get('critical', 0)}")
    print(f"  Live Data: {summary.get('live_data', 0)}")
    print(f"  Disconnected: {summary.get('disconnected', 0)}")
    
    return assets


def test_twin_summary(cookies):
    """Test /api/twins/summary endpoint"""
    print("\nTesting /api/twins/summary")
    print("-" * 50)
    
    resp = requests.get(f"{BASE_URL}/api/twins/summary", cookies=cookies)
    if resp.status_code != 200:
        print(f"  ERROR: {resp.status_code}")
        return None
    
    data = resp.json()
    stats = data.get("stats", {})
    assets = data.get("assets", [])
    
    print(f"  Stats: {stats}")
    print(f"  Assets Count: {len(assets)}")
    
    return data


def test_asset_metrics(cookies, asset_id: int):
    """Test /api/twins/assets/{id}/metrics endpoint"""
    print(f"\nTesting /api/twins/assets/{asset_id}/metrics")
    print("-" * 50)
    
    resp = requests.get(f"{BASE_URL}/api/twins/assets/{asset_id}/metrics", cookies=cookies)
    if resp.status_code != 200:
        print(f"  ERROR: {resp.status_code}")
        return []
    
    data = resp.json()
    metrics = data.get("metrics", [])
    
    print(f"  Asset: {data.get('asset_name', 'Unknown')}")
    print(f"  Metrics Found: {len(metrics)}")
    for m in metrics[:5]:
        print(f"    - {m.get('name')}: {m.get('external_tag')} ({m.get('unit', 'N/A')})")
    
    return metrics


def test_timeseries(cookies, asset_id: int, metric_name: str):
    """Test /api/twins/assets/{id}/metrics/{name}/series endpoint"""
    print(f"\nTesting /api/twins/assets/{asset_id}/metrics/{metric_name}/series")
    print("-" * 50)
    
    resp = requests.get(
        f"{BASE_URL}/api/twins/assets/{asset_id}/metrics/{metric_name}/series",
        params={"limit": 20},
        cookies=cookies
    )
    
    if resp.status_code != 200:
        print(f"  ERROR: {resp.status_code}")
        return None
    
    data = resp.json()
    points = data.get("points", [])
    
    print(f"  Asset: {data.get('asset_name', 'Unknown')}")
    print(f"  Metric: {data.get('metric', 'Unknown')}")
    print(f"  External Tag: {data.get('external_tag', 'Unknown')}")
    print(f"  Unit: {data.get('unit', 'N/A')}")
    print(f"  Integration Type: {data.get('integration_type', 'Unknown')}")
    print(f"  Points Returned: {len(points)}")
    
    if points:
        print(f"\n  Sample Points:")
        for p in points[:3]:
            print(f"    {p.get('timestamp')}: {p.get('value')} {p.get('unit', '')}")
        if len(points) > 3:
            print(f"    ... and {len(points) - 3} more")
    
    return data


def test_blackbox_events(cookies):
    """Check if SENSOR events were created in BlackBox"""
    print("\nChecking BlackBox SENSOR events")
    print("-" * 50)
    
    resp = requests.get(
        f"{BASE_URL}/api/blackbox/events",
        params={"event_category": "SENSOR", "limit": 5},
        cookies=cookies
    )
    
    if resp.status_code != 200:
        print(f"  ERROR: {resp.status_code}")
        return
    
    data = resp.json()
    events = data.get("events", [])
    
    print(f"  Recent SENSOR Events: {len(events)}")
    for e in events[:3]:
        print(f"    - {e.get('summary', 'No summary')[:50]}...")


def main():
    print("=" * 60)
    print("DIGITAL TWIN SMOKE TEST")
    print("=" * 60)
    print(f"Started: {datetime.now().isoformat()}")
    
    print("\n1. Logging in as demo@aramco.com")
    cookies = login("demo@aramco.com", "Demo2024!")
    if not cookies:
        print("FAILED: Could not login")
        return 1
    print("  Login successful!")
    
    print("\n2. Testing Twin Summary Endpoint")
    test_twin_summary(cookies)
    
    print("\n3. Testing Twin Assets Endpoint")
    assets = test_twin_assets(cookies)
    
    if not assets:
        print("\nWARNING: No assets found. Run seed script first:")
        print("  python scripts/seed_demo_mappings.py")
        return 1
    
    test_asset = assets[0]
    asset_id = test_asset.get("id")
    
    print(f"\n4. Testing Metrics for Asset ID: {asset_id}")
    metrics = test_asset_metrics(cookies, asset_id)
    
    if metrics:
        metric_name = metrics[0].get("name")
        print(f"\n5. Testing Time-Series for Metric: {metric_name}")
        test_timeseries(cookies, asset_id, metric_name)
    else:
        print("\n5. SKIPPED: No metrics found for this asset")
        print("   Run seed script first: python scripts/seed_demo_mappings.py")
    
    print("\n6. Checking BlackBox SENSOR Events")
    test_blackbox_events(cookies)
    
    print("\n" + "=" * 60)
    print("SMOKE TEST COMPLETE")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
