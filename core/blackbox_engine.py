"""
Industrial Black Box Engine
Event collection, incident detection, and root cause analysis.
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from models.blackbox import (
    BlackBoxEvent, BlackBoxIncident, BlackBoxIncidentEvent, BlackBoxRCARule,
    SOURCE_SYSTEMS, EVENT_CATEGORIES, SEVERITY_LEVELS, EVENT_ROLES, RCA_CATEGORIES
)


class EventCollector:
    """
    Collects and normalizes events from OPTRIA internal tables.
    Maps alerts, work orders, and AI outputs to canonical BlackBoxEvent format.
    """
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
    
    def collect_alerts(self, since: datetime = None) -> List[BlackBoxEvent]:
        """Collect alerts and convert to BlackBox events"""
        from models.asset import Alert
        
        query = self.db.query(Alert).filter(Alert.tenant_id == self.tenant_id)
        if since:
            query = query.filter(Alert.created_at >= since)
        
        events = []
        for alert in query.all():
            existing = self.db.query(BlackBoxEvent).filter(
                BlackBoxEvent.tenant_id == self.tenant_id,
                BlackBoxEvent.source_system == "OPTRIA_ALERT",
                BlackBoxEvent.source_id == str(alert.id)
            ).first()
            
            if existing:
                continue
            
            severity_map = {
                "info": "INFO",
                "warning": "WARNING",
                "minor": "MINOR",
                "major": "MAJOR",
                "critical": "CRITICAL"
            }
            
            event = BlackBoxEvent(
                tenant_id=self.tenant_id,
                asset_id=alert.asset_id,
                site_id=getattr(alert, 'site_id', None),
                source_system="OPTRIA_ALERT",
                source_type="ALERT",
                source_id=str(alert.id),
                event_time=alert.created_at,
                severity=severity_map.get(alert.severity, "INFO"),
                event_category="ALERT",
                summary=f"{alert.alert_type}: {alert.message[:200] if alert.message else 'No message'}",
                payload={
                    "alert_type": alert.alert_type,
                    "message": alert.message,
                    "threshold_value": getattr(alert, 'threshold_value', None),
                    "actual_value": getattr(alert, 'actual_value', None),
                    "status": alert.status
                },
                tags=[alert.alert_type, alert.severity] if alert.alert_type else [alert.severity]
            )
            events.append(event)
        
        return events
    
    def collect_work_orders(self, since: datetime = None) -> List[BlackBoxEvent]:
        """Collect work orders and convert to BlackBox events"""
        from models.optimization import WorkOrder
        
        query = self.db.query(WorkOrder).filter(WorkOrder.tenant_id == self.tenant_id)
        if since:
            query = query.filter(WorkOrder.created_at >= since)
        
        events = []
        for wo in query.all():
            existing = self.db.query(BlackBoxEvent).filter(
                BlackBoxEvent.tenant_id == self.tenant_id,
                BlackBoxEvent.source_system == "OPTRIA_WORKORDER",
                BlackBoxEvent.source_id == str(wo.id)
            ).first()
            
            if existing:
                continue
            
            priority_severity = {
                "low": "INFO",
                "medium": "WARNING",
                "high": "MAJOR",
                "critical": "CRITICAL",
                "emergency": "CRITICAL"
            }
            
            event = BlackBoxEvent(
                tenant_id=self.tenant_id,
                asset_id=wo.asset_id,
                site_id=getattr(wo, 'site_id', None),
                source_system="OPTRIA_WORKORDER",
                source_type="WORK_ORDER",
                source_id=str(wo.id),
                event_time=wo.created_at,
                severity=priority_severity.get(wo.priority, "INFO") if wo.priority else "INFO",
                event_category="MAINTENANCE",
                summary=f"Work Order: {wo.title[:200] if wo.title else 'Untitled'}",
                payload={
                    "work_order_number": wo.work_order_number,
                    "title": wo.title,
                    "work_type": wo.work_type,
                    "priority": wo.priority,
                    "status": wo.status,
                    "scheduled_start": wo.scheduled_start.isoformat() if wo.scheduled_start else None,
                    "scheduled_end": wo.scheduled_end.isoformat() if wo.scheduled_end else None
                },
                tags=["work_order", wo.work_type] if wo.work_type else ["work_order"]
            )
            events.append(event)
        
        return events
    
    def collect_ai_outputs(self, since: datetime = None) -> List[BlackBoxEvent]:
        """Collect AI predictions and anomalies as events"""
        from models.asset import Asset
        
        query = self.db.query(Asset).filter(Asset.tenant_id == self.tenant_id)
        
        events = []
        for asset in query.all():
            health_score = getattr(asset, 'health_score', None)
            failure_probability = getattr(asset, 'failure_probability', None)
            anomaly_score = getattr(asset, 'anomaly_score', None)
            
            if failure_probability and failure_probability > 0.7:
                event_id = f"ai_failure_{asset.id}_{datetime.utcnow().strftime('%Y%m%d')}"
                existing = self.db.query(BlackBoxEvent).filter(
                    BlackBoxEvent.tenant_id == self.tenant_id,
                    BlackBoxEvent.source_system == "AI_ENGINE",
                    BlackBoxEvent.source_id == event_id
                ).first()
                
                if not existing:
                    severity = "CRITICAL" if failure_probability > 0.9 else "MAJOR"
                    event = BlackBoxEvent(
                        tenant_id=self.tenant_id,
                        asset_id=asset.id,
                        site_id=asset.site_id,
                        source_system="AI_ENGINE",
                        source_type="AI_PREDICTION",
                        source_id=event_id,
                        event_time=datetime.utcnow(),
                        severity=severity,
                        event_category="AI_OUTPUT",
                        summary=f"High failure probability detected: {failure_probability:.1%}",
                        payload={
                            "prediction_type": "failure_probability",
                            "value": failure_probability,
                            "health_score": health_score,
                            "asset_name": asset.name
                        },
                        tags=["ai_prediction", "failure_risk"]
                    )
                    events.append(event)
            
            if anomaly_score and anomaly_score > 0.8:
                event_id = f"ai_anomaly_{asset.id}_{datetime.utcnow().strftime('%Y%m%d%H')}"
                existing = self.db.query(BlackBoxEvent).filter(
                    BlackBoxEvent.tenant_id == self.tenant_id,
                    BlackBoxEvent.source_system == "AI_ENGINE",
                    BlackBoxEvent.source_id == event_id
                ).first()
                
                if not existing:
                    event = BlackBoxEvent(
                        tenant_id=self.tenant_id,
                        asset_id=asset.id,
                        site_id=asset.site_id,
                        source_system="AI_ENGINE",
                        source_type="ANOMALY",
                        source_id=event_id,
                        event_time=datetime.utcnow(),
                        severity="MAJOR",
                        event_category="AI_OUTPUT",
                        summary=f"Anomaly detected: score {anomaly_score:.2f}",
                        payload={
                            "prediction_type": "anomaly",
                            "anomaly_score": anomaly_score,
                            "health_score": health_score,
                            "asset_name": asset.name
                        },
                        tags=["ai_prediction", "anomaly"]
                    )
                    events.append(event)
        
        return events
    
    def run_collection(self, since: datetime = None) -> Dict[str, int]:
        """Run full collection cycle"""
        results = {
            "alerts": 0,
            "work_orders": 0,
            "ai_outputs": 0,
            "total": 0
        }
        
        try:
            alert_events = self.collect_alerts(since)
            for event in alert_events:
                self.db.add(event)
            results["alerts"] = len(alert_events)
            
            wo_events = self.collect_work_orders(since)
            for event in wo_events:
                self.db.add(event)
            results["work_orders"] = len(wo_events)
            
            ai_events = self.collect_ai_outputs(since)
            for event in ai_events:
                self.db.add(event)
            results["ai_outputs"] = len(ai_events)
            
            self.db.commit()
            results["total"] = results["alerts"] + results["work_orders"] + results["ai_outputs"]
            
        except Exception as e:
            self.db.rollback()
            raise e
        
        return results


class IncidentEngine:
    """
    Detects and manages incidents from Black Box events.
    Groups related events and builds incident timelines.
    """
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.window_before = timedelta(minutes=30)
        self.window_after = timedelta(minutes=30)
    
    def find_trigger_events(self) -> List[BlackBoxEvent]:
        """Find events that should trigger incident creation"""
        trigger_events = self.db.query(BlackBoxEvent).filter(
            BlackBoxEvent.tenant_id == self.tenant_id,
            BlackBoxEvent.is_processed == False,
            or_(
                BlackBoxEvent.severity.in_(["CRITICAL", "MAJOR"]),
                BlackBoxEvent.event_category == "FAILURE"
            )
        ).order_by(BlackBoxEvent.event_time.asc()).all()
        
        return trigger_events
    
    def create_incident_from_event(self, trigger_event: BlackBoxEvent) -> BlackBoxIncident:
        """Create a new incident from a trigger event"""
        incident = BlackBoxIncident(
            tenant_id=self.tenant_id,
            incident_type=self._determine_incident_type(trigger_event),
            status="OPEN",
            severity=trigger_event.severity,
            root_asset_id=trigger_event.asset_id,
            site_id=trigger_event.site_id,
            start_time=trigger_event.event_time - self.window_before,
            trigger_event_id=trigger_event.id,
            title=f"Incident: {trigger_event.summary[:100] if trigger_event.summary else 'Untitled'}",
            description=trigger_event.summary,
            impact_scope={
                "assets": [trigger_event.asset_id] if trigger_event.asset_id else [],
                "sites": [trigger_event.site_id] if trigger_event.site_id else []
            }
        )
        
        self.db.add(incident)
        self.db.flush()
        
        incident.generate_incident_number(self.db)
        
        incident_event = BlackBoxIncidentEvent(
            tenant_id=self.tenant_id,
            incident_id=incident.id,
            event_id=trigger_event.id,
            role="CAUSE",
            sequence_order=0
        )
        self.db.add(incident_event)
        
        trigger_event.is_processed = True
        
        self._gather_related_events(incident, trigger_event)
        
        self.db.commit()
        return incident
    
    def _determine_incident_type(self, event: BlackBoxEvent) -> str:
        """Determine incident type from event characteristics"""
        if event.event_category == "FAILURE":
            return "FAILURE"
        if event.severity == "CRITICAL":
            return "FAILURE"
        if "anomaly" in (event.tags or []):
            return "ANOMALY"
        if event.severity == "MAJOR":
            return "NEAR_MISS"
        return "ANOMALY"
    
    def _gather_related_events(self, incident: BlackBoxIncident, trigger_event: BlackBoxEvent):
        """Gather events within the incident window"""
        window_start = trigger_event.event_time - self.window_before
        window_end = trigger_event.event_time + self.window_after
        
        related_events = self.db.query(BlackBoxEvent).filter(
            BlackBoxEvent.tenant_id == self.tenant_id,
            BlackBoxEvent.id != trigger_event.id,
            BlackBoxEvent.event_time >= window_start,
            BlackBoxEvent.event_time <= window_end,
            or_(
                BlackBoxEvent.asset_id == trigger_event.asset_id,
                BlackBoxEvent.site_id == trigger_event.site_id
            )
        ).order_by(BlackBoxEvent.event_time.asc()).all()
        
        sequence = 1
        for event in related_events:
            role = self._classify_event_role(event, trigger_event)
            
            incident_event = BlackBoxIncidentEvent(
                tenant_id=self.tenant_id,
                incident_id=incident.id,
                event_id=event.id,
                role=role,
                sequence_order=sequence
            )
            self.db.add(incident_event)
            
            event.is_processed = True
            sequence += 1
            
            if event.asset_id and event.asset_id not in incident.impact_scope.get("assets", []):
                incident.impact_scope["assets"].append(event.asset_id)
    
    def _classify_event_role(self, event: BlackBoxEvent, trigger: BlackBoxEvent) -> str:
        """Classify event's role in the incident"""
        if event.event_time < trigger.event_time:
            if event.severity in ["CRITICAL", "MAJOR"]:
                return "CAUSE"
            if event.event_category == "MAINTENANCE":
                return "CONTEXT"
            return "CONTEXT"
        else:
            if event.severity in ["CRITICAL", "MAJOR"]:
                return "SYMPTOM"
            return "CONTEXT"
    
    def run_detection(self) -> Dict[str, Any]:
        """Run incident detection cycle"""
        results = {
            "trigger_events_found": 0,
            "incidents_created": 0,
            "events_processed": 0
        }
        
        trigger_events = self.find_trigger_events()
        results["trigger_events_found"] = len(trigger_events)
        
        for event in trigger_events:
            existing = self.db.query(BlackBoxIncidentEvent).filter(
                BlackBoxIncidentEvent.event_id == event.id
            ).first()
            
            if not existing:
                self.create_incident_from_event(event)
                results["incidents_created"] += 1
            
            results["events_processed"] += 1
        
        return results
    
    def update_incident(self, incident_id: str, updates: Dict) -> BlackBoxIncident:
        """Update an existing incident"""
        incident = self.db.query(BlackBoxIncident).filter(
            BlackBoxIncident.id == incident_id,
            BlackBoxIncident.tenant_id == self.tenant_id
        ).first()
        
        if not incident:
            return None
        
        allowed_fields = ["status", "severity", "title", "description", "assigned_to", 
                         "impact_estimate", "rca_summary", "rca_status"]
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(incident, field, value)
        
        if updates.get("status") == "RESOLVED":
            incident.resolved_at = datetime.utcnow()
            incident.end_time = datetime.utcnow()
        
        self.db.commit()
        return incident


