from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.schemas.link import PublicShortenRequest, PublicShortenResponse
from app.services.link_service import LinkService


router = APIRouter(tags=["public"])


@router.post("/shorten", response_model=PublicShortenResponse)
async def public_shorten(
    payload: PublicShortenRequest,
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    service = LinkService(db)
    link = await service.create_link(
        original_url=str(payload.original_url),
        owner_id=user.id if user else None,
    )
    short_url = str(request.base_url).rstrip("/") + f"/{link.short_code}"
    return PublicShortenResponse(
        original_url=link.original_url,
        short_url=short_url,
        short_code=link.short_code,
    )


@router.get("/{short_code}")
async def redirect_short_root(short_code: str, db: AsyncSession = Depends(get_db_session)):
    service = LinkService(db)
    url = await service.resolve_and_track(short_code)
    return RedirectResponse(url=url, status_code=307)
