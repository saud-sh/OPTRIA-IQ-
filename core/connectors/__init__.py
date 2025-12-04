from core.connectors.base import BaseConnector, ConnectorStatus
from core.connectors.demo import DemoConnector
from core.connectors.opcua import OPCUAConnector
from core.connectors.pi import PIConnector
from core.connectors.sap import SAPConnector
from core.connectors.sql import SQLConnector

CONNECTOR_TYPES = {
    "demo": DemoConnector,
    "opcua": OPCUAConnector,
    "pi": PIConnector,
    "sap": SAPConnector,
    "sql": SQLConnector
}

def get_connector(connector_type: str, config: dict) -> BaseConnector:
    connector_class = CONNECTOR_TYPES.get(connector_type)
    if not connector_class:
        raise ValueError(f"Unknown connector type: {connector_type}")
    return connector_class(config)

__all__ = [
    'BaseConnector', 'ConnectorStatus', 'DemoConnector', 
    'OPCUAConnector', 'PIConnector', 'SAPConnector', 'SQLConnector',
    'CONNECTOR_TYPES', 'get_connector'
]
