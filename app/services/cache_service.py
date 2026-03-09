import json

from app.core.redis_client import redis_client
from app.core.settings import settings


class CacheService:
    async def get_redirect_url(self, short_code: str) -> str | None:
        return await redis_client.get(f"redirect:{short_code}")

    async def set_redirect_url(self, short_code: str, original_url: str) -> None:
        await redis_client.setex(
            f"redirect:{short_code}", settings.cache_redirect_ttl_seconds, original_url
        )

    async def get_stats(self, short_code: str) -> dict | None:
        raw = await redis_client.get(f"stats:{short_code}")
        return json.loads(raw) if raw else None

    async def set_stats(self, short_code: str, payload: dict) -> None:
        await redis_client.setex(
            f"stats:{short_code}", settings.cache_stats_ttl_seconds, json.dumps(payload, default=str)
        )

    async def invalidate_link(self, short_code: str) -> None:
        await redis_client.delete(f"redirect:{short_code}", f"stats:{short_code}")

    async def invalidate_stats(self, short_code: str) -> None:
        await redis_client.delete(f"stats:{short_code}")
