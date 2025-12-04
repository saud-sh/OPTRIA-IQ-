from typing import Dict, Type, Any
from core.connectors.base import BaseConnector, ConnectorStatus
from core.connectors.demo import DemoConnector
from core.connectors.opcua import OPCUAConnector
from core.connectors.pi import PIConnector
from core.connectors.sap import SAPConnector
from core.connectors.sql import SQLConnector

CONNECTOR_TYPES: Dict[str, Type[BaseConnector]] = {
    "demo": DemoConnector,
    "opcua": OPCUAConnector,
    "pi": PIConnector,
    "sap": SAPConnector,
    "sql": SQLConnector
}

CONNECTOR_SCHEMAS = {
    "demo": {
        "name": "Demo Connector",
        "description": "Simulated data for testing and demos",
        "fields": [
            {"name": "data_frequency_seconds", "type": "number", "label": "Data Frequency (seconds)", "default": 60, "required": False},
            {"name": "num_tags", "type": "number", "label": "Number of Tags", "default": 50, "required": False},
            {"name": "anomaly_probability", "type": "number", "label": "Anomaly Probability (0-1)", "default": 0.05, "required": False}
        ]
    },
    "opcua": {
        "name": "OPC-UA Connector",
        "description": "Connect to OPC-UA servers for industrial data",
        "fields": [
            {"name": "endpoint_url", "type": "text", "label": "Endpoint URL", "placeholder": "opc.tcp://server:4840", "required": True},
            {"name": "security_mode", "type": "select", "label": "Security Mode", "options": ["None", "Sign", "SignAndEncrypt"], "default": "None", "required": True},
            {"name": "security_policy", "type": "select", "label": "Security Policy", "options": ["None", "Basic128Rsa15", "Basic256", "Basic256Sha256", "Aes128_Sha256_RsaOaep", "Aes256_Sha256_RsaPss"], "default": "None", "required": False},
            {"name": "auth_type", "type": "select", "label": "Authentication Type", "options": ["Anonymous", "UsernamePassword", "Certificate"], "default": "Anonymous", "required": True},
            {"name": "username", "type": "text", "label": "Username", "required": False, "show_when": {"auth_type": "UsernamePassword"}},
            {"name": "password", "type": "password", "label": "Password", "required": False, "show_when": {"auth_type": "UsernamePassword"}},
            {"name": "certificate", "type": "textarea", "label": "Certificate (PEM)", "required": False, "show_when": {"auth_type": "Certificate"}},
            {"name": "private_key", "type": "textarea", "label": "Private Key (PEM)", "required": False, "show_when": {"auth_type": "Certificate"}},
            {"name": "namespace_filter", "type": "text", "label": "Namespace Filter", "placeholder": "ns=2;s=", "required": False},
            {"name": "tag_prefix", "type": "text", "label": "Tag Prefix Filter", "required": False},
            {"name": "sampling_interval_ms", "type": "number", "label": "Sampling Interval (ms)", "default": 1000, "required": False},
            {"name": "max_tags_per_scan", "type": "number", "label": "Max Tags per Scan", "default": 500, "required": False},
            {"name": "time_zone", "type": "text", "label": "Time Zone", "default": "Asia/Riyadh", "required": False}
        ]
    },
    "pi": {
        "name": "PI System / PI WebAPI",
        "description": "Connect to OSIsoft PI System via Web API",
        "fields": [
            {"name": "pi_webapi_url", "type": "text", "label": "PI Web API URL", "placeholder": "https://piserver/piwebapi", "required": True},
            {"name": "auth_type", "type": "select", "label": "Authentication Type", "options": ["Basic", "Token", "Kerberos"], "default": "Basic", "required": True},
            {"name": "username", "type": "text", "label": "Username", "required": False, "show_when": {"auth_type": ["Basic", "Kerberos"]}},
            {"name": "password", "type": "password", "label": "Password", "required": False, "show_when": {"auth_type": ["Basic", "Kerberos"]}},
            {"name": "token", "type": "password", "label": "API Token", "required": False, "show_when": {"auth_type": "Token"}},
            {"name": "af_database_path", "type": "text", "label": "AF Database Path", "placeholder": "\\\\Server\\Database", "required": False},
            {"name": "tag_filter", "type": "text", "label": "Tag Filter / Prefix", "required": False},
            {"name": "sync_mode", "type": "select", "label": "Sync Mode", "options": ["last_24h", "last_7d", "last_30d", "full"], "default": "last_24h", "required": True},
            {"name": "time_zone", "type": "text", "label": "Time Zone", "default": "Asia/Riyadh", "required": False}
        ]
    },
    "sql": {
        "name": "External Database",
        "description": "Connect to SQL Server, Oracle, PostgreSQL, or MySQL databases",
        "fields": [
            {"name": "db_type", "type": "select", "label": "Database Type", "options": ["postgres", "sqlserver", "oracle", "mysql"], "required": True},
            {"name": "host", "type": "text", "label": "Host", "placeholder": "db.example.com", "required": True},
            {"name": "port", "type": "number", "label": "Port", "default": 5432, "required": True},
            {"name": "database_name", "type": "text", "label": "Database Name", "required": True},
            {"name": "service_name", "type": "text", "label": "Service Name (Oracle)", "required": False, "show_when": {"db_type": "oracle"}},
            {"name": "schema", "type": "text", "label": "Schema", "default": "public", "required": False},
            {"name": "username", "type": "text", "label": "Username", "required": True},
            {"name": "password", "type": "password", "label": "Password", "required": True},
            {"name": "ssl_mode", "type": "select", "label": "SSL Mode", "options": ["disable", "require", "verify-ca", "verify-full"], "default": "require", "required": False},
            {"name": "data_mode", "type": "select", "label": "Data Mode", "options": ["raw_table", "custom_query"], "default": "raw_table", "required": True},
            {"name": "table_name", "type": "text", "label": "Table Name", "required": False, "show_when": {"data_mode": "raw_table"}},
            {"name": "timestamp_column", "type": "text", "label": "Timestamp Column", "required": False, "show_when": {"data_mode": "raw_table"}},
            {"name": "value_column", "type": "text", "label": "Value Column", "required": False, "show_when": {"data_mode": "raw_table"}},
            {"name": "tag_column", "type": "text", "label": "Tag Column", "required": False, "show_when": {"data_mode": "raw_table"}},
            {"name": "custom_query", "type": "textarea", "label": "Custom Query", "placeholder": "SELECT timestamp, tag, value FROM ...", "required": False, "show_when": {"data_mode": "custom_query"}}
        ]
    },
    "sap": {
        "name": "SAP PM / Oracle EAM",
        "description": "Connect to SAP Plant Maintenance or Oracle EAM systems",
        "fields": [
            {"name": "system_type", "type": "select", "label": "System Type", "options": ["sap_pm", "oracle_eam"], "default": "sap_pm", "required": True},
            {"name": "base_url", "type": "text", "label": "Base URL / API Endpoint", "placeholder": "https://sap-server/sap/opu/odata/", "required": True},
            {"name": "auth_type", "type": "select", "label": "Authentication Type", "options": ["Basic", "OAuth2"], "default": "Basic", "required": True},
            {"name": "username", "type": "text", "label": "Username", "required": False, "show_when": {"auth_type": "Basic"}},
            {"name": "password", "type": "password", "label": "Password", "required": False, "show_when": {"auth_type": "Basic"}},
            {"name": "client_id", "type": "text", "label": "Client ID", "required": False, "show_when": {"auth_type": "OAuth2"}},
            {"name": "client_secret", "type": "password", "label": "Client Secret", "required": False, "show_when": {"auth_type": "OAuth2"}},
            {"name": "token_url", "type": "text", "label": "Token URL", "required": False, "show_when": {"auth_type": "OAuth2"}},
            {"name": "plant_code", "type": "text", "label": "Plant Code", "required": False},
            {"name": "company_code", "type": "text", "label": "Company Code", "required": False},
            {"name": "work_order_sync_mode", "type": "select", "label": "Work Order Sync Mode", "options": ["pull_only", "push_and_sync"], "default": "pull_only", "required": True},
            {"name": "asset_mapping_mode", "type": "select", "label": "Asset Mapping Mode", "options": ["by_equipment_number", "by_functional_location"], "default": "by_equipment_number", "required": True}
        ]
    }
}

