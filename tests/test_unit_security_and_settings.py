import os
import warnings

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.core.settings import Settings


def test_hash_password_roundtrip_and_invalid_format():
    password_hash = hash_password("super-secret")

    assert verify_password("super-secret", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False
    assert verify_password("super-secret", "broken-hash") is False


def test_access_token_roundtrip():
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"datetime\.datetime\.utcnow\(\) is deprecated and scheduled for removal in a future version.*",
            category=DeprecationWarning,
        )
        token = create_access_token("42")
        decoded = decode_access_token(token)

    assert decoded == "42"
    assert decode_access_token("not-a-token") is None


def test_settings_normalize_urls(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("RENDER_SERVICE_ID", raising=False)

    settings = Settings(
        database_url=' "postgresql://user:pass@db.example.com:5432/app" ',
        redis_url=" 'redis://redis.example.com:6379/0' ",
    )

    assert settings.database_url == "postgresql+asyncpg://user:pass@db.example.com:5432/app"
    assert settings.redis_url == "redis://redis.example.com:6379/0"


def test_settings_reject_local_render_hosts(monkeypatch):
    monkeypatch.setenv("RENDER", "true")

    try:
        Settings(
            database_url="postgresql://user:pass@localhost:5432/app",
            redis_url="redis://redis.internal:6379/0",
        )
    except ValueError as exc:
        assert "Invalid DATABASE_URL host" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid Render database host")

    monkeypatch.setenv("RENDER_SERVICE_ID", "svc-1")
    monkeypatch.setenv("RENDER", "false")

    try:
        Settings(
            database_url="postgresql://user:pass@db.example.com:5432/app",
            redis_url="redis://localhost:6379/0",
        )
    except ValueError as exc:
        assert "Invalid REDIS_URL host" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid Render redis host")

    for key in ("RENDER", "RENDER_SERVICE_ID"):
        os.environ.pop(key, None)
