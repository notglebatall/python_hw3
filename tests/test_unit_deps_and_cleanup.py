from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.deps import get_current_user, require_user
from app.tasks.cleanup import cleanup_expired_and_unused_links


@pytest.mark.asyncio
async def test_get_current_user_handles_missing_and_invalid_tokens(mocker):
    assert await get_current_user(token=None, db=object()) is None

    mocker.patch("app.api.deps.decode_access_token", return_value=None)
    with pytest.raises(HTTPException) as invalid_exc:
        await get_current_user(token="broken", db=object())
    assert invalid_exc.value.status_code == 401

    mocker.patch("app.api.deps.decode_access_token", return_value="not-an-int")
    with pytest.raises(HTTPException) as parse_exc:
        await get_current_user(token="weird", db=object())
    assert parse_exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_returns_user_and_require_user_enforces_auth(mocker):
    repo = mocker.Mock()
    repo.get_by_id = mocker.AsyncMock(return_value=SimpleNamespace(id=1, email="user@example.com"))
    mocker.patch("app.api.deps.decode_access_token", return_value="1")
    mocker.patch("app.api.deps.UserRepository", return_value=repo)

    user = await get_current_user(token="valid", db=object())

    assert user.id == 1
    assert await require_user(user=user) == user

    with pytest.raises(HTTPException) as exc:
        await require_user(user=None)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_cleanup_uses_repository_and_settings_days(mocker):
    repo = mocker.Mock()
    repo.delete_expired = mocker.AsyncMock(return_value=2)
    repo.delete_unused = mocker.AsyncMock(return_value=5)
    mocker.patch("app.tasks.cleanup.LinkRepository", return_value=repo)

    expired_deleted, unused_deleted = await cleanup_expired_and_unused_links(object())

    assert (expired_deleted, unused_deleted) == (2, 5)
    repo.delete_unused.assert_awaited_once()