SSO_PROVIDER_SCHEMAS = {
    "azure_ad": {
        "name": "Azure Active Directory",
        "description": "Microsoft Azure AD / Entra ID SSO",
        "fields": [
            {"name": "display_name", "type": "text", "label": "Display Name", "default": "Sign in with Microsoft", "required": True},
            {"name": "client_id", "type": "text", "label": "Application (Client) ID", "required": True},
            {"name": "client_secret", "type": "password", "label": "Client Secret", "required": True},
            {"name": "tenant_id", "type": "text", "label": "Directory (Tenant) ID", "required": True},
            {"name": "scopes", "type": "text", "label": "Scopes", "default": "openid profile email", "required": False},
            {"name": "domain_hint", "type": "text", "label": "Domain Hint", "required": False}
        ]
    },
    "okta": {
        "name": "Okta",
        "description": "Okta Identity Provider SSO",
        "fields": [
            {"name": "display_name", "type": "text", "label": "Display Name", "default": "Sign in with Okta", "required": True},
            {"name": "client_id", "type": "text", "label": "Client ID", "required": True},
            {"name": "client_secret", "type": "password", "label": "Client Secret", "required": True},
            {"name": "issuer_url", "type": "text", "label": "Issuer URL", "placeholder": "https://your-domain.okta.com", "required": True},
            {"name": "scopes", "type": "text", "label": "Scopes", "default": "openid profile email", "required": False}
        ]
    },
    "google": {
        "name": "Google",
        "description": "Google Workspace SSO",
        "fields": [
            {"name": "display_name", "type": "text", "label": "Display Name", "default": "Sign in with Google", "required": True},
            {"name": "client_id", "type": "text", "label": "Client ID", "required": True},
            {"name": "client_secret", "type": "password", "label": "Client Secret", "required": True},
            {"name": "hosted_domain", "type": "text", "label": "Hosted Domain (restrict to)", "placeholder": "your-company.com", "required": False},
            {"name": "scopes", "type": "text", "label": "Scopes", "default": "openid profile email", "required": False}
        ]
    }
}

def get_connector(connector_type: str, config: dict) -> BaseConnector:
    connector_class = CONNECTOR_TYPES.get(connector_type)
    if not connector_class:
        raise ValueError(f"Unknown connector type: {connector_type}")
    return connector_class(config)

def get_connector_schema(connector_type: str) -> Dict[str, Any]:
    return CONNECTOR_SCHEMAS.get(connector_type, {})

def get_sso_provider_schema(provider_type: str) -> Dict[str, Any]:
    return SSO_PROVIDER_SCHEMAS.get(provider_type, {})

__all__ = [
    'BaseConnector', 'ConnectorStatus', 'DemoConnector', 
    'OPCUAConnector', 'PIConnector', 'SAPConnector', 'SQLConnector',
    'CONNECTOR_TYPES', 'CONNECTOR_SCHEMAS', 'SSO_PROVIDER_SCHEMAS',
    'get_connector', 'get_connector_schema', 'get_sso_provider_schema'
]
