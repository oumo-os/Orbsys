from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = "postgresql+asyncpg://orbsys_app:change_me@localhost:5432/orbsys"
    database_url_sync: str = "postgresql://orbsys_app:change_me@localhost:5432/orbsys"

    # Auth
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # NATS
    nats_url: str = "nats://localhost:4222"

    # LLM
    llm_backend: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"

    # S3
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "orbsys"
    s3_access_key: str = ""
    s3_secret_key: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
