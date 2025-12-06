from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

class ConnectorStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"

@dataclass
class MetricReading:
    tag: str
    value: float
    unit: str
    quality: str
    timestamp: datetime
    source: str

class BaseConnector(ABC):
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.status = ConnectorStatus.UNKNOWN
        self.last_error: Optional[str] = None
        self.last_connection_time: Optional[datetime] = None
    
    @property
    @abstractmethod
    def connector_type(self) -> str:
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        pass
    
    @abstractmethod
    def connect(self) -> bool:
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        pass
    
    @abstractmethod
    def read_tags(self, tags: List[str]) -> List[MetricReading]:
        pass
    
    @abstractmethod
    def get_available_tags(self) -> List[str]:
        pass
    
    def fetch_timeseries(self, tag: str, from_time: datetime, to_time: datetime, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch time-series data for a tag between from_time and to_time.
        Returns list of dicts: [{"timestamp": "...", "value": ..., "unit": "..."}]
        Default implementation returns empty list - override in subclasses.
        """
        return []
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "type": self.connector_type,
            "status": self.status.value,
            "last_error": self.last_error,
            "last_connection_time": self.last_connection_time.isoformat() if self.last_connection_time else None
        }
    
    @staticmethod
    def get_config_schema() -> Dict[str, Any]:
        return {}
