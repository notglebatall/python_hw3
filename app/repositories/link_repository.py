from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.link import Link


class LinkRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_short_code(self, short_code: str) -> Link | None:
        result = await self.db.execute(select(Link).where(Link.short_code == short_code))
        return result.scalar_one_or_none()

    async def get_by_original_url(self, original_url: str) -> Link | None:
        result = await self.db.execute(
            select(Link).where(Link.original_url == original_url).order_by(Link.created_at.desc())
        )
        return result.scalars().first()

    async def create(
        self,
        short_code: str,
        original_url: str,
        owner_id: int | None,
        expires_at: datetime | None,
    ) -> Link:
        link = Link(
            short_code=short_code,
            original_url=original_url,
            owner_id=owner_id,
            expires_at=expires_at,
        )
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def update_original_url(self, short_code: str, original_url: str) -> Link | None:
        await self.db.execute(
            update(Link)
            .where(Link.short_code == short_code)
            .values(original_url=original_url)
        )
        await self.db.commit()
        return await self.get_by_short_code(short_code)

    async def delete_by_short_code(self, short_code: str) -> bool:
        result = await self.db.execute(delete(Link).where(Link.short_code == short_code))
        await self.db.commit()
        return result.rowcount > 0

    async def increment_clicks(self, short_code: str) -> None:
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(Link)
            .where(Link.short_code == short_code)
            .values(click_count=Link.click_count + 1, last_accessed_at=now)
        )
        await self.db.commit()

    async def delete_expired(self) -> int:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(delete(Link).where(Link.expires_at.is_not(None), Link.expires_at < now))
        await self.db.commit()
        return result.rowcount

    async def delete_unused(self, unused_days: int) -> int:
        threshold = datetime.now(timezone.utc) - timedelta(days=unused_days)
        result = await self.db.execute(
            delete(Link).where(
                or_(
                    and_(Link.last_accessed_at.is_(None), Link.created_at < threshold),
                    Link.last_accessed_at < threshold,
                ),
            )
        )
        await self.db.commit()
        return result.rowcount
