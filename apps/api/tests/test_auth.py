from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"] == {"status": "ok"}
    assert "request_id" in payload["meta"]


@pytest.mark.asyncio
async def test_readiness_and_version_endpoints(client) -> None:
    readiness_response = await client.get("/health/readiness")
    version_response = await client.get("/health/version")

    assert readiness_response.status_code == 200
    readiness_payload = readiness_response.json()
    assert readiness_payload["data"]["status"] == "ready"
    assert readiness_payload["data"]["database"] == "ok"
    assert readiness_payload["data"]["redis"] == "skipped"

    assert version_response.status_code == 200
    version_payload = version_response.json()
    assert version_payload["data"]["name"] == "career-pilot-api"
    assert version_payload["data"]["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_auth_flow_register_me_logout_and_login(client) -> None:
    register_response = await client.post(
        "/auth/register",
        json={
            "email": "alice@example.com",
            "password": "super-secret-123",
            "nickname": "Alice",
        },
    )

    assert register_response.status_code == 201
    register_payload = register_response.json()["data"]
    assert register_payload["user"]["email"] == "alice@example.com"
    assert register_payload["token_type"] == "bearer"

    access_token = register_payload["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    me_response = await client.get("/auth/me", headers=auth_headers)
    assert me_response.status_code == 200
    assert me_response.json()["data"]["nickname"] == "Alice"

    logout_response = await client.post("/auth/logout", headers=auth_headers)
    assert logout_response.status_code == 200
    assert logout_response.json()["data"]["message"] == "Logged out successfully"

    stale_token_response = await client.get("/auth/me", headers=auth_headers)
    assert stale_token_response.status_code == 401
    assert stale_token_response.json()["error"]["code"] == "AUTH_TOKEN_REVOKED"

    login_response = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "super-secret-123"},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()["data"]
    assert login_payload["user"]["email"] == "alice@example.com"


@pytest.mark.asyncio
async def test_duplicate_registration_and_invalid_login(client) -> None:
    payload = {
        "email": "duplicate@example.com",
        "password": "super-secret-123",
        "nickname": "Dupe",
    }

    first_response = await client.post("/auth/register", json=payload)
    duplicate_response = await client.post("/auth/register", json=payload)
    invalid_login_response = await client.post(
        "/auth/login",
        json={"email": payload["email"], "password": "wrong-password-123"},
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert invalid_login_response.status_code == 401
    assert duplicate_response.json()["error"]["code"] == "USER_ALREADY_EXISTS"
    assert invalid_login_response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
