from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    ENVIRONMENT: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    DATABASE_URL: str = "sqlite:///./uav_qaoa_sar.db"

    DEFAULT_K_COVERAGE: int = 2
    DEFAULT_QAOA_REPS: int = 2
    MAX_WAYPOINTS: int = 24
    QAOA_SHOTS: int = 2048
    AER_SIMULATOR_METHOD: str = "statevector"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

