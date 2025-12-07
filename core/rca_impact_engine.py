"""
RCA & Impact Engine for OPTRIA IQ
Comprehensive Root Cause Analysis with Financial and Carbon Impact Estimation.
Integrates with Black Box incidents and Digital Twin for complete incident-to-work-order pipeline.
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from models.blackbox import BlackBoxEvent, BlackBoxIncident, BlackBoxIncidentEvent
from models.asset import Asset, Site
from models.optimization import WorkOrder, OptimizationCostModel
from models.user import User
from models.notification import Notification

logger = logging.getLogger(__name__)


CAUSAL_RULES = [
    {
        "id": "bearing_fault",
        "name": "Bearing Fault",
        "name_ar": "عطل المحمل",
        "triggers": [
            {"metric": "vibration", "condition": "high", "threshold": 1.5},
            {"metric": "temperature", "condition": "rising", "threshold": 10}
        ],
        "asset_types": ["pump", "compressor", "motor", "turbine"],
        "root_cause": "BEARING_FAULT",
        "confidence_boost": 0.25,
        "recommended_actions": [
            {"priority": 1, "action": "Schedule bearing replacement within 12 hours", "action_ar": "جدولة استبدال المحمل خلال 12 ساعة"},
            {"priority": 2, "action": "Reduce load to 60% until bearing is replaced", "action_ar": "خفض الحمل إلى 60% حتى استبدال المحمل"},
            {"priority": 3, "action": "Monitor vibration levels continuously", "action_ar": "مراقبة مستويات الاهتزاز بشكل مستمر"}
        ],
        "estimated_downtime_hours": 4
    },
    {
        "id": "pump_cavitation",
        "name": "Pump Cavitation",
        "name_ar": "تكهف المضخة",
        "triggers": [
            {"metric": "temperature", "condition": "high", "threshold": 1.3},
            {"metric": "flow_rate", "condition": "low", "threshold": 0.7}
        ],
        "asset_types": ["pump"],
        "root_cause": "PUMP_CAVITATION",
        "confidence_boost": 0.30,
        "recommended_actions": [
            {"priority": 1, "action": "Check suction line for air leaks", "action_ar": "التحقق من خط السحب بحثًا عن تسرب الهواء"},
            {"priority": 2, "action": "Verify NPSH requirements are met", "action_ar": "التحقق من استيفاء متطلبات NPSH"},
            {"priority": 3, "action": "Reduce pump speed temporarily", "action_ar": "تقليل سرعة المضخة مؤقتًا"}
        ],
        "estimated_downtime_hours": 2
    },
    {
        "id": "valve_leak",
        "name": "Valve Leakage",
        "name_ar": "تسرب الصمام",
        "triggers": [
            {"metric": "pressure", "condition": "dropping", "threshold": 0.8}
        ],
        "asset_types": ["valve", "pipeline", "separator"],
        "root_cause": "VALVE_LEAKAGE",
        "confidence_boost": 0.20,
        "recommended_actions": [
            {"priority": 1, "action": "Isolate and inspect valve", "action_ar": "عزل وفحص الصمام"},
            {"priority": 2, "action": "Check valve seat and seal condition", "action_ar": "التحقق من حالة مقعد الصمام والختم"},
            {"priority": 3, "action": "Prepare for valve replacement if needed", "action_ar": "الاستعداد لاستبدال الصمام إذا لزم الأمر"}
        ],
        "estimated_downtime_hours": 3
    },
    {
        "id": "electrical_fault",
        "name": "Electrical Fault",
        "name_ar": "عطل كهربائي",
        "triggers": [
            {"metric": "current", "condition": "high", "threshold": 1.2},
            {"metric": "power", "condition": "fluctuating"}
        ],
        "asset_types": ["motor", "transformer", "switchgear"],
        "root_cause": "ELECTRICAL_FAILURE",
        "confidence_boost": 0.25,
        "recommended_actions": [
            {"priority": 1, "action": "Perform electrical isolation and lockout", "action_ar": "تنفيذ العزل الكهربائي والقفل"},
            {"priority": 2, "action": "Check motor windings and insulation", "action_ar": "فحص ملفات المحرك والعزل"},
            {"priority": 3, "action": "Verify power supply quality", "action_ar": "التحقق من جودة إمدادات الطاقة"}
        ],
        "estimated_downtime_hours": 6
    },
    {
        "id": "process_upset",
        "name": "Process Upset",
        "name_ar": "اضطراب العملية",
        "triggers": [
            {"metric": "level", "condition": "abnormal"},
            {"metric": "flow_rate", "condition": "abnormal"}
        ],
        "asset_types": ["vessel", "separator", "reactor", "column"],
        "root_cause": "PROCESS_UPSET",
        "confidence_boost": 0.15,
        "recommended_actions": [
            {"priority": 1, "action": "Review operating parameters and setpoints", "action_ar": "مراجعة معلمات التشغيل ونقاط الضبط"},
            {"priority": 2, "action": "Check feed composition and flow", "action_ar": "التحقق من تركيبة التغذية والتدفق"},
            {"priority": 3, "action": "Verify instrumentation calibration", "action_ar": "التحقق من معايرة الأجهزة"}
        ],
        "estimated_downtime_hours": 1
    }
]

CARBON_FACTORS = {
    "electricity": 0.4,
    "natural_gas": 2.0,
    "diesel": 2.68,
    "fuel_oil": 3.1,
    "default": 0.5
}

DEFAULT_ENERGY_CONSUMPTION = {
    "pump": 50,
    "compressor": 200,
    "motor": 75,
    "turbine": 500,
    "separator": 25,
    "vessel": 10,
    "default": 30
}


class RCAImpactEngine:
    """
    Comprehensive RCA and Impact Engine for industrial incidents.
    Implements pattern matching, causal analysis, and impact estimation.
    """
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.window_minutes = 30
    
    def analyze_incident(self, incident_id: str) -> Dict[str, Any]:
        """
        Perform comprehensive RCA on an incident.
        Returns EventStory, RootCauseScore, RecommendedActions, FinancialImpact, CarbonImpact.
        """
        incident = self.db.query(BlackBoxIncident).filter(
            BlackBoxIncident.id == incident_id,
            BlackBoxIncident.tenant_id == self.tenant_id
        ).first()
        
        if not incident:
            return {"error": "Incident not found"}
        
        events = self._gather_incident_events(incident)
        sensor_data = self._gather_sensor_data(incident)
        maintenance_logs = self._gather_maintenance_logs(incident)
        historical_incidents = self._get_historical_incidents(incident)
        
        unified_timeline = self._build_unified_timeline(events, sensor_data, maintenance_logs)
        event_window = self._extract_event_window(unified_timeline, incident.start_time)
        
        pattern_matches = self._match_historical_patterns(event_window, historical_incidents)
        causal_matches = self._apply_causal_rules(event_window, incident)
        
        root_cause_scores = self._compute_root_cause_scores(pattern_matches, causal_matches)
        
        top_cause = max(root_cause_scores.items(), key=lambda x: x[1]) if root_cause_scores else ("UNKNOWN", 0.3)
        
        recommended_actions = self._generate_recommended_actions(top_cause[0], incident)
        
        event_story = self._build_event_story(incident, event_window, top_cause, pattern_matches)
        event_story_ar = self._build_event_story_ar(incident, event_window, top_cause, pattern_matches)
        
        financial_impact = self._estimate_financial_impact(incident, top_cause)
        carbon_impact = self._estimate_carbon_impact(incident, event_window)
        
        incident.event_story = event_story
        incident.event_story_ar = event_story_ar
        incident.root_cause_scores = root_cause_scores
        incident.recommended_actions = recommended_actions
        incident.financial_impact_estimate = financial_impact
        incident.carbon_impact_estimate = carbon_impact
        incident.rca_status = "COMPLETED"
        incident.rca_completed_at = datetime.utcnow()
        incident.rca_summary = {
            "root_cause_category": top_cause[0],
            "confidence": top_cause[1],
            "matched_patterns": len(pattern_matches),
            "matched_rules": len(causal_matches),
            "analysis_time": datetime.utcnow().isoformat()
        }
        
        self.db.commit()
        
        return {
            "incident_id": str(incident.id),
            "event_story": event_story,
            "event_story_ar": event_story_ar,
            "root_cause_scores": root_cause_scores,
            "top_cause": {"category": top_cause[0], "confidence": top_cause[1]},
            "recommended_actions": recommended_actions,
            "financial_impact": financial_impact,
            "carbon_impact": carbon_impact,
            "pattern_matches": pattern_matches,
            "causal_matches": causal_matches,
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    def _gather_incident_events(self, incident: BlackBoxIncident) -> List[Dict]:
        """Gather all events linked to the incident"""
        incident_events = self.db.query(BlackBoxIncidentEvent).filter(
            BlackBoxIncidentEvent.incident_id == incident.id
        ).order_by(BlackBoxIncidentEvent.sequence_order.asc()).all()
        
        events = []
        for ie in incident_events:
            event = self.db.query(BlackBoxEvent).filter(
                BlackBoxEvent.id == ie.event_id
            ).first()
            if event:
                events.append({
                    "event": event,
                    "role": ie.role,
                    "sequence": ie.sequence_order
                })
        return events
    
    def _gather_sensor_data(self, incident: BlackBoxIncident) -> List[Dict]:
        """Gather sensor events around the incident window"""
        window_start = incident.start_time - timedelta(minutes=self.window_minutes)
        window_end = incident.start_time + timedelta(minutes=self.window_minutes)
        
        sensor_events = self.db.query(BlackBoxEvent).filter(
            BlackBoxEvent.tenant_id == self.tenant_id,
            BlackBoxEvent.event_category == "SENSOR",
            BlackBoxEvent.event_time >= window_start,
            BlackBoxEvent.event_time <= window_end
        )
        
        if incident.root_asset_id:
            sensor_events = sensor_events.filter(
                BlackBoxEvent.asset_id == incident.root_asset_id
            )
        
        return [{"event": e, "type": "sensor"} for e in sensor_events.all()]
    
    def _gather_maintenance_logs(self, incident: BlackBoxIncident) -> List[Dict]:
        """Gather recent maintenance work orders for the asset"""
        if not incident.root_asset_id:
            return []
        
        recent_wos = self.db.query(WorkOrder).filter(
            WorkOrder.tenant_id == self.tenant_id,
            WorkOrder.asset_id == incident.root_asset_id,
            WorkOrder.completed_at >= incident.start_time - timedelta(days=7)
        ).all()
        
        return [{"work_order": wo, "type": "maintenance"} for wo in recent_wos]
    
    def _get_historical_incidents(self, incident: BlackBoxIncident) -> List[BlackBoxIncident]:
        """Get historical incidents for pattern matching"""
        query = self.db.query(BlackBoxIncident).filter(
            BlackBoxIncident.tenant_id == self.tenant_id,
            BlackBoxIncident.id != incident.id,
            BlackBoxIncident.rca_status == "COMPLETED"
        ).order_by(desc(BlackBoxIncident.created_at)).limit(50)
        
        if incident.root_asset_id:
            asset = self.db.query(Asset).filter(Asset.id == incident.root_asset_id).first()
            if asset:
                similar_assets = self.db.query(Asset.id).filter(
                    Asset.tenant_id == self.tenant_id,
                    Asset.asset_type == asset.asset_type
                ).all()
                asset_ids = [a[0] for a in similar_assets]
                query = query.filter(BlackBoxIncident.root_asset_id.in_(asset_ids))
        
        return query.all()
    
    def _build_unified_timeline(self, events: List[Dict], sensor_data: List[Dict], 
                                  maintenance_logs: List[Dict]) -> List[Dict]:
        """Build a unified timeline from all data sources"""
        timeline = []
        
        for e in events:
            timeline.append({
                "time": e["event"].event_time,
                "source": "event",
                "category": e["event"].event_category,
                "severity": e["event"].severity,
                "summary": e["event"].summary,
                "role": e.get("role", "UNKNOWN"),
                "data": e
            })
        
        for s in sensor_data:
            timeline.append({
                "time": s["event"].event_time,
                "source": "sensor",
                "category": "SENSOR",
                "severity": s["event"].severity,
                "summary": s["event"].summary,
                "data": s
            })
        
        for m in maintenance_logs:
            timeline.append({
                "time": m["work_order"].completed_at or m["work_order"].created_at,
                "source": "maintenance",
                "category": "MAINTENANCE",
                "severity": "INFO",
                "summary": f"Work Order: {m['work_order'].title}",
                "data": m
            })
        
        timeline.sort(key=lambda x: x["time"] if x["time"] else datetime.min)
        return timeline
    
    def _extract_event_window(self, timeline: List[Dict], anchor_time: datetime) -> List[Dict]:
        """Extract events within the analysis window"""
        window_start = anchor_time - timedelta(minutes=self.window_minutes)
        window_end = anchor_time + timedelta(minutes=self.window_minutes)
        
        return [
            e for e in timeline 
            if e["time"] and window_start <= e["time"] <= window_end
        ]
    
    def _match_historical_patterns(self, event_window: List[Dict], 
                                     historical_incidents: List[BlackBoxIncident]) -> List[Dict]:
        """Match current event patterns against historical incidents"""
        matches = []
        
        current_categories = set(e["category"] for e in event_window)
        current_severities = set(e["severity"] for e in event_window)
        
        for hist in historical_incidents:
            if not hist.rca_summary:
                continue
            
            hist_summary = hist.rca_summary or {}
            hist_timeline = hist_summary.get("timeline_summary", [])
            
            if not hist_timeline:
                continue
            
            hist_categories = set(e.get("category", "") for e in hist_timeline)
            
            overlap = len(current_categories & hist_categories)
            total = len(current_categories | hist_categories)
            similarity = overlap / total if total > 0 else 0
            
            if similarity >= 0.5:
                matches.append({
                    "incident_id": str(hist.id),
                    "incident_number": hist.incident_number,
                    "similarity": similarity,
                    "root_cause": hist_summary.get("root_cause_category", "UNKNOWN"),
                    "confidence": hist_summary.get("confidence", 0.5)
                })
        
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return matches[:5]
    
    def _apply_causal_rules(self, event_window: List[Dict], 
                             incident: BlackBoxIncident) -> List[Dict]:
        """Apply causal rules to determine root causes"""
        matches = []
        
        asset = None
        if incident.root_asset_id:
            asset = self.db.query(Asset).filter(Asset.id == incident.root_asset_id).first()
        
        asset_type = (asset.asset_type or "").lower() if asset else ""
        
        event_summaries = " ".join(e.get("summary", "") or "" for e in event_window).lower()
        
        for rule in CAUSAL_RULES:
            if rule["asset_types"] and asset_type:
                if not any(t in asset_type for t in rule["asset_types"]):
                    continue
            
            trigger_count = 0
            for trigger in rule["triggers"]:
                metric = trigger["metric"].lower()
                if metric in event_summaries:
                    trigger_count += 1
                    
                if trigger["condition"] == "high" and ("high" in event_summaries or "exceeded" in event_summaries):
                    trigger_count += 0.5
                if trigger["condition"] == "low" and ("low" in event_summaries or "below" in event_summaries):
                    trigger_count += 0.5
            
            if trigger_count >= 1:
                matches.append({
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "rule_name_ar": rule["name_ar"],
                    "root_cause": rule["root_cause"],
                    "confidence_boost": rule["confidence_boost"],
                    "trigger_score": trigger_count / len(rule["triggers"]),
                    "recommended_actions": rule["recommended_actions"],
                    "estimated_downtime": rule["estimated_downtime_hours"]
                })
        
        matches.sort(key=lambda x: x["trigger_score"], reverse=True)
        return matches
    
    def _compute_root_cause_scores(self, pattern_matches: List[Dict], 
                                     causal_matches: List[Dict]) -> Dict[str, float]:
        """Compute probability distribution of root causes"""
        scores = {}
        
        for pm in pattern_matches:
            cause = pm["root_cause"]
            weight = pm["similarity"] * pm["confidence"]
            scores[cause] = scores.get(cause, 0) + weight
        
        for cm in causal_matches:
            cause = cm["root_cause"]
            weight = cm["trigger_score"] * cm["confidence_boost"] * 2
            scores[cause] = scores.get(cause, 0) + weight
        
        if not scores:
            scores["UNKNOWN"] = 0.3
        
        total = sum(scores.values())
        if total > 0:
            scores = {k: round(v / total, 3) for k, v in scores.items()}
        
        scores = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5])
        
        return scores
    
    def _generate_recommended_actions(self, top_cause: str, 
                                        incident: BlackBoxIncident) -> List[Dict]:
        """Generate prioritized recommended actions"""
        actions = []
        
        for rule in CAUSAL_RULES:
            if rule["root_cause"] == top_cause:
                for action in rule["recommended_actions"]:
                    actions.append({
                        "priority": action["priority"],
                        "action": action["action"],
                        "action_ar": action["action_ar"],
                        "category": "CORRECTIVE",
                        "source": "causal_rule"
                    })
                break
        
        if incident.severity in ["CRITICAL", "MAJOR"]:
            actions.insert(0, {
                "priority": 0,
                "action": "Immediately notify operations supervisor and initiate emergency response if required",
                "action_ar": "إخطار مشرف العمليات فورًا وبدء الاستجابة للطوارئ إذا لزم الأمر",
                "category": "IMMEDIATE",
                "source": "severity"
            })
        
        if not actions:
            actions = [
                {
                    "priority": 1,
                    "action": "Perform detailed inspection of affected equipment",
                    "action_ar": "إجراء فحص تفصيلي للمعدات المتأثرة",
                    "category": "INVESTIGATION",
                    "source": "default"
                },
                {
                    "priority": 2,
                    "action": "Review operating parameters and recent changes",
                    "action_ar": "مراجعة معلمات التشغيل والتغييرات الأخيرة",
                    "category": "INVESTIGATION",
                    "source": "default"
                },
                {
                    "priority": 3,
                    "action": "Consult manufacturer documentation and maintenance history",
                    "action_ar": "الرجوع إلى وثائق الشركة المصنعة وتاريخ الصيانة",
                    "category": "INVESTIGATION",
                    "source": "default"
                }
            ]
        
        return actions
    
    def _build_event_story(self, incident: BlackBoxIncident, event_window: List[Dict],
                            top_cause: Tuple[str, float], pattern_matches: List[Dict]) -> str:
        """Build human-readable event narrative in English"""
        asset_name = "Unknown Asset"
        if incident.root_asset_id:
            asset = self.db.query(Asset).filter(Asset.id == incident.root_asset_id).first()
            if asset:
                asset_name = asset.name
        
        start_time = incident.start_time.strftime("%Y-%m-%d %H:%M:%S UTC") if incident.start_time else "Unknown time"
        
        story_parts = [
            f"At {start_time}, the system detected a {incident.severity} severity incident on {asset_name}."
        ]
        
        precursor_events = [e for e in event_window if e.get("role") == "CAUSE" or e["source"] == "sensor"]
        if precursor_events:
            story_parts.append("\nThis was preceded by:")
            for event in precursor_events[:5]:
                time_str = event["time"].strftime("%H:%M:%S") if event["time"] else ""
                story_parts.append(f"  - [{time_str}] {event.get('summary', 'Event')}")
        
        story_parts.append(f"\nThe most likely root cause is {top_cause[0].replace('_', ' ').title()} with {top_cause[1]:.0%} probability.")
        
        if pattern_matches:
            similar_ids = ", ".join(pm["incident_number"] or str(pm["incident_id"])[:8] for pm in pattern_matches[:3])
            story_parts.append(f"\nPast similar incidents ({similar_ids}) showed the same pattern.")
        
        return "\n".join(story_parts)
    
    def _build_event_story_ar(self, incident: BlackBoxIncident, event_window: List[Dict],
                               top_cause: Tuple[str, float], pattern_matches: List[Dict]) -> str:
        """Build human-readable event narrative in Arabic"""
        asset_name = "أصل غير معروف"
        if incident.root_asset_id:
            asset = self.db.query(Asset).filter(Asset.id == incident.root_asset_id).first()
            if asset:
                asset_name = asset.name_ar or asset.name
        
        start_time = incident.start_time.strftime("%Y-%m-%d %H:%M:%S") if incident.start_time else "وقت غير معروف"
        
        severity_ar = {
            "CRITICAL": "حرج",
            "MAJOR": "رئيسي",
            "MINOR": "ثانوي",
            "WARNING": "تحذير",
            "INFO": "معلوماتي"
        }
        
        story_parts = [
            f"في {start_time}، اكتشف النظام حادثة {severity_ar.get(incident.severity, incident.severity)} على {asset_name}."
        ]
        
        story_parts.append(f"\nالسبب الجذري الأكثر احتمالاً هو {top_cause[0].replace('_', ' ')} باحتمال {top_cause[1]:.0%}.")
        
        return "\n".join(story_parts)
    
    def _estimate_financial_impact(self, incident: BlackBoxIncident, 
                                     top_cause: Tuple[str, float]) -> Dict[str, Any]:
        """Estimate financial impact of the incident"""
        cost_model = None
        if incident.root_asset_id:
            cost_model = self.db.query(OptimizationCostModel).filter(
                OptimizationCostModel.tenant_id == self.tenant_id,
                OptimizationCostModel.asset_id == incident.root_asset_id,
                OptimizationCostModel.is_active == True
            ).first()
        
        if not cost_model:
            cost_model = self.db.query(OptimizationCostModel).filter(
                OptimizationCostModel.tenant_id == self.tenant_id,
                OptimizationCostModel.is_active == True
            ).first()
        
        cost_per_hour = float(cost_model.cost_per_hour_downtime) if cost_model and cost_model.cost_per_hour_downtime else 10000.0
        currency = cost_model.currency if cost_model else "SAR"
        
        estimated_downtime = 4.0
        for rule in CAUSAL_RULES:
            if rule["root_cause"] == top_cause[0]:
                estimated_downtime = rule["estimated_downtime_hours"]
                break
        
        if incident.severity == "CRITICAL":
            estimated_downtime *= 1.5
        elif incident.severity == "MINOR":
            estimated_downtime *= 0.5
        
        repair_cost = estimated_downtime * 1000
        production_loss = estimated_downtime * cost_per_hour
        total_cost = repair_cost + production_loss
        
        return {
            "estimated_downtime_hours": estimated_downtime,
            "cost_per_hour": cost_per_hour,
            "currency": currency,
            "repair_cost": repair_cost,
            "production_loss": production_loss,
            "total_estimated_cost": total_cost,
            "confidence": top_cause[1] * 0.8
        }
    
    def _estimate_carbon_impact(self, incident: BlackBoxIncident, 
                                  event_window: List[Dict]) -> Dict[str, Any]:
        """Estimate carbon impact of the incident"""
        asset = None
        if incident.root_asset_id:
            asset = self.db.query(Asset).filter(Asset.id == incident.root_asset_id).first()
        
        asset_type = (asset.asset_type or "default").lower() if asset else "default"
        
        base_consumption = DEFAULT_ENERGY_CONSUMPTION.get(asset_type, DEFAULT_ENERGY_CONSUMPTION["default"])
        
        window_hours = len(event_window) * 0.1
        if window_hours < 1:
            window_hours = 1
        
        energy_used = base_consumption * window_hours
        
        carbon_factor = CARBON_FACTORS.get("electricity", CARBON_FACTORS["default"])
        
        carbon_kg = energy_used * carbon_factor
        
        return {
            "energy_used_kwh": energy_used,
            "carbon_factor": carbon_factor,
            "carbon_kg": round(carbon_kg, 2),
            "carbon_tons": round(carbon_kg / 1000, 4),
            "energy_type": "electricity",
            "window_hours": window_hours
        }


class WorkOrderAutoCreator:
    """
    Automatically creates work orders from incidents based on configurable rules.
    """
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.severity_threshold = ["CRITICAL", "MAJOR"]
        self.confidence_threshold = 0.5
    
    def should_create_work_order(self, incident: BlackBoxIncident) -> bool:
        """Determine if a work order should be auto-created for an incident"""
        if incident.auto_work_order_created:
            return False
        
        if incident.severity in self.severity_threshold:
            return True
        
        root_cause_scores = incident.root_cause_scores or {}
        if root_cause_scores:
            top_confidence = max(root_cause_scores.values()) if root_cause_scores else 0
            if top_confidence >= self.confidence_threshold:
                return True
        
        return False
    
    def create_work_order(self, incident: BlackBoxIncident) -> Optional[WorkOrder]:
        """Create a work order from an incident"""
        if not self.should_create_work_order(incident):
            return None
        
        root_cause_scores = incident.root_cause_scores or {}
        top_cause = max(root_cause_scores.items(), key=lambda x: x[1]) if root_cause_scores else ("UNKNOWN", 0.3)
        
        priority_map = {
            "CRITICAL": "emergency",
            "MAJOR": "high",
            "MINOR": "medium",
            "WARNING": "low",
            "INFO": "low"
        }
        priority = priority_map.get(incident.severity, "medium")
        
        work_type = "corrective"
        for rule in CAUSAL_RULES:
            if rule["root_cause"] == top_cause[0]:
                work_type = "corrective"
                break
        
        asset_name = "Asset"
        if incident.root_asset_id:
            asset = self.db.query(Asset).filter(Asset.id == incident.root_asset_id).first()
            if asset:
                asset_name = asset.name
        
        title = f"{top_cause[0].replace('_', ' ').title()} detected on {asset_name}"
        title_ar = f"تم اكتشاف {top_cause[0].replace('_', ' ')} على {asset_name}"
        
        description_parts = []
        if incident.event_story:
            description_parts.append(incident.event_story)
        
        if incident.recommended_actions:
            description_parts.append("\n\nRecommended Actions:")
            for action in incident.recommended_actions:
                description_parts.append(f"  {action.get('priority', '-')}. {action.get('action', '')}")
        
        if incident.financial_impact_estimate:
            fi = incident.financial_impact_estimate
            description_parts.append(f"\n\nEstimated Impact: {fi.get('total_estimated_cost', 0):,.0f} {fi.get('currency', 'SAR')}")
        
        description = "\n".join(description_parts)
        
        wo_count = self.db.query(func.count(WorkOrder.id)).filter(
            WorkOrder.tenant_id == self.tenant_id
        ).scalar() or 0
        code = f"WO-BB-{datetime.utcnow().year}-{str(wo_count + 1).zfill(5)}"
        
        assignee = self._find_assignee()
        
        work_order = WorkOrder(
            tenant_id=self.tenant_id,
            asset_id=incident.root_asset_id,
            incident_id=str(incident.id),
            code=code,
            work_order_number=code,
            title=title,
            title_ar=title_ar,
            description=description,
            work_type=work_type,
            priority=priority,
            status="open",
            source="BLACKBOX_AUTO",
            assigned_to=assignee.id if assignee else None
        )
        
        self.db.add(work_order)
        self.db.flush()
        
        incident.auto_work_order_id = work_order.id
        incident.auto_work_order_created = True
        
        self.db.commit()
        
        if assignee:
            self._create_notification(work_order, assignee, incident)
        
        return work_order
    
    def _find_assignee(self) -> Optional[User]:
        """Find the appropriate user to assign the work order to"""
        engineer = self.db.query(User).filter(
            User.tenant_id == self.tenant_id,
            User.role.in_(["optimization_engineer", "engineer"]),
            User.is_active == True
        ).first()
        
        if engineer:
            return engineer
        
        admin = self.db.query(User).filter(
            User.tenant_id == self.tenant_id,
            User.role == "tenant_admin",
            User.is_active == True
        ).first()
        
        return admin
    
    def _create_notification(self, work_order: WorkOrder, user: User, incident: BlackBoxIncident):
        """Create a notification for the assigned user"""
        notification = Notification(
            tenant_id=self.tenant_id,
            user_id=user.id,
            notification_type="WORK_ORDER_CREATED",
            title=f"New Work Order Assigned: {work_order.code}",
            title_ar=f"أمر عمل جديد مخصص: {work_order.code}",
            body=f"Work order '{work_order.title}' has been automatically created from incident {incident.incident_number}",
            body_ar=f"تم إنشاء أمر العمل '{work_order.title_ar or work_order.title}' تلقائيًا من الحادثة {incident.incident_number}",
            severity=incident.severity,
            entity_type="work_order",
            entity_id=str(work_order.id),
            action_url=f"/work-orders/{work_order.id}",
            payload={
                "incident_id": str(incident.id),
                "incident_number": incident.incident_number,
                "work_order_id": work_order.id,
                "work_order_code": work_order.code
            }
        )
        self.db.add(notification)
        self.db.commit()


def run_rca_and_create_work_order(db: Session, tenant_id: int, incident_id: str) -> Dict[str, Any]:
    """
    Run complete RCA analysis and auto-create work order if conditions are met.
    This is the main entry point for the incident-to-work-order pipeline.
    """
    rca_engine = RCAImpactEngine(db, tenant_id)
    rca_result = rca_engine.analyze_incident(incident_id)
    
    if "error" in rca_result:
        return rca_result
    
    wo_creator = WorkOrderAutoCreator(db, tenant_id)
    incident = db.query(BlackBoxIncident).filter(
        BlackBoxIncident.id == incident_id,
        BlackBoxIncident.tenant_id == tenant_id
    ).first()
    
    work_order = None
    if incident and wo_creator.should_create_work_order(incident):
        work_order = wo_creator.create_work_order(incident)
    
    result = rca_result.copy()
    result["work_order_created"] = work_order is not None
    if work_order:
        result["work_order"] = work_order.to_dict()
    
    return result
