import os
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Link Shortener"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/shortener"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    default_short_code_length: int = 7
    unused_link_ttl_days: int = 30

    cache_redirect_ttl_seconds: int = 3600
    cache_stats_ttl_seconds: int = 300

    model_config = SettingsConfigDict(extra="ignore")

    @staticmethod
    def _strip_quotes_and_spaces(value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
            cleaned = cleaned[1:-1].strip()
        return cleaned

    @model_validator(mode="after")
    def normalize_urls(self):
        self.database_url = self._strip_quotes_and_spaces(self.database_url)
        self.redis_url = self._strip_quotes_and_spaces(self.redis_url)

        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif self.database_url.startswith("postgresql://") and "+asyncpg" not in self.database_url:
            self.database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        if os.getenv("RENDER") == "true" or os.getenv("RENDER_SERVICE_ID"):
            db_host = urlparse(self.database_url).hostname
            redis_host = urlparse(self.redis_url).hostname
            bad_db_hosts = {"postgres", "localhost", "127.0.0.1"}
            bad_redis_hosts = {"redis", "localhost", "127.0.0.1"}

            if db_host in bad_db_hosts:
                raise ValueError(
                    f"Invalid DATABASE_URL host '{db_host}' for Render. "
                    "Use Internal Database URL from Render PostgreSQL service."
                )
            if redis_host in bad_redis_hosts:
                raise ValueError(
                    f"Invalid REDIS_URL host '{redis_host}' for Render. "
                    "Use Internal Redis URL from Render Redis service."
                )
        return self


settings = Settings()
