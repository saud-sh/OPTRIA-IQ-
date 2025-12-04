import random
from datetime import datetime
from typing import Dict, List, Any
from core.connectors.base import BaseConnector, ConnectorStatus, MetricReading

class SAPConnector(BaseConnector):
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.server_url = config.get("server_url", "")
        self.client = config.get("client", "")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
    
    @property
    def connector_type(self) -> str:
        return "sap"
    
    def test_connection(self) -> bool:
        if not self.server_url:
            self.status = ConnectorStatus.ERROR
            self.last_error = "No server URL configured"
            return False
        
        try:
            self.status = ConnectorStatus.CONNECTED
            self.last_connection_time = datetime.utcnow()
            self.last_error = None
            return True
        except Exception as e:
            self.status = ConnectorStatus.ERROR
            self.last_error = str(e)
            return False
    
    def connect(self) -> bool:
        return self.test_connection()
    
    def disconnect(self) -> bool:
        self.status = ConnectorStatus.DISCONNECTED
        return True
    
    def read_tags(self, tags: List[str]) -> List[MetricReading]:
        readings = []
        for tag in tags:
            readings.append(MetricReading(
                tag=tag,
                value=random.uniform(0, 100),
                unit="unit",
                quality="good",
                timestamp=datetime.utcnow(),
                source="sap"
            ))
        return readings
    
    def get_available_tags(self) -> List[str]:
        return [
            "EQUIPMENT_STATUS",
            "FUNCTIONAL_LOCATION",
            "WORK_ORDER_STATUS",
            "MAINTENANCE_PLAN"
        ]
    
    def get_equipment_list(self) -> List[Dict]:
        return [
            {"id": "PUMP-001", "description": "Main Cooling Pump", "location": "PLANT-A"},
            {"id": "COMP-001", "description": "Air Compressor", "location": "PLANT-A"},
            {"id": "TURB-001", "description": "Gas Turbine", "location": "PLANT-B"}
        ]
    
    def get_work_orders(self) -> List[Dict]:
        return [
            {"id": "WO-001", "equipment": "PUMP-001", "type": "PM", "status": "Released"},
            {"id": "WO-002", "equipment": "COMP-001", "type": "CM", "status": "In Progress"}
        ]
    
    @staticmethod
    def get_config_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["server_url", "client"],
            "properties": {
                "server_url": {
                    "type": "string",
                    "description": "SAP server URL",
                    "placeholder": "https://sap.example.com"
                },
                "client": {
                    "type": "string",
                    "description": "SAP client number"
                },
                "username": {
                    "type": "string",
                    "description": "SAP username"
                },
                "password": {
                    "type": "string",
                    "description": "SAP password",
                    "secret": True
                },
                "language": {
                    "type": "string",
                    "default": "EN",
                    "description": "SAP language code"
                }
            }
        }
