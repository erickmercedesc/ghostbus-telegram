from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "telegram-engine"
    database_url: str = "sqlite+aiosqlite:///./data/telegram_engine.db"
    telegram_api_id: int = 0
    telegram_api_hash: str = ""
    session_store_path: Path = Path("./data/sessions")
    session_encryption_key: str = ""
    internal_api_key: str = Field(min_length=1, default="dev-internal-key")


def get_settings() -> Settings:
    return Settings()
