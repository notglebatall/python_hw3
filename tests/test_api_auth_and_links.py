from datetime import datetime, timedelta, timezone

import pytest


async def register_and_login(client, email: str, password: str = "secret123") -> str:
    register_response = await client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 200

    login_response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


@pytest.mark.asyncio
async def test_auth_register_login_duplicate_and_invalid_credentials(client):
    token = await register_and_login(client, "user1@example.com")
    assert token

    duplicate_response = await client.post(
        "/auth/register",
        json={"email": "user1@example.com", "password": "secret123"},
    )
    assert duplicate_response.status_code == 409

    invalid_login = await client.post(
        "/auth/login",
        json={"email": "user1@example.com", "password": "wrong"},
    )
    assert invalid_login.status_code == 401


@pytest.mark.asyncio
async def test_public_shorten_redirect_search_stats_and_root_routes(client):
    create_response = await client.post(
        "/shorten",
        json={"original_url": "https://example.com/public"},
    )

    assert create_response.status_code == 200
    payload = create_response.json()
    short_code = payload["short_code"]
    assert payload["short_url"].endswith(f"/{short_code}")

    info_response = await client.get(f"/links/{short_code}/info")
    assert info_response.status_code == 200
    assert info_response.json()["original_url"] == "https://example.com/public"

    search_response = await client.get(
        "/links/search",
        params={"original_url": "https://example.com/public"},
    )
    assert search_response.status_code == 200
    assert search_response.json()["short_code"] == short_code

    redirect_response = await client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_response.status_code == 307
    assert redirect_response.headers["location"] == "https://example.com/public"

    link_redirect_response = await client.get(f"/links/{short_code}", follow_redirects=False)
    assert link_redirect_response.status_code == 307
    assert link_redirect_response.headers["location"] == "https://example.com/public"

    stats_response = await client.get(f"/links/{short_code}/stats")
    assert stats_response.status_code == 200
    stats_payload = stats_response.json()
    assert stats_payload["click_count"] == 2
    assert stats_payload["last_accessed_at"] is not None


@pytest.mark.asyncio
async def test_authorized_link_crud_and_permissions(client):
    owner_token = await register_and_login(client, "owner@example.com")
    intruder_token = await register_and_login(client, "intruder@example.com")
    expires_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    create_response = await client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/private",
            "custom_alias": "owner77",
            "expires_at": expires_at,
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert create_response.status_code == 200
    assert create_response.json()["short_code"] == "owner77"

    forbidden_update = await client.put(
        "/links/owner77",
        json={"original_url": "https://example.com/hacked"},
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert forbidden_update.status_code == 403

    update_response = await client.put(
        "/links/owner77",
        json={"original_url": "https://example.com/updated"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["original_url"] == "https://example.com/updated"

    delete_without_auth = await client.delete("/links/owner77")
    assert delete_without_auth.status_code == 401

    delete_response = await client.delete(
        "/links/owner77",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json() == {"status": "deleted"}

    missing_info = await client.get("/links/owner77/info")
    assert missing_info.status_code == 404


@pytest.mark.asyncio
async def test_api_validation_and_error_paths(client):
    token = await register_and_login(client, "validator@example.com")

    invalid_url = await client.post("/shorten", json={"original_url": "not-a-url"})
    assert invalid_url.status_code == 422

    expired_create = await client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com/expired",
            "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert expired_create.status_code == 400

    missing_search = await client.get(
        "/links/search",
        params={"original_url": "https://example.com/unknown"},
    )
    assert missing_search.status_code == 404

    missing_redirect = await client.get("/unknown77", follow_redirects=False)
    assert missing_redirect.status_code == 404

    invalid_token = await client.post(
        "/links/shorten",
        json={"original_url": "https://example.com/test"},
        headers={"Authorization": "Bearer bad-token"},
    )
    assert invalid_token.status_code == 401
