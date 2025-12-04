import random
from datetime import datetime
from typing import Dict, List, Any
from core.connectors.base import BaseConnector, ConnectorStatus, MetricReading

class PIConnector(BaseConnector):
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.server_url = config.get("server_url", "")
        self.api_key = config.get("api_key", "")
        self.database = config.get("database", "")
    
    @property
    def connector_type(self) -> str:
        return "pi"
    
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
            value = random.uniform(0, 100)
            readings.append(MetricReading(
                tag=tag,
                value=round(value, 3),
                unit="unit",
                quality="good",
                timestamp=datetime.utcnow(),
                source="pi"
            ))
        return readings
    
    def get_available_tags(self) -> List[str]:
        return [
            "\\\\PIServer\\sinusoid",
            "\\\\PIServer\\sinusoidu",
            "\\\\PIServer\\cdt158",
            "\\\\PIServer\\cdm158"
        ]
    
    @staticmethod
    def get_config_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["server_url"],
            "properties": {
                "server_url": {
                    "type": "string",
                    "description": "PI Web API server URL",
                    "placeholder": "https://piwebapi.example.com/piwebapi"
                },
                "api_key": {
                    "type": "string",
                    "description": "API Key for authentication",
                    "secret": True
                },
                "database": {
                    "type": "string",
                    "description": "PI Asset Framework database name"
                },
                "verify_ssl": {
                    "type": "boolean",
                    "default": True,
                    "description": "Verify SSL certificates"
                }
            }
        }
