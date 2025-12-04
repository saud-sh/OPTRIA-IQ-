import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models.asset import Asset, AssetMetricsSnapshot, AssetAIScore, AssetFailureMode

class AIService:
    
    def __init__(self, db: Session):
        self.db = db
        self.model_version = "v1.0.0-heuristic"
    
    def compute_health_score(self, asset_id: int, tenant_id: int) -> float:
        recent_metrics = self.db.query(AssetMetricsSnapshot).filter(
            AssetMetricsSnapshot.asset_id == asset_id,
            AssetMetricsSnapshot.tenant_id == tenant_id,
            AssetMetricsSnapshot.recorded_at >= datetime.utcnow() - timedelta(days=7)
        ).all()
        
        if not recent_metrics:
            return 75.0 + random.uniform(-5, 10)
        
        temp_metrics = [m for m in recent_metrics if 'temperature' in m.metric_name.lower()]
        vibration_metrics = [m for m in recent_metrics if 'vibration' in m.metric_name.lower()]
        pressure_metrics = [m for m in recent_metrics if 'pressure' in m.metric_name.lower()]
        
        score = 100.0
        
        if temp_metrics:
            avg_temp = sum(float(m.metric_value or 0) for m in temp_metrics) / len(temp_metrics)
            if avg_temp > 80:
                score -= min(20, (avg_temp - 80) * 0.5)
        
        if vibration_metrics:
            avg_vib = sum(float(m.metric_value or 0) for m in vibration_metrics) / len(vibration_metrics)
            if avg_vib > 5:
                score -= min(25, (avg_vib - 5) * 2)
        
        if pressure_metrics:
            avg_pressure = sum(float(m.metric_value or 0) for m in pressure_metrics) / len(pressure_metrics)
            if avg_pressure > 100 or avg_pressure < 20:
                score -= 10
        
        score += random.uniform(-3, 3)
        return max(0, min(100, score))
    
    def compute_failure_probability(self, asset_id: int, tenant_id: int, health_score: float) -> float:
        failure_modes = self.db.query(AssetFailureMode).filter(
            AssetFailureMode.asset_id == asset_id,
            AssetFailureMode.tenant_id == tenant_id,
            AssetFailureMode.is_active == True
        ).all()
        
        base_prob = (100 - health_score) / 100 * 0.3
        
        if failure_modes:
            max_rpn = max((fm.rpn or 0) for fm in failure_modes)
            rpn_factor = max_rpn / 1000
            base_prob += rpn_factor * 0.2
        
        base_prob += random.uniform(-0.02, 0.02)
        return max(0, min(1, base_prob))
    
    def estimate_rul(self, asset_id: int, tenant_id: int, health_score: float, failure_prob: float) -> int:
        asset = self.db.query(Asset).filter(
            Asset.id == asset_id,
            Asset.tenant_id == tenant_id
        ).first()
        
        if not asset:
            return 365
        
        base_rul = 365
        
        if asset.install_date:
            age_days = (datetime.utcnow().date() - asset.install_date).days
            if age_days > 3650:
                base_rul -= 100
            elif age_days > 1825:
                base_rul -= 50
        
        health_factor = health_score / 100
        prob_factor = 1 - failure_prob
        
        rul = int(base_rul * health_factor * prob_factor)
        rul += random.randint(-10, 10)
        
        return max(1, rul)
    
    def detect_anomaly(self, asset_id: int, tenant_id: int) -> Tuple[bool, Optional[Dict]]:
        recent_metrics = self.db.query(AssetMetricsSnapshot).filter(
            AssetMetricsSnapshot.asset_id == asset_id,
            AssetMetricsSnapshot.tenant_id == tenant_id,
            AssetMetricsSnapshot.recorded_at >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(desc(AssetMetricsSnapshot.recorded_at)).limit(100).all()
        
        if len(recent_metrics) < 10:
            return False, None
        
        anomalies = []
        
        metric_groups = {}
        for m in recent_metrics:
            if m.metric_name not in metric_groups:
                metric_groups[m.metric_name] = []
            metric_groups[m.metric_name].append(float(m.metric_value or 0))
        
        for metric_name, values in metric_groups.items():
            if len(values) < 5:
                continue
            
            mean_val = sum(values) / len(values)
            variance = sum((x - mean_val) ** 2 for x in values) / len(values)
            std_dev = math.sqrt(variance) if variance > 0 else 0.1
            
            for val in values[-3:]:
                z_score = abs(val - mean_val) / std_dev if std_dev > 0 else 0
                if z_score > 3:
                    anomalies.append({
                        "metric": metric_name,
                        "value": val,
                        "z_score": z_score,
                        "threshold": 3.0
                    })
        
        if anomalies:
            return True, {"anomalies": anomalies[:5]}
        return False, None
    
    def compute_production_risk(self, asset_id: int, tenant_id: int, health_score: float, failure_prob: float) -> float:
        asset = self.db.query(Asset).filter(
            Asset.id == asset_id,
            Asset.tenant_id == tenant_id
        ).first()
        
        if not asset:
            return 50.0
        
        criticality_weights = {
            "critical": 1.5,
            "high": 1.2,
            "medium": 1.0,
            "low": 0.7
        }
        
        weight = criticality_weights.get(asset.criticality, 1.0)
        base_risk = (100 - health_score) * 0.4 + failure_prob * 100 * 0.4
        risk = base_risk * weight
        risk += random.uniform(-2, 2)
        
        return max(0, min(100, risk))
    
    def compute_all_scores(self, asset_id: int, tenant_id: int) -> AssetAIScore:
        health_score = self.compute_health_score(asset_id, tenant_id)
        failure_prob = self.compute_failure_probability(asset_id, tenant_id, health_score)
        rul = self.estimate_rul(asset_id, tenant_id, health_score, failure_prob)
        anomaly_detected, anomaly_details = self.detect_anomaly(asset_id, tenant_id)
        production_risk = self.compute_production_risk(asset_id, tenant_id, health_score, failure_prob)
        
        ai_score = AssetAIScore(
            tenant_id=tenant_id,
            asset_id=asset_id,
            health_score=health_score,
            failure_probability=failure_prob,
            remaining_useful_life_days=rul,
            production_risk_index=production_risk,
            anomaly_detected=anomaly_detected,
            anomaly_details=anomaly_details,
            computed_at=datetime.utcnow(),
            model_version=self.model_version
        )
        
        return ai_score
    
    def process_all_assets(self, tenant_id: int) -> int:
        assets = self.db.query(Asset).filter(
            Asset.tenant_id == tenant_id,
            Asset.is_active == True
        ).all()
        
        processed = 0
        for asset in assets:
            ai_score = self.compute_all_scores(asset.id, tenant_id)
            self.db.add(ai_score)
            processed += 1
        
        self.db.commit()
        return processed

def get_ai_service(db: Session) -> AIService:
    return AIService(db)
