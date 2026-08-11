from typing import Optional

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    ADMIN_PSWD: str
    DB_URL: str
    SECRET_KEY: str
    COOKIE_NAME: str = "pyrokube_session"
    COOKIE_SECURE: bool = False
    SESSION_TTL: int = 86400
    WILDCARD_DOMAIN: Optional[str] = "anubhav.fyi"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )


setting: Settings = Settings()
