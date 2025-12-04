import random
from datetime import datetime
from typing import Dict, List, Any
from core.connectors.base import BaseConnector, ConnectorStatus, MetricReading

class DemoConnector(BaseConnector):
    
    @property
    def connector_type(self) -> str:
        return "demo"
    
    def test_connection(self) -> bool:
        self.status = ConnectorStatus.CONNECTED
        self.last_connection_time = datetime.utcnow()
        return True
    
    def connect(self) -> bool:
        self.status = ConnectorStatus.CONNECTED
        self.last_connection_time = datetime.utcnow()
        return True
    
    def disconnect(self) -> bool:
        self.status = ConnectorStatus.DISCONNECTED
        return True
    
    def read_tags(self, tags: List[str]) -> List[MetricReading]:
        readings = []
        for tag in tags:
            value, unit = self._generate_value(tag)
            readings.append(MetricReading(
                tag=tag,
                value=value,
                unit=unit,
                quality="good",
                timestamp=datetime.utcnow(),
                source="demo"
            ))
        return readings
    
    def _generate_value(self, tag: str) -> tuple:
        tag_lower = tag.lower()
        
        if "temperature" in tag_lower or "temp" in tag_lower:
            return round(60 + random.uniform(-10, 30), 2), "°C"
        elif "vibration" in tag_lower or "vib" in tag_lower:
            return round(random.uniform(0.5, 8), 3), "mm/s"
        elif "pressure" in tag_lower:
            return round(random.uniform(20, 120), 2), "bar"
        elif "flow" in tag_lower:
            return round(random.uniform(100, 500), 2), "m³/h"
        elif "power" in tag_lower:
            return round(random.uniform(500, 2000), 2), "kW"
        elif "speed" in tag_lower or "rpm" in tag_lower:
            return round(random.uniform(1000, 3600), 0), "RPM"
        elif "level" in tag_lower:
            return round(random.uniform(20, 95), 1), "%"
        elif "current" in tag_lower:
            return round(random.uniform(50, 200), 2), "A"
        elif "voltage" in tag_lower:
            return round(random.uniform(380, 420), 1), "V"
        else:
            return round(random.uniform(0, 100), 2), "unit"
    
    def get_available_tags(self) -> List[str]:
        return [
            "PUMP_001_TEMPERATURE",
            "PUMP_001_VIBRATION",
            "PUMP_001_PRESSURE_IN",
            "PUMP_001_PRESSURE_OUT",
            "PUMP_001_FLOW",
            "PUMP_001_POWER",
            "PUMP_001_SPEED",
            "COMPRESSOR_001_TEMPERATURE",
            "COMPRESSOR_001_VIBRATION",
            "COMPRESSOR_001_PRESSURE",
            "TURBINE_001_TEMPERATURE",
            "TURBINE_001_VIBRATION",
            "TURBINE_001_SPEED",
            "TURBINE_001_POWER",
            "TANK_001_LEVEL",
            "TANK_001_TEMPERATURE",
            "MOTOR_001_CURRENT",
            "MOTOR_001_VOLTAGE",
            "MOTOR_001_TEMPERATURE"
        ]
    
    @staticmethod
    def get_config_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "refresh_interval": {
                    "type": "integer",
                    "description": "Data refresh interval in seconds",
                    "default": 60
                },
                "noise_level": {
                    "type": "number",
                    "description": "Random noise level (0-1)",
                    "default": 0.1
                }
            }
        }
