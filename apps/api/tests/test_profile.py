from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_profile_defaults_and_update(client) -> None:
    register_response = await client.post(
        "/auth/register",
        json={
            "email": "profile@example.com",
            "password": "super-secret-123",
            "nickname": "求职者",
        },
    )
    assert register_response.status_code == 201

    access_token = register_response.json()["data"]["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    profile_response = await client.get("/profile/me", headers=auth_headers)
    assert profile_response.status_code == 200
    profile_payload = profile_response.json()["data"]
    assert profile_payload["email"] == "profile@example.com"
    assert profile_payload["nickname"] == "求职者"
    assert profile_payload["job_direction"] is None

    update_response = await client.put(
        "/profile/me",
        headers=auth_headers,
        json={
            "nickname": "阿泽",
            "job_direction": "数据分析",
            "target_city": "上海",
            "target_role": "数据分析师",
        },
    )
    assert update_response.status_code == 200
    updated_payload = update_response.json()["data"]
    assert updated_payload["nickname"] == "阿泽"
    assert updated_payload["job_direction"] == "数据分析"
    assert updated_payload["target_city"] == "上海"
    assert updated_payload["target_role"] == "数据分析师"

    me_response = await client.get("/auth/me", headers=auth_headers)
    assert me_response.status_code == 200
    assert me_response.json()["data"]["nickname"] == "阿泽"
