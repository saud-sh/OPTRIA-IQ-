import random
from datetime import datetime
from typing import Dict, List, Any
from core.connectors.base import BaseConnector, ConnectorStatus, MetricReading

class SQLConnector(BaseConnector):
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection_string = config.get("connection_string", "")
        self.database_type = config.get("database_type", "postgresql")
        self.query_template = config.get("query_template", "")
    
    @property
    def connector_type(self) -> str:
        return "sql"
    
    def test_connection(self) -> bool:
        if not self.connection_string:
            self.status = ConnectorStatus.ERROR
            self.last_error = "No connection string configured"
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
                source="sql"
            ))
        return readings
    
    def get_available_tags(self) -> List[str]:
        return [
            "sensor_data.temperature",
            "sensor_data.pressure",
            "sensor_data.flow_rate",
            "equipment_status.running",
            "equipment_status.alarm"
        ]
    
    def execute_query(self, query: str) -> List[Dict]:
        return []
    
    @staticmethod
    def get_config_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["connection_string", "database_type"],
            "properties": {
                "database_type": {
                    "type": "string",
                    "enum": ["postgresql", "mysql", "mssql", "oracle"],
                    "description": "Database type"
                },
                "connection_string": {
                    "type": "string",
                    "description": "Database connection string",
                    "secret": True,
                    "placeholder": "postgresql://user:pass@host:5432/db"
                },
                "query_template": {
                    "type": "string",
                    "description": "SQL query template for fetching data"
                },
                "poll_interval": {
                    "type": "integer",
                    "default": 60,
                    "description": "Polling interval in seconds"
                }
            }
        }
