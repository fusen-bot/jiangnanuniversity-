from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="JFP_", extra="ignore")

    app_name: str = "期刊财务智能运营平台"
    environment: str = "development"
    secret_key: str = Field(default="development-only-secret-change-me", min_length=32)
    database_url: str = "sqlite:///./journal_finance.db"
    redis_url: str = "redis://localhost:6379/0"
    allowed_origins: str = "http://localhost:5173,http://localhost:8080"
    storage_dir: Path = Path("storage")
    max_upload_mb: int = Field(default=20, ge=1, le=100)
    access_token_minutes: int = Field(default=30, ge=5, le=1440)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    use_fake_ai: bool = False
    journal_base_url: str = "https://journal.example.invalid"

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
