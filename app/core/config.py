from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    app_name: str = "Algo Trading"
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = False

    database_url: str
    redis_url: str = "redis://localhost:5379/0"

    anthropic_api_key: SecretStr | None = None
    anthropic_sonnet_model: str | None = None
    anthropic_haiku_model: str | None = None

    exchange_id: str | None = None
    exchange_api_key: SecretStr | None = None
    exchange_secret: SecretStr | None = None

    telegram_bot_token: SecretStr | None = None
    telegram_chat_id: str | None = None

settings = Settings()