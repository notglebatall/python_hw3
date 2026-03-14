from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.link_service import LinkService


@pytest.mark.asyncio
async def test_create_link_rejects_past_expiration():
    service = LinkService(object())

    with pytest.raises(HTTPException) as exc:
        await service.create_link(
            original_url="https://example.com",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_link_rejects_taken_custom_alias(mocker):
    service = LinkService(object())
    service.links = mocker.Mock()
    service.cache = mocker.Mock()
    service.links.get_by_short_code = mocker.AsyncMock(return_value=object())

    with pytest.raises(HTTPException) as exc:
        await service.create_link(
            original_url="https://example.com",
            custom_alias="custom",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_link_generates_unique_short_code_after_collision(mocker):
    service = LinkService(object())
    service.links = mocker.Mock()
    service.cache = mocker.Mock()
    service.links.get_by_short_code = mocker.AsyncMock(side_effect=[object(), None])
    service.links.create = mocker.AsyncMock(
        return_value=SimpleNamespace(short_code="fresh77", original_url="https://example.com", expires_at=None)
    )
    service.cache.set_redirect_url = mocker.AsyncMock()
    mocker.patch("app.services.link_service.generate_short_code", side_effect=["taken77", "fresh77"])

    link = await service.create_link(original_url="https://example.com")

    assert link.short_code == "fresh77"
    assert service.links.get_by_short_code.await_count == 2
    service.cache.set_redirect_url.assert_awaited_once_with("fresh77", "https://example.com")


@pytest.mark.asyncio
async def test_generate_unique_short_code_raises_after_too_many_collisions(mocker):
    service = LinkService(object())
    service.links = mocker.Mock()
    service.links.get_by_short_code = mocker.AsyncMock(return_value=object())
    mocker.patch("app.services.link_service.generate_short_code", return_value="repeat77")

    with pytest.raises(HTTPException) as exc:
        await service._generate_unique_short_code()

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_resolve_and_track_prefers_cache(mocker):
    service = LinkService(object())
    service.links = mocker.Mock()
    service.cache = mocker.Mock()
    service.cache.get_redirect_url = mocker.AsyncMock(return_value="https://cached.example.com")
    service.links.increment_clicks = mocker.AsyncMock()
    service.cache.invalidate_stats = mocker.AsyncMock()

    result = await service.resolve_and_track("cache77")

    assert result == "https://cached.example.com"
    service.links.increment_clicks.assert_awaited_once_with("cache77")
    service.cache.invalidate_stats.assert_awaited_once_with("cache77")


@pytest.mark.asyncio
async def test_resolve_and_track_removes_expired_links(mocker):
    service = LinkService(object())
    service.links = mocker.Mock()
    service.cache = mocker.Mock()
    expired_link = SimpleNamespace(
        original_url="https://example.com",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    service.cache.get_redirect_url = mocker.AsyncMock(return_value=None)
    service.links.get_by_short_code = mocker.AsyncMock(return_value=expired_link)
    service.links.delete_by_short_code = mocker.AsyncMock()
    service.cache.invalidate_link = mocker.AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await service.resolve_and_track("dead77")

    assert exc.value.status_code == 404
    service.links.delete_by_short_code.assert_awaited_once_with("dead77")
    service.cache.invalidate_link.assert_awaited_once_with("dead77")


@pytest.mark.asyncio
async def test_update_and_delete_require_owner(mocker):
    service = LinkService(object())
    service.links = mocker.Mock()
    service.cache = mocker.Mock()
    link = SimpleNamespace(owner_id=10)
    service.links.get_by_short_code = mocker.AsyncMock(return_value=link)

    with pytest.raises(HTTPException) as update_exc:
        await service.update_link("abc123", "https://example.org", requester_id=99)

    with pytest.raises(HTTPException) as delete_exc:
        await service.delete_link("abc123", requester_id=99)

    assert update_exc.value.status_code == 403
    assert delete_exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_stats_uses_cache_and_populates_when_missing(mocker):
    service = LinkService(object())
    service.links = mocker.Mock()
    service.cache = mocker.Mock()
    cached_payload = {"short_code": "abc123", "click_count": 2}
    service.cache.get_stats = mocker.AsyncMock(side_effect=[cached_payload, None])
    service.cache.set_stats = mocker.AsyncMock()
    service.links.get_by_short_code = mocker.AsyncMock(
        return_value=SimpleNamespace(
            short_code="abc123",
            original_url="https://example.com",
            created_at=datetime.now(timezone.utc),
            click_count=7,
            last_accessed_at=None,
            expires_at=None,
        )
    )

    assert await service.get_stats("abc123") == cached_payload

    payload = await service.get_stats("abc123")

    assert payload["click_count"] == 7
    service.cache.set_stats.assert_awaited_once()


@pytest.mark.asyncio
async def test_find_by_original_url_raises_when_missing(mocker):
    service = LinkService(object())
    service.links = mocker.Mock()
    service.links.get_by_original_url = mocker.AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await service.find_by_original_url("https://missing.example.com")

    assert exc.value.status_code == 404
