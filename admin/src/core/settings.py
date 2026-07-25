from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ADMIN_PSWD: str
    DB_URL: str  # i know could have been better
    COOKIE_NAME: str = "ADMIN_PSWD"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


setting: Settings = Settings()
