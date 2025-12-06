#!/usr/bin/env python3
"""
Seed Demo Signal Mappings
Creates realistic signal mappings for ARAMCO_DEMO tenant assets
with multiple metrics per asset for Digital Twin visualization.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from models.base import SessionLocal
from models.tenant import Tenant
from models.asset import Asset
from models.integration import TenantIntegration, ExternalSignalMapping
from config import settings

METRIC_TEMPLATES = {
    "pump": [
        {"metric": "vibration_rms", "tag_suffix": "VIB", "unit": "mm/s"},
        {"metric": "temperature", "tag_suffix": "TEMP", "unit": "°C"},
        {"metric": "pressure_in", "tag_suffix": "PRES_IN", "unit": "bar"},
        {"metric": "pressure_out", "tag_suffix": "PRES_OUT", "unit": "bar"},
        {"metric": "flow_rate", "tag_suffix": "FLOW", "unit": "m³/h"},
        {"metric": "motor_current", "tag_suffix": "CURR", "unit": "A"},
    ],
    "compressor": [
        {"metric": "vibration_rms", "tag_suffix": "VIB", "unit": "mm/s"},
        {"metric": "temperature", "tag_suffix": "TEMP", "unit": "°C"},
        {"metric": "pressure", "tag_suffix": "PRES", "unit": "bar"},
        {"metric": "speed", "tag_suffix": "RPM", "unit": "RPM"},
        {"metric": "power", "tag_suffix": "PWR", "unit": "kW"},
    ],
    "separator": [
        {"metric": "temperature", "tag_suffix": "TEMP", "unit": "°C"},
        {"metric": "pressure", "tag_suffix": "PRES", "unit": "bar"},
        {"metric": "level", "tag_suffix": "LVL", "unit": "%"},
        {"metric": "flow_gas", "tag_suffix": "FLOW_GAS", "unit": "m³/h"},
        {"metric": "flow_oil", "tag_suffix": "FLOW_OIL", "unit": "m³/h"},
    ],
    "heat_exchanger": [
        {"metric": "temp_inlet", "tag_suffix": "TEMP_IN", "unit": "°C"},
        {"metric": "temp_outlet", "tag_suffix": "TEMP_OUT", "unit": "°C"},
        {"metric": "pressure_drop", "tag_suffix": "PRES_DROP", "unit": "bar"},
        {"metric": "flow_rate", "tag_suffix": "FLOW", "unit": "m³/h"},
    ],
    "valve": [
        {"metric": "position", "tag_suffix": "POS", "unit": "%"},
        {"metric": "temperature", "tag_suffix": "TEMP", "unit": "°C"},
        {"metric": "pressure", "tag_suffix": "PRES", "unit": "bar"},
    ],
    "tank": [
        {"metric": "level", "tag_suffix": "LVL", "unit": "%"},
        {"metric": "temperature", "tag_suffix": "TEMP", "unit": "°C"},
        {"metric": "pressure", "tag_suffix": "PRES", "unit": "bar"},
    ],
    "turbine": [
        {"metric": "vibration_rms", "tag_suffix": "VIB", "unit": "mm/s"},
        {"metric": "temperature", "tag_suffix": "TEMP", "unit": "°C"},
        {"metric": "speed", "tag_suffix": "RPM", "unit": "RPM"},
        {"metric": "power", "tag_suffix": "PWR", "unit": "MW"},
        {"metric": "exhaust_temp", "tag_suffix": "EXH_TEMP", "unit": "°C"},
    ],
    "motor": [
        {"metric": "current", "tag_suffix": "CURR", "unit": "A"},
        {"metric": "voltage", "tag_suffix": "VOLT", "unit": "V"},
        {"metric": "temperature", "tag_suffix": "TEMP", "unit": "°C"},
        {"metric": "vibration_rms", "tag_suffix": "VIB", "unit": "mm/s"},
        {"metric": "speed", "tag_suffix": "RPM", "unit": "RPM"},
    ],
    "default": [
        {"metric": "vibration_rms", "tag_suffix": "VIB", "unit": "mm/s"},
        {"metric": "temperature", "tag_suffix": "TEMP", "unit": "°C"},
        {"metric": "pressure", "tag_suffix": "PRES", "unit": "bar"},
    ],
}


def get_or_create_demo_integration(db: Session, tenant: Tenant) -> TenantIntegration:
    """Get or create a demo integration for the tenant"""
    integration = db.query(TenantIntegration).filter(
        TenantIntegration.tenant_id == tenant.id,
        TenantIntegration.integration_type == "demo"
    ).first()
    
    if not integration:
        integration = TenantIntegration(
            tenant_id=tenant.id,
            name="Demo ARAMCO Connector",
            integration_type="demo",
            config={"mode": "demo", "refresh_interval": 60},
            status="active",
            is_active=True
        )
        db.add(integration)
        db.commit()
        print(f"  Created demo integration: {integration.name}")
    else:
        print(f"  Using existing demo integration: {integration.name}")
    
    return integration


def get_metrics_for_asset_type(asset_type: str) -> list:
    """Get appropriate metrics based on asset type"""
    if not asset_type:
        return METRIC_TEMPLATES["default"]
    
    asset_type_lower = asset_type.lower()
    
    for key in METRIC_TEMPLATES:
        if key in asset_type_lower:
            return METRIC_TEMPLATES[key]
    
    return METRIC_TEMPLATES["default"]


def seed_demo_signal_mappings(db: Session) -> dict:
    """
    Seed signal mappings for ARAMCO_DEMO tenant.
    Returns summary of created mappings.
    """
    print("\n" + "=" * 60)
    print("SEEDING DEMO SIGNAL MAPPINGS")
    print("=" * 60)
    
    tenant = db.query(Tenant).filter(Tenant.code == "ARAMCO_DEMO").first()
    if not tenant:
        print("  ERROR: ARAMCO_DEMO tenant not found!")
        return {"error": "Tenant not found", "created": 0}
    
    print(f"  Found tenant: {tenant.code} (ID: {tenant.id})")
    
    integration = get_or_create_demo_integration(db, tenant)
    
    assets = db.query(Asset).filter(Asset.tenant_id == tenant.id).all()
    if not assets:
        print("  WARNING: No assets found for tenant!")
        return {"error": "No assets found", "created": 0}
    
    print(f"  Found {len(assets)} assets")
    
    created_count = 0
    skipped_count = 0
    
    for asset in assets:
        metrics = get_metrics_for_asset_type(asset.asset_type)
        asset_tag_prefix = asset.code.upper().replace("-", "_") if asset.code else f"ASSET_{asset.id}"
        
        print(f"\n  Asset: {asset.name} ({asset.asset_type})")
        
        for metric_def in metrics:
            external_tag = f"PI:{asset_tag_prefix}.{metric_def['tag_suffix']}"
            
            existing = db.query(ExternalSignalMapping).filter(
                ExternalSignalMapping.tenant_id == tenant.id,
                ExternalSignalMapping.asset_id == asset.id,
                ExternalSignalMapping.internal_metric_name == metric_def["metric"]
            ).first()
            
            if existing:
                skipped_count += 1
                continue
            
            mapping = ExternalSignalMapping(
                tenant_id=tenant.id,
                integration_id=integration.id,
                asset_id=asset.id,
                external_tag=external_tag,
                internal_metric_name=metric_def["metric"],
                unit=metric_def["unit"],
                scaling_factor=1.0,
                offset_value=0.0,
                is_active=True,
                extra_data={"source": "demo_seed"}
            )
            db.add(mapping)
            created_count += 1
            print(f"    + {metric_def['metric']} -> {external_tag}")
    
    db.commit()
    
    print(f"\n" + "-" * 60)
    print(f"SUMMARY: Created {created_count} mappings, skipped {skipped_count} existing")
    print("-" * 60 + "\n")
    
    return {
        "tenant_id": tenant.id,
        "tenant_code": tenant.code,
        "integration_id": integration.id,
        "assets_processed": len(assets),
        "mappings_created": created_count,
        "mappings_skipped": skipped_count
    }


def main():
    """CLI entry point"""
    print("\nStarting Demo Signal Mappings Seed Script...")
    
    db = SessionLocal()
    try:
        result = seed_demo_signal_mappings(db)
        print("\nResult:", result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
