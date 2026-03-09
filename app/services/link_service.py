from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.repositories.link_repository import LinkRepository
from app.services.cache_service import CacheService
from app.utils.code_generator import generate_short_code


class LinkService:
    def __init__(self, db: AsyncSession):
        self.links = LinkRepository(db)
        self.cache = CacheService()

    async def create_link(
        self,
        original_url: str,
        owner_id: int | None = None,
        custom_alias: str | None = None,
        expires_at: datetime | None = None,
    ):
        if expires_at and expires_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="expires_at must be in the future",
            )

        short_code = custom_alias or await self._generate_unique_short_code()
        if custom_alias:
            exists = await self.links.get_by_short_code(custom_alias)
            if exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Alias already taken",
                )

        link = await self.links.create(
            short_code=short_code,
            original_url=original_url,
            owner_id=owner_id,
            expires_at=expires_at,
        )

        await self.cache.set_redirect_url(link.short_code, link.original_url)
        return link

    async def resolve_and_track(self, short_code: str) -> str:
        cached = await self.cache.get_redirect_url(short_code)
        if cached:
            await self.links.increment_clicks(short_code)
            await self.cache.invalidate_stats(short_code)
            return cached

        link = await self.links.get_by_short_code(short_code)
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

        if link.expires_at and link.expires_at <= datetime.now(timezone.utc):
            await self.links.delete_by_short_code(short_code)
            await self.cache.invalidate_link(short_code)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link expired")

        await self.links.increment_clicks(short_code)
        await self.cache.set_redirect_url(short_code, link.original_url)
        await self.cache.invalidate_stats(short_code)
        return link.original_url

    async def get_info(self, short_code: str):
        link = await self.links.get_by_short_code(short_code)
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
        return link

    async def update_link(self, short_code: str, original_url: str, requester_id: int):
        link = await self.links.get_by_short_code(short_code)
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
        if link.owner_id != requester_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        updated = await self.links.update_original_url(short_code, original_url)
        await self.cache.invalidate_link(short_code)
        return updated

    async def delete_link(self, short_code: str, requester_id: int):
        link = await self.links.get_by_short_code(short_code)
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
        if link.owner_id != requester_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        await self.links.delete_by_short_code(short_code)
        await self.cache.invalidate_link(short_code)

    async def get_stats(self, short_code: str) -> dict:
        cached = await self.cache.get_stats(short_code)
        if cached:
            return cached

        link = await self.links.get_by_short_code(short_code)
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

        payload = {
            "short_code": link.short_code,
            "original_url": link.original_url,
            "created_at": link.created_at,
            "click_count": link.click_count,
            "last_accessed_at": link.last_accessed_at,
            "expires_at": link.expires_at,
        }
        await self.cache.set_stats(short_code, payload)
        return payload

    async def find_by_original_url(self, original_url: str):
        link = await self.links.get_by_original_url(original_url)
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
        return link

    async def _generate_unique_short_code(self) -> str:
        for _ in range(10):
            candidate = generate_short_code(settings.default_short_code_length)
            exists = await self.links.get_by_short_code(candidate)
            if not exists:
                return candidate
        raise HTTPException(status_code=500, detail="Could not generate unique short code")
