from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    PROJECT_NAME: str = "Disaster Management System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Security
    SECRET_KEY: str = "dev_secret_key_change_in_production_1234567890abcdef"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/disaster_mgmt"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5433/disaster_mgmt"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Spatial configuration (WGS84)
    DEFAULT_SRID: int = 4326

    # Replay configuration
    REPLAY_SPEED_MULTIPLIER: float = 1.0

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]


settings = Settings()
