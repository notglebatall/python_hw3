from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_user
from app.db.session import get_db_session
from app.schemas.link import (
    LinkCreateRequest,
    LinkCreateResponse,
    LinkInfoResponse,
    LinkSearchResponse,
    LinkStatsResponse,
    LinkUpdateRequest,
)
from app.services.link_service import LinkService


router = APIRouter(prefix="/links", tags=["links"])


@router.post("/shorten", response_model=LinkCreateResponse)
async def create_short_link(
    payload: LinkCreateRequest,
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    service = LinkService(db)
    link = await service.create_link(
        original_url=str(payload.original_url),
        owner_id=user.id if user else None,
        custom_alias=payload.custom_alias,
        expires_at=payload.expires_at,
    )
    short_url = str(request.base_url).rstrip("/") + f"/{link.short_code}"
    return LinkCreateResponse(
        short_code=link.short_code,
        short_url=short_url,
        original_url=link.original_url,
        expires_at=link.expires_at,
    )


@router.get("/search", response_model=LinkSearchResponse)
async def search_link(
    original_url: str = Query(...),
    db: AsyncSession = Depends(get_db_session),
):
    service = LinkService(db)
    link = await service.find_by_original_url(original_url)
    return LinkSearchResponse(
        short_code=link.short_code,
        original_url=link.original_url,
        created_at=link.created_at,
        expires_at=link.expires_at,
    )


@router.get("/{short_code}")
async def redirect_by_code(short_code: str, db: AsyncSession = Depends(get_db_session)):
    service = LinkService(db)
    url = await service.resolve_and_track(short_code)
    return RedirectResponse(url=url, status_code=307)


@router.get("/{short_code}/info", response_model=LinkInfoResponse)
async def get_link_info(short_code: str, db: AsyncSession = Depends(get_db_session)):
    service = LinkService(db)
    link = await service.get_info(short_code)
    return LinkInfoResponse.model_validate(link)


@router.put("/{short_code}", response_model=LinkInfoResponse)
async def update_link(
    short_code: str,
    payload: LinkUpdateRequest,
    user=Depends(require_user),
    db: AsyncSession = Depends(get_db_session),
):
    service = LinkService(db)
    updated = await service.update_link(short_code=short_code, original_url=str(payload.original_url), requester_id=user.id)
    return LinkInfoResponse.model_validate(updated)


@router.delete("/{short_code}")
async def delete_link(
    short_code: str,
    user=Depends(require_user),
    db: AsyncSession = Depends(get_db_session),
):
    service = LinkService(db)
    await service.delete_link(short_code=short_code, requester_id=user.id)
    return {"status": "deleted"}


@router.get("/{short_code}/stats", response_model=LinkStatsResponse)
async def link_stats(short_code: str, db: AsyncSession = Depends(get_db_session)):
    service = LinkService(db)
    stats = await service.get_stats(short_code)
    return LinkStatsResponse(**stats)
