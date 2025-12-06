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
    
    def fetch_timeseries(self, tag: str, from_time, to_time, limit: int = 100) -> List[Dict[str, Any]]:
        """Generate synthetic time-series data for demo purposes"""
        import math
        from datetime import timedelta
        
        if from_time is None:
            from_time = datetime.utcnow() - timedelta(hours=1)
        if to_time is None:
            to_time = datetime.utcnow()
        
        total_seconds = (to_time - from_time).total_seconds()
        if total_seconds <= 0:
            total_seconds = 3600
        
        num_points = min(limit, max(10, int(total_seconds / 60)))
        interval = total_seconds / num_points
        
        _, unit = self._generate_value(tag)
        
        base_value, _ = self._generate_value(tag)
        
        points = []
        for i in range(num_points):
            ts = from_time + timedelta(seconds=i * interval)
            
            sine_component = math.sin(2 * math.pi * i / num_points) * (base_value * 0.1)
            noise = random.uniform(-0.05, 0.05) * base_value
            value = base_value + sine_component + noise
            
            if "temperature" in tag.lower():
                value = round(60 + 20 * math.sin(2 * math.pi * i / num_points) + random.uniform(-2, 2), 2)
            elif "vibration" in tag.lower():
                value = round(2.5 + 1.5 * math.sin(2 * math.pi * i / num_points) + random.uniform(-0.3, 0.3), 3)
            elif "pressure" in tag.lower():
                value = round(50 + 10 * math.sin(2 * math.pi * i / num_points) + random.uniform(-1, 1), 2)
            elif "flow" in tag.lower():
                value = round(250 + 50 * math.sin(2 * math.pi * i / num_points) + random.uniform(-5, 5), 2)
            elif "level" in tag.lower():
                value = round(60 + 15 * math.sin(2 * math.pi * i / num_points) + random.uniform(-2, 2), 1)
            elif "current" in tag.lower():
                value = round(120 + 20 * math.sin(2 * math.pi * i / num_points) + random.uniform(-3, 3), 2)
            elif "speed" in tag.lower() or "rpm" in tag.lower():
                value = round(2800 + 200 * math.sin(2 * math.pi * i / num_points) + random.uniform(-20, 20), 0)
            elif "power" in tag.lower():
                value = round(1200 + 300 * math.sin(2 * math.pi * i / num_points) + random.uniform(-20, 20), 2)
            else:
                value = round(base_value + sine_component + noise, 2)
            
            points.append({
                "timestamp": ts.isoformat() + "Z",
                "value": value,
                "unit": unit,
                "quality": "good"
            })
        
        return points
    
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
