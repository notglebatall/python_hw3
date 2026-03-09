from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


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

    @model_validator(mode="after")
    def normalize_urls(self):
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif self.database_url.startswith("postgresql://") and "+asyncpg" not in self.database_url:
            self.database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self


settings = Settings()