class RCAEngine:
    """
    Rule-based Root Cause Analysis engine.
    Evaluates event patterns to determine probable causes.
    """
    
    DEFAULT_RULES = [
        {
            "name": "Pressure Cascade Failure",
            "description": "Pressure spike followed by temperature rise and trip",
            "pattern": {
                "sequence": [
                    {"category": "SENSOR", "contains": "pressure", "severity": ["MAJOR", "CRITICAL"]},
                    {"category": "ALERT", "within_minutes": 10}
                ]
            },
            "root_cause_category": "MECHANICAL_STRESS",
            "confidence": 0.85
        },
        {
            "name": "Post-Maintenance Failure",
            "description": "Failure occurring shortly after maintenance work",
            "pattern": {
                "sequence": [
                    {"category": "MAINTENANCE", "within_hours": -24},
                    {"category": "FAILURE", "role": "trigger"}
                ]
            },
            "root_cause_category": "MAINTENANCE_INDUCED",
            "confidence": 0.75
        },
        {
            "name": "Cascading Alert Pattern",
            "description": "Multiple alerts in quick succession indicating cascade",
            "pattern": {
                "count": {"category": "ALERT", "min": 3, "within_minutes": 15}
            },
            "root_cause_category": "PROCESS_UPSET",
            "confidence": 0.70
        },
        {
            "name": "AI Predicted Failure",
            "description": "AI prediction followed by actual failure",
            "pattern": {
                "sequence": [
                    {"source_system": "AI_ENGINE", "within_hours": -48},
                    {"severity": ["CRITICAL"], "role": "trigger"}
                ]
            },
            "root_cause_category": "MECHANICAL_STRESS",
            "confidence": 0.80
        }
    ]
    
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
    
    def analyze_incident(self, incident_id: str) -> Dict[str, Any]:
        """Perform RCA on an incident"""
        incident = self.db.query(BlackBoxIncident).filter(
            BlackBoxIncident.id == incident_id,
            BlackBoxIncident.tenant_id == self.tenant_id
        ).first()
        
        if not incident:
            return {"error": "Incident not found"}
        
        incident_events = self.db.query(BlackBoxIncidentEvent).filter(
            BlackBoxIncidentEvent.incident_id == incident_id
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
        
        rules = self._get_rules()
        
        matched_rules = []
        for rule in rules:
            if self._evaluate_rule(rule, events):
                matched_rules.append({
                    "rule_name": rule["name"],
                    "root_cause_category": rule["root_cause_category"],
                    "confidence": rule["confidence"],
                    "description": rule.get("description", "")
                })
        
        rca_summary = self._build_rca_summary(incident, events, matched_rules)
        
        incident.rca_summary = rca_summary
        incident.rca_status = "COMPLETED"
        incident.rca_completed_at = datetime.utcnow()
        self.db.commit()
        
        return rca_summary
    
    def _get_rules(self) -> List[Dict]:
        """Get all active RCA rules (system + tenant)"""
        db_rules = self.db.query(BlackBoxRCARule).filter(
            or_(
                BlackBoxRCARule.tenant_id == self.tenant_id,
                BlackBoxRCARule.is_system == True
            ),
            BlackBoxRCARule.is_active == True
        ).order_by(BlackBoxRCARule.priority.asc()).all()
        
        rules = [r.pattern for r in db_rules if r.pattern]
        rules.extend(self.DEFAULT_RULES)
        
        return rules
    
    def _evaluate_rule(self, rule: Dict, events: List[Dict]) -> bool:
        """Evaluate if a rule pattern matches the events"""
        pattern = rule.get("pattern", {})
        
        if "sequence" in pattern:
            return self._check_sequence(pattern["sequence"], events)
        
        if "count" in pattern:
            return self._check_count(pattern["count"], events)
        
        return False
    
    def _check_sequence(self, sequence: List[Dict], events: List[Dict]) -> bool:
        """Check if events match a sequence pattern"""
        if not events:
            return False
        
        seq_idx = 0
        for event_data in events:
            event = event_data["event"]
            pattern = sequence[seq_idx]
            
            if self._event_matches_pattern(event, pattern):
                seq_idx += 1
                if seq_idx >= len(sequence):
                    return True
        
        return False
    
    def _check_count(self, count_pattern: Dict, events: List[Dict]) -> bool:
        """Check if event count matches pattern"""
        category = count_pattern.get("category")
        min_count = count_pattern.get("min", 1)
        
        matching = 0
        for event_data in events:
            event = event_data["event"]
            if not category or event.event_category == category:
                matching += 1
        
        return matching >= min_count
    
    def _event_matches_pattern(self, event: BlackBoxEvent, pattern: Dict) -> bool:
        """Check if an event matches a pattern"""
        if "category" in pattern:
            if event.event_category != pattern["category"]:
                return False
        
        if "severity" in pattern:
            if event.severity not in pattern["severity"]:
                return False
        
        if "source_system" in pattern:
            if event.source_system != pattern["source_system"]:
                return False
        
        if "contains" in pattern:
            summary = (event.summary or "").lower()
            if pattern["contains"].lower() not in summary:
                return False
        
        return True
    
    def _build_rca_summary(self, incident: BlackBoxIncident, events: List[Dict], 
                           matched_rules: List[Dict]) -> Dict:
        """Build comprehensive RCA summary"""
        cause_events = [e for e in events if e["role"] == "CAUSE"]
        symptom_events = [e for e in events if e["role"] == "SYMPTOM"]
        context_events = [e for e in events if e["role"] == "CONTEXT"]
        
        if matched_rules:
            best_match = max(matched_rules, key=lambda r: r["confidence"])
            root_cause_category = best_match["root_cause_category"]
            confidence = best_match["confidence"]
        else:
            root_cause_category = "UNKNOWN"
            confidence = 0.3
        
        contributing_factors = []
        for event_data in cause_events:
            event = event_data["event"]
            contributing_factors.append({
                "event_id": str(event.id),
                "summary": event.summary,
                "category": event.event_category,
                "severity": event.severity,
                "time": event.event_time.isoformat() if event.event_time else None
            })
        
        timeline_summary = []
        for event_data in sorted(events, key=lambda e: e["event"].event_time):
            event = event_data["event"]
            timeline_summary.append({
                "time": event.event_time.isoformat() if event.event_time else None,
                "summary": event.summary,
                "role": event_data["role"],
                "severity": event.severity
            })
        
        return {
            "root_cause_category": root_cause_category,
            "confidence": confidence,
            "matched_rules": matched_rules,
            "contributing_factors": contributing_factors,
            "timeline_summary": timeline_summary[:20],
            "statistics": {
                "total_events": len(events),
                "cause_events": len(cause_events),
                "symptom_events": len(symptom_events),
                "context_events": len(context_events)
            },
            "analysis_time": datetime.utcnow().isoformat()
        }


def run_blackbox_pipeline(db: Session, tenant_id: int) -> Dict[str, Any]:
    """Run the complete Black Box pipeline for a tenant"""
    results = {
        "collection": {},
        "detection": {},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    collector = EventCollector(db, tenant_id)
    results["collection"] = collector.run_collection(
        since=datetime.utcnow() - timedelta(hours=24)
    )
    
    engine = IncidentEngine(db, tenant_id)
    results["detection"] = engine.run_detection()
    
    return results
