import json

import pytest

from app.services.cache_service import CacheService
from app.utils import code_generator


def test_generate_short_code_uses_requested_length_and_alphabet(mocker):
    sequence = list("AbC123x")
    mocked_choice = mocker.patch("app.utils.code_generator.secrets.choice", side_effect=sequence)

    result = code_generator.generate_short_code(7)

    assert result == "AbC123x"
    assert mocked_choice.call_count == 7
    assert set(result) <= set(code_generator.ALPHABET)


@pytest.mark.asyncio
async def test_cache_service_stores_redirect_and_stats(fake_redis):
    service = CacheService()

    await service.set_redirect_url("abc123", "https://example.com")
    await service.set_stats("abc123", {"click_count": 3, "created_at": "2026-01-01T00:00:00+00:00"})

    assert await service.get_redirect_url("abc123") == "https://example.com"
    assert await service.get_stats("abc123") == {
        "click_count": 3,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    assert json.loads(fake_redis.storage["stats:abc123"])["click_count"] == 3


@pytest.mark.asyncio
async def test_cache_service_invalidation(fake_redis):
    service = CacheService()
    await service.set_redirect_url("to-delete", "https://example.com")
    await service.set_stats("to-delete", {"click_count": 1})

    await service.invalidate_stats("to-delete")
    assert await service.get_stats("to-delete") is None
    assert await service.get_redirect_url("to-delete") == "https://example.com"

    await service.invalidate_link("to-delete")
    assert await service.get_redirect_url("to-delete") is None
