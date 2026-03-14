from datetime import datetime, timedelta, timezone

import pytest

from app.models.link import Link
from app.repositories.link_repository import LinkRepository
from app.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_user_repository_create_and_lookup(db_session):
    repo = UserRepository(db_session)

    user = await repo.create(email="repo-user@example.com", password_hash="hash-123")

    assert user.id is not None
    assert (await repo.get_by_email("repo-user@example.com")).id == user.id
    assert (await repo.get_by_id(user.id)).email == "repo-user@example.com"
    assert await repo.get_by_email("missing@example.com") is None


@pytest.mark.asyncio
async def test_link_repository_crud_and_stats(db_session):
    repo = LinkRepository(db_session)

    link = await repo.create(
        short_code="repo777",
        original_url="https://example.com/repo",
        owner_id=None,
        expires_at=None,
    )

    assert (await repo.get_by_short_code("repo777")).id == link.id
    assert (await repo.get_by_original_url("https://example.com/repo")).short_code == "repo777"

    updated = await repo.update_original_url("repo777", "https://example.com/repo-updated")
    assert updated.original_url == "https://example.com/repo-updated"

    await repo.increment_clicks("repo777")
    tracked = await repo.get_by_short_code("repo777")
    assert tracked.click_count == 1
    assert tracked.last_accessed_at is not None

    assert await repo.delete_by_short_code("repo777") is True
    assert await repo.get_by_short_code("repo777") is None


@pytest.mark.asyncio
async def test_link_repository_delete_expired_and_unused(db_session):
    repo = LinkRepository(db_session)
    now = datetime.now(timezone.utc)

    await repo.create(
        short_code="expired77",
        original_url="https://example.com/expired",
        owner_id=None,
        expires_at=now - timedelta(days=1),
    )

    fresh_link = await repo.create(
        short_code="unused77",
        original_url="https://example.com/unused",
        owner_id=None,
        expires_at=None,
    )
    fresh_link.created_at = now - timedelta(days=40)

    recent_link = await repo.create(
        short_code="recent77",
        original_url="https://example.com/recent",
        owner_id=None,
        expires_at=None,
    )
    recent_link.last_accessed_at = now - timedelta(days=35)

    active_link = await repo.create(
        short_code="active77",
        original_url="https://example.com/active",
        owner_id=None,
        expires_at=None,
    )
    active_link.created_at = now

    await db_session.merge(fresh_link)
    await db_session.merge(recent_link)
    await db_session.merge(active_link)
    await db_session.commit()

    assert await repo.delete_expired() == 1
    assert await repo.delete_unused(30) == 2

    remaining = await repo.get_by_short_code("active77")
    assert remaining is not None
    assert await repo.get_by_short_code("expired77") is None


@pytest.mark.asyncio
async def test_link_repository_prefers_newest_original_url_match(db_session):
    repo = LinkRepository(db_session)

    first = await repo.create(
        short_code="first77",
        original_url="https://example.com/same",
        owner_id=None,
        expires_at=None,
    )
    second = await repo.create(
        short_code="second77",
        original_url="https://example.com/same",
        owner_id=None,
        expires_at=None,
    )
    second.created_at = first.created_at + timedelta(seconds=5)
    await db_session.merge(second)
    await db_session.commit()

    latest = await repo.get_by_original_url("https://example.com/same")

    assert latest.short_code == "second77"
    assert isinstance(latest, Link)
