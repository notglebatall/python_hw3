import pytest
from fastapi import HTTPException

from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_register_creates_user_with_hashed_password(mocker):
    db = object()
    service = AuthService(db)
    repo = mocker.Mock()
    repo.get_by_email = mocker.AsyncMock(return_value=None)
    repo.create = mocker.AsyncMock(return_value={"id": 1})
    service.users = repo

    result = await service.register("user@example.com", "plain-password")

    assert result == {"id": 1}
    create_kwargs = repo.create.await_args.kwargs
    assert create_kwargs["email"] == "user@example.com"
    assert create_kwargs["password_hash"] != "plain-password"


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(mocker):
    service = AuthService(object())
    repo = mocker.Mock()
    repo.get_by_email = mocker.AsyncMock(return_value=object())
    service.users = repo

    with pytest.raises(HTTPException) as exc:
        await service.register("user@example.com", "plain-password")

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_login_returns_token_and_rejects_invalid_credentials(mocker):
    service = AuthService(object())
    password_hash = "pbkdf2_sha256$100000$c2FsdA==$2aLx1Uy1d9V6jL3A4Xn5q4f5jY0fSvQ5ZZxW9Dg6Y1Y="
    user = mocker.Mock(id=7, password_hash=password_hash)
    repo = mocker.Mock()
    repo.get_by_email = mocker.AsyncMock(side_effect=[user, None])
    service.users = repo
    mocker.patch("app.services.auth_service.verify_password", return_value=True)
    create_access_token = mocker.patch("app.services.auth_service.create_access_token", return_value="token-123")

    token = await service.login("user@example.com", "plain-password")

    assert token == "token-123"
    create_access_token.assert_called_once_with("7")

    with pytest.raises(HTTPException) as exc:
        await service.login("missing@example.com", "plain-password")

    assert exc.value.status_code == 401
