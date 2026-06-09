from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GROQ_API_KEY: str = ""
    ENV: Literal["dev", "staging", "prod"] = "dev"
    APP_VERSION: str = "0.0.0"
    SECRET_KEY: str = "change-me-in-production"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/churchfinder"

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    NOTIFY_METHOD: Literal["email", "webhook", "both", "none"] = "none"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    NOTIFY_EMAIL_TO: str = ""
    WEBHOOK_URL: str = ""

    CRAWL_INTERVAL_HOURS: int = 3
    REQUEST_DELAY_SECONDS: int = 3
    KEYWORDS: list[str] = [
        "church", "chapel", "former church",
        "ecclesiastical", "vestry", "nave",
    ]

    DOCKER_IMAGE: str = "church-finder-backend"
    GITHUB_REPO: str = ""
    GITHUB_TOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @property
    def is_production(self) -> bool:
        return self.ENV == "prod"

    @property
    def is_development(self) -> bool:
        return self.ENV == "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()