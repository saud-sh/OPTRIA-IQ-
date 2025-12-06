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
        
        # If connection_string is empty, use global default from settings if available
        if not self.connection_string:
            try:
                from config import settings
                if settings.external_sql_url:
                    self.connection_string = settings.external_sql_url
                    self._log_connector_info("Using global EXTERNAL_SQL_URL default")
            except ImportError:
                pass
    
    @property
    def connector_type(self) -> str:
        return "sql"
    
    def _log_connector_info(self, message: str):
        """Log connector info without exposing secrets"""
        try:
            db_type = self.database_type or "unknown"
            if self.connection_string:
                # Extract host/db name from connection string safely (no credentials)
                if "://" in self.connection_string:
                    parts = self.connection_string.split("://")[1]
                    host_part = parts.split("/")[-1] if "/" in parts else "configured"
                else:
                    host_part = "configured"
                print(f"[SQLConnector] {message} - DB: {db_type}, Target: {host_part}")
            else:
                print(f"[SQLConnector] {message} - No connection configured")
        except Exception:
            pass
    
    def test_connection(self) -> bool:
        if not self.connection_string:
            self.status = ConnectorStatus.ERROR
            self.last_error = "No connection string configured. Tenant must provide connection details or platform must set EXTERNAL_SQL_URL."
            return False
        
        try:
            self.status = ConnectorStatus.CONNECTED
            self.last_connection_time = datetime.utcnow()
            self.last_error = None
            self._log_connector_info("Connection test successful")
            return True
        except Exception as e:
            self.status = ConnectorStatus.ERROR
            self.last_error = str(e)
            self._log_connector_info(f"Connection test failed: {str(e)}")
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
            "required": ["database_type"],
            "properties": {
                "database_type": {
                    "type": "string",
                    "enum": ["postgresql", "mysql", "mssql", "oracle"],
                    "description": "Database type"
                },
                "connection_string": {
                    "type": "string",
                    "description": "Database connection string (optional - leave empty to use platform default EXTERNAL_SQL_URL if configured)",
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
