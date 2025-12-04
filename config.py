import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # REQUIRED SECRETS - fail fast if missing
    database_url: str = os.getenv("DATABASE_URL", "")
    session_secret: str = os.getenv("SESSION_SECRET", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Database credentials
    pg_host: str = os.getenv("PGHOST", "localhost")
    pg_port: str = os.getenv("PGPORT", "5432")
    pg_user: str = os.getenv("PGUSER", "postgres")
    pg_password: str = os.getenv("PGPASSWORD", "")
    pg_database: str = os.getenv("PGDATABASE", "optria")
    
    # Feature flags
    demo_mode: bool = os.getenv("DEMO_MODE", "true").lower() == "true"
    app_env: str = os.getenv("APP_ENV", "development")
    optimization_engine_enabled: bool = os.getenv("OPTIMIZATION_ENGINE_ENABLED", "true").lower() == "true"
    external_db_enable: bool = os.getenv("EXTERNAL_DB_ENABLE", "true").lower() == "true"
    
    # Integration defaults (fallback values)
    pi_base_url: str = os.getenv("PI_BASE_URL", "")
    sap_base_url: str = os.getenv("SAP_BASE_URL", "")
    opcua_username: str = os.getenv("OPCUA_USERNAME", "")
    opcua_password: str = os.getenv("OPCUA_PASSWORD", "")
    
    # App settings
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    app_name: str = "OPTRIA IQ"
    app_version: str = "1.0.0"
    debug: bool = app_env == "development"
    
    class Config:
        env_file = ".env"
        extra = "allow"
    
    def validate_required_secrets(self):
        """Validate that all required secrets are present"""
        missing = []
        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.session_secret:
            missing.append("SESSION_SECRET")
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

@lru_cache()
def get_settings() -> Settings:
    settings_instance = Settings()
    settings_instance.validate_required_secrets()
    return settings_instance

settings = get_settings()
