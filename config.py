import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "")
    session_secret: str = os.getenv("SESSION_SECRET", "optria-iq-secret-key-change-in-production")
    demo_mode: bool = True
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    app_name: str = "OPTRIA IQ"
    app_version: str = "1.0.0"
    debug: bool = False
    
    class Config:
        env_file = ".env"
        extra = "allow"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
