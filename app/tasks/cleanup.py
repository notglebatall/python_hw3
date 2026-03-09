from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.repositories.link_repository import LinkRepository


async def cleanup_expired_and_unused_links(db: AsyncSession) -> tuple[int, int]:
    repo = LinkRepository(db)
    expired_deleted = await repo.delete_expired()
    unused_deleted = await repo.delete_unused(settings.unused_link_ttl_days)
    return expired_deleted, unused_deleted
