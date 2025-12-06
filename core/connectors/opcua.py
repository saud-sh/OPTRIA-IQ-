import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from core.connectors.base import BaseConnector, ConnectorStatus, MetricReading
from config import settings

class OPCUAConnector(BaseConnector):
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.endpoint = config.get("endpoint", "") or config.get("endpoint_url", "") or settings.opcua_endpoint_url
        self.namespace = config.get("namespace", "")
        self.username = config.get("username", "") or settings.opcua_username
        self.password = config.get("password", "") or settings.opcua_password
        self._client = None
    
    @property
    def connector_type(self) -> str:
        return "opcua"
    
    def test_connection(self) -> bool:
        if not self.endpoint:
            self.status = ConnectorStatus.ERROR
            self.last_error = "No endpoint configured"
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
        self._client = None
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
                source="opcua"
            ))
        return readings
    
    def get_available_tags(self) -> List[str]:
        return [
            "ns=2;s=Channel1.Device1.Tag1",
            "ns=2;s=Channel1.Device1.Tag2",
            "ns=2;s=Channel1.Device1.Temperature",
            "ns=2;s=Channel1.Device1.Pressure",
            "ns=2;s=Channel1.Device1.Flow"
        ]
    
    @staticmethod
    def get_config_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["endpoint"],
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "OPC-UA server endpoint URL",
                    "placeholder": "opc.tcp://server:4840"
                },
                "namespace": {
                    "type": "string",
                    "description": "OPC-UA namespace"
                },
                "username": {
                    "type": "string",
                    "description": "Username for authentication"
                },
                "password": {
                    "type": "string",
                    "description": "Password for authentication",
                    "secret": True
                },
                "security_policy": {
                    "type": "string",
                    "enum": ["None", "Basic128Rsa15", "Basic256", "Basic256Sha256"],
                    "default": "None"
                }
            }
        }
