import math
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import desc
import pulp

from models.asset import Asset, AssetAIScore
from models.optimization import (
    OptimizationRun, OptimizationScenario, OptimizationRecommendation,
    OptimizationCostModel, WorkOrder
)
from models.user import User

@dataclass
class MaintenancePriorityResult:
    asset_id: int
    asset_name: str
    priority_score: float
    health_score: float
    failure_probability: float
    criticality: str
    recommended_action: str

@dataclass
class DeferralCostResult:
    asset_id: int
    asset_name: str
    days_deferred: int
    expected_cost: float
    risk_increase: float
    recommendation: str

@dataclass
class ProductionRiskResult:
    asset_id: int
    asset_name: str
    current_risk: float
    optimized_risk: float
    suggested_mode: str
    risk_reduction: float

@dataclass
class WorkforceDispatchResult:
    engineer_id: int
    engineer_name: str
    assigned_assets: List[int]
    total_priority: float
    estimated_hours: float
    schedule_date: date


class OptimizationEngine:
    
    def __init__(self, db: Session):
        self.db = db
    
    def run_maintenance_prioritization(
        self, 
        tenant_id: int, 
        user_id: int,
        parameters: Dict[str, Any]
    ) -> OptimizationRun:
        run = OptimizationRun(
            tenant_id=tenant_id,
            run_type="maintenance_priority",
            status="running",
            started_at=datetime.utcnow(),
            input_parameters=parameters,
            created_by=user_id
        )
        self.db.add(run)
        self.db.flush()
        
        try:
            assets = self.db.query(Asset).filter(
                Asset.tenant_id == tenant_id,
                Asset.is_active == True
            ).all()
            
            results = []
            for asset in assets:
                ai_score = self.db.query(AssetAIScore).filter(
                    AssetAIScore.asset_id == asset.id,
                    AssetAIScore.tenant_id == tenant_id
                ).order_by(desc(AssetAIScore.computed_at)).first()
                
                health = float(ai_score.health_score) if ai_score and ai_score.health_score else 75.0
                fail_prob = float(ai_score.failure_probability) if ai_score and ai_score.failure_probability else 0.1
                
                criticality_weights = {"critical": 2.0, "high": 1.5, "medium": 1.0, "low": 0.5}
                crit_weight = criticality_weights.get(asset.criticality, 1.0)
                
                priority_score = (100 - health) * 0.4 + fail_prob * 100 * 0.4 + crit_weight * 10
                
                if priority_score > 70:
                    action = "Immediate maintenance required"
                    action_ar = "صيانة فورية مطلوبة"
                elif priority_score > 50:
                    action = "Schedule maintenance within 7 days"
                    action_ar = "جدولة الصيانة خلال 7 أيام"
                elif priority_score > 30:
                    action = "Plan maintenance within 30 days"
                    action_ar = "تخطيط الصيانة خلال 30 يوماً"
                else:
                    action = "Monitor - no immediate action"
                    action_ar = "مراقبة - لا يلزم إجراء فوري"
                
                results.append({
                    "asset_id": asset.id,
                    "asset_name": asset.name,
                    "priority_score": priority_score,
                    "health_score": health,
                    "failure_probability": fail_prob,
                    "criticality": asset.criticality,
                    "action": action,
                    "action_ar": action_ar
                })
            
            results.sort(key=lambda x: x["priority_score"], reverse=True)
            
            scenario = OptimizationScenario(
                tenant_id=tenant_id,
                run_id=run.id,
                name="Maintenance Priority Ranking",
                name_ar="ترتيب أولوية الصيانة",
                scenario_type="maintenance_priority",
                parameters=parameters,
                results={"ranked_assets": results},
                total_risk_score=sum(r["priority_score"] for r in results) / len(results) if results else 0,
                is_recommended=True
            )
            self.db.add(scenario)
            self.db.flush()
            
            for idx, result in enumerate(results[:20]):
                rec = OptimizationRecommendation(
                    tenant_id=tenant_id,
                    run_id=run.id,
                    scenario_id=scenario.id,
                    asset_id=result["asset_id"],
                    recommendation_type="maintenance",
                    priority_score=result["priority_score"],
                    action_title=result["action"],
                    action_title_ar=result["action_ar"],
                    action_description=f"Asset {result['asset_name']} requires attention based on health score {result['health_score']:.1f}% and failure probability {result['failure_probability']*100:.1f}%",
                    recommended_date=date.today() + timedelta(days=max(1, 7 - idx)),
                    status="pending"
                )
                self.db.add(rec)
            
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.output_summary = {
                "total_assets": len(results),
                "high_priority": len([r for r in results if r["priority_score"] > 70]),
                "medium_priority": len([r for r in results if 50 < r["priority_score"] <= 70]),
                "low_priority": len([r for r in results if r["priority_score"] <= 50])
            }
            
            self.db.commit()
            
        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            self.db.commit()
        
        return run
    
    def run_deferral_cost_analysis(
        self,
        tenant_id: int,
        user_id: int,
        parameters: Dict[str, Any]
    ) -> OptimizationRun:
        run = OptimizationRun(
            tenant_id=tenant_id,
            run_type="deferral_cost",
            status="running",
            started_at=datetime.utcnow(),
            input_parameters=parameters,
            created_by=user_id
        )
        self.db.add(run)
        self.db.flush()
        
        try:
            deferral_days = parameters.get("deferral_days", 7)
            
            assets = self.db.query(Asset).filter(
                Asset.tenant_id == tenant_id,
                Asset.is_active == True
            ).all()
            
            results = []
            total_deferral_cost = 0
            
            for asset in assets:
                cost_model = self.db.query(OptimizationCostModel).filter(
                    OptimizationCostModel.tenant_id == tenant_id,
                    OptimizationCostModel.asset_id == asset.id,
                    OptimizationCostModel.is_active == True
                ).first()
                
                if not cost_model:
                    cost_model = self.db.query(OptimizationCostModel).filter(
                        OptimizationCostModel.tenant_id == tenant_id,
                        OptimizationCostModel.site_id == asset.site_id,
                        OptimizationCostModel.is_active == True
                    ).first()
                
                hourly_cost = float(cost_model.cost_per_hour_downtime) if cost_model and cost_model.cost_per_hour_downtime else 10000
                failure_cost = float(cost_model.cost_per_failure) if cost_model and cost_model.cost_per_failure else 50000
                
                ai_score = self.db.query(AssetAIScore).filter(
                    AssetAIScore.asset_id == asset.id,
                    AssetAIScore.tenant_id == tenant_id
                ).order_by(desc(AssetAIScore.computed_at)).first()
                
                fail_prob = float(ai_score.failure_probability) if ai_score and ai_score.failure_probability else 0.1
                
                prob_increase = fail_prob * (1 + 0.05 * deferral_days)
                prob_increase = min(prob_increase, 0.95)
                
                expected_cost = prob_increase * failure_cost + (prob_increase * 24 * hourly_cost * 0.1)
                total_deferral_cost += expected_cost
                
                if expected_cost > 100000:
                    rec = "Do not defer - high risk"
                    rec_ar = "لا تؤجل - مخاطر عالية"
                elif expected_cost > 50000:
                    rec = "Defer with caution"
                    rec_ar = "تأجيل بحذر"
                else:
                    rec = "Safe to defer"
                    rec_ar = "آمن للتأجيل"
                
                results.append({
                    "asset_id": asset.id,
                    "asset_name": asset.name,
                    "days_deferred": deferral_days,
                    "current_failure_prob": fail_prob,
                    "projected_failure_prob": prob_increase,
                    "expected_cost": expected_cost,
                    "recommendation": rec,
                    "recommendation_ar": rec_ar
                })
            
            results.sort(key=lambda x: x["expected_cost"], reverse=True)
            
            scenario = OptimizationScenario(
                tenant_id=tenant_id,
                run_id=run.id,
                name=f"Deferral Cost Analysis ({deferral_days} days)",
                name_ar=f"تحليل تكلفة التأجيل ({deferral_days} يوم)",
                scenario_type="deferral_cost",
                parameters=parameters,
                results={"cost_analysis": results},
                total_cost=total_deferral_cost,
                is_recommended=True
            )
            self.db.add(scenario)
            self.db.flush()
            
            for result in results[:10]:
                rec = OptimizationRecommendation(
                    tenant_id=tenant_id,
                    run_id=run.id,
                    scenario_id=scenario.id,
                    asset_id=result["asset_id"],
                    recommendation_type="deferral",
                    deferral_cost=result["expected_cost"],
                    action_title=result["recommendation"],
                    action_title_ar=result["recommendation_ar"],
                    action_description=f"Deferring maintenance by {deferral_days} days increases failure probability from {result['current_failure_prob']*100:.1f}% to {result['projected_failure_prob']*100:.1f}%",
                    status="pending"
                )
                self.db.add(rec)
            
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.output_summary = {
                "total_deferral_cost": total_deferral_cost,
                "assets_analyzed": len(results),
                "high_risk_assets": len([r for r in results if r["expected_cost"] > 100000])
            }
            
            self.db.commit()
            
        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            self.db.commit()
        
        return run
    
    def run_production_risk_optimization(
        self,
        tenant_id: int,
        user_id: int,
        parameters: Dict[str, Any]
    ) -> OptimizationRun:
        run = OptimizationRun(
            tenant_id=tenant_id,
            run_type="production_risk",
            status="running",
            started_at=datetime.utcnow(),
            input_parameters=parameters,
            created_by=user_id
        )
        self.db.add(run)
        self.db.flush()
        
        try:
            target_risk_reduction = parameters.get("target_risk_reduction", 20)
            
            assets = self.db.query(Asset).filter(
                Asset.tenant_id == tenant_id,
                Asset.is_active == True
            ).all()
            
            results = []
            total_current_risk = 0
            total_optimized_risk = 0
            
            for asset in assets:
                ai_score = self.db.query(AssetAIScore).filter(
                    AssetAIScore.asset_id == asset.id,
                    AssetAIScore.tenant_id == tenant_id
                ).order_by(desc(AssetAIScore.computed_at)).first()
                
                current_risk = float(ai_score.production_risk_index) if ai_score and ai_score.production_risk_index else 50.0
                total_current_risk += current_risk
                
                if current_risk > 70:
                    mode = "Reduce load to 60%"
                    mode_ar = "تقليل الحمل إلى 60%"
                    reduction = current_risk * 0.35
                elif current_risk > 50:
                    mode = "Reduce load to 80%"
                    mode_ar = "تقليل الحمل إلى 80%"
                    reduction = current_risk * 0.20
                elif current_risk > 30:
                    mode = "Monitor closely"
                    mode_ar = "مراقبة عن كثب"
                    reduction = current_risk * 0.10
                else:
                    mode = "Normal operation"
                    mode_ar = "التشغيل العادي"
                    reduction = 0
                
                optimized_risk = current_risk - reduction
                total_optimized_risk += optimized_risk
                
                results.append({
                    "asset_id": asset.id,
                    "asset_name": asset.name,
                    "current_risk": current_risk,
                    "optimized_risk": optimized_risk,
                    "suggested_mode": mode,
                    "suggested_mode_ar": mode_ar,
                    "risk_reduction": reduction
                })
            
            results.sort(key=lambda x: x["current_risk"], reverse=True)
            
            scenario = OptimizationScenario(
                tenant_id=tenant_id,
                run_id=run.id,
                name="Production Risk Optimization",
                name_ar="تحسين مخاطر الإنتاج",
                scenario_type="production_risk",
                parameters=parameters,
                results={"risk_analysis": results},
                total_risk_score=total_optimized_risk / len(results) if results else 0,
                is_recommended=True
            )
            self.db.add(scenario)
            self.db.flush()
            
            for result in results[:15]:
                if result["risk_reduction"] > 0:
                    rec = OptimizationRecommendation(
                        tenant_id=tenant_id,
                        run_id=run.id,
                        scenario_id=scenario.id,
                        asset_id=result["asset_id"],
                        recommendation_type="production_risk",
                        risk_reduction=result["risk_reduction"],
                        action_title=result["suggested_mode"],
                        action_title_ar=result["suggested_mode_ar"],
                        action_description=f"Reduce production risk from {result['current_risk']:.1f}% to {result['optimized_risk']:.1f}% by adjusting operating mode",
                        status="pending"
                    )
                    self.db.add(rec)
            
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.output_summary = {
                "total_current_risk": total_current_risk,
                "total_optimized_risk": total_optimized_risk,
                "risk_reduction_achieved": ((total_current_risk - total_optimized_risk) / total_current_risk * 100) if total_current_risk > 0 else 0,
                "assets_requiring_action": len([r for r in results if r["risk_reduction"] > 0])
            }
            
            self.db.commit()
            
        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            self.db.commit()
        
        return run
    
    def run_workforce_dispatch_optimization(
        self,
        tenant_id: int,
        user_id: int,
        parameters: Dict[str, Any]
    ) -> OptimizationRun:
        run = OptimizationRun(
            tenant_id=tenant_id,
            run_type="workforce_dispatch",
            status="running",
            started_at=datetime.utcnow(),
            input_parameters=parameters,
            created_by=user_id
        )
        self.db.add(run)
        self.db.flush()
        
        try:
            planning_days = parameters.get("planning_days", 7)
            max_hours_per_day = parameters.get("max_hours_per_day", 8)
            
            engineers = self.db.query(User).filter(
                User.tenant_id == tenant_id,
                User.role.in_(["engineer", "optimization_engineer"]),
                User.is_active == True
            ).all()
            
            open_work_orders = self.db.query(WorkOrder).filter(
                WorkOrder.tenant_id == tenant_id,
                WorkOrder.status.in_(["open", "pending"])
            ).all()
            
            priority_assets = self.db.query(Asset).join(
                AssetAIScore, Asset.id == AssetAIScore.asset_id
            ).filter(
                Asset.tenant_id == tenant_id,
                Asset.is_active == True
            ).order_by(desc(AssetAIScore.production_risk_index)).limit(20).all()
            
            assignments = []
            
            if engineers and (open_work_orders or priority_assets):
                problem = pulp.LpProblem("WorkforceDispatch", pulp.LpMinimize)
                
                tasks = []
                for wo in open_work_orders:
                    tasks.append({
                        "id": f"wo_{wo.id}",
                        "type": "work_order",
                        "asset_id": wo.asset_id,
                        "priority": {"high": 3, "medium": 2, "low": 1}.get(wo.priority, 2),
                        "hours": float(wo.estimated_hours) if wo.estimated_hours else 4
                    })
                
                for asset in priority_assets[:10]:
                    if not any(t["asset_id"] == asset.id for t in tasks):
                        tasks.append({
                            "id": f"asset_{asset.id}",
                            "type": "inspection",
                            "asset_id": asset.id,
                            "priority": 2,
                            "hours": 2
                        })
                
                x = {}
                for eng in engineers:
                    for task in tasks:
                        for day in range(planning_days):
                            x[(eng.id, task["id"], day)] = pulp.LpVariable(
                                f"x_{eng.id}_{task['id']}_{day}", cat=pulp.LpBinary
                            )
                
                problem += pulp.lpSum(
                    -task["priority"] * x[(eng.id, task["id"], day)]
                    for eng in engineers
                    for task in tasks
                    for day in range(planning_days)
                )
                
                for task in tasks:
                    problem += pulp.lpSum(
                        x[(eng.id, task["id"], day)]
                        for eng in engineers
                        for day in range(planning_days)
                    ) <= 1
                
                for eng in engineers:
                    for day in range(planning_days):
                        problem += pulp.lpSum(
                            task["hours"] * x[(eng.id, task["id"], day)]
                            for task in tasks
                        ) <= max_hours_per_day
                
                problem.solve(pulp.PULP_CBC_CMD(msg=0))
                
                for eng in engineers:
                    eng_assignments = []
                    total_hours = 0
                    for day in range(planning_days):
                        for task in tasks:
                            if x[(eng.id, task["id"], day)].value() == 1:
                                eng_assignments.append({
                                    "task_id": task["id"],
                                    "task_type": task["type"],
                                    "asset_id": task["asset_id"],
                                    "day": day,
                                    "hours": task["hours"],
                                    "priority": task["priority"]
                                })
                                total_hours += task["hours"]
                    
                    if eng_assignments:
                        assignments.append({
                            "engineer_id": eng.id,
                            "engineer_name": eng.full_name or eng.username,
                            "assignments": eng_assignments,
                            "total_hours": total_hours,
                            "total_priority": sum(a["priority"] for a in eng_assignments)
                        })
            
            scenario = OptimizationScenario(
                tenant_id=tenant_id,
                run_id=run.id,
                name=f"Workforce Dispatch ({planning_days} days)",
                name_ar=f"جدولة القوى العاملة ({planning_days} يوم)",
                scenario_type="workforce_dispatch",
                parameters=parameters,
                results={"dispatch_plan": assignments},
                is_recommended=True
            )
            self.db.add(scenario)
            self.db.flush()
            
            for assignment in assignments:
                for task in assignment["assignments"]:
                    rec = OptimizationRecommendation(
                        tenant_id=tenant_id,
                        run_id=run.id,
                        scenario_id=scenario.id,
                        asset_id=task["asset_id"],
                        recommendation_type="dispatch",
                        priority_score=task["priority"],
                        action_title=f"Assign {assignment['engineer_name']} - {task['task_type']}",
                        action_title_ar=f"تعيين {assignment['engineer_name']} - {task['task_type']}",
                        action_description=f"Scheduled for day {task['day'] + 1}, estimated {task['hours']} hours",
                        recommended_date=date.today() + timedelta(days=task["day"]),
                        assigned_to=assignment["engineer_id"],
                        status="pending"
                    )
                    self.db.add(rec)
            
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.output_summary = {
                "engineers_assigned": len(assignments),
                "total_tasks": sum(len(a["assignments"]) for a in assignments),
                "total_hours_planned": sum(a["total_hours"] for a in assignments),
                "planning_days": planning_days
            }
            
            self.db.commit()
            
        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            self.db.commit()
        
        return run


def get_optimization_engine(db: Session) -> OptimizationEngine:
    return OptimizationEngine(db)
