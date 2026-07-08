import socket
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.services import trigger_service as trigger_service_module


def _public_dns_result(hostname: str, port: int | None, *args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port or 443))]


async def _create_event(authenticated_client: AsyncClient, slug: str) -> str:
    team_response = await authenticated_client.post(
        "/api/v1/teams",
        json={"name": f"Trigger Team {slug}", "slug": f"trigger-team-{slug}"},
    )
    assert team_response.status_code == 201
    team_id = team_response.json()["id"]

    start = datetime.now(timezone.utc)
    event_response = await authenticated_client.post(
        "/api/v1/events",
        json={
            "team_id": team_id,
            "name": f"Trigger Event {slug}",
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(hours=2)).isoformat(),
        },
    )
    assert event_response.status_code == 201
    return event_response.json()["id"]


@pytest.mark.anyio
async def test_trigger_config_rejects_local_app_execution(
    authenticated_client: AsyncClient,
):
    event_id = await _create_event(authenticated_client, "reject-app-execute")

    response = await authenticated_client.put(
        f"/api/v1/triggers/{event_id}",
        json=[
            {
                "event_type": "session_start",
                "action_type": "app_execute",
                "target": "C:\\scripts\\flash.exe",
                "enabled": True,
            }
        ],
    )

    assert response.status_code == 400
    assert "HTTP callback" in response.json()["error"]["message"]


@pytest.mark.anyio
async def test_trigger_config_rejects_private_network_callback_without_deleting_existing(
    authenticated_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(trigger_service_module.socket, "getaddrinfo", _public_dns_result)
    event_id = await _create_event(authenticated_client, "reject-private-callback")

    create_response = await authenticated_client.put(
        f"/api/v1/triggers/{event_id}",
        json=[
            {
                "event_type": "session_start",
                "action_type": "http_callback",
                "target": "https://hooks.example.test/callback",
                "enabled": True,
                "payload_template": {},
                "timeout": 10,
                "retry": 3,
            }
        ],
    )
    assert create_response.status_code == 200
    existing_id = create_response.json()[0]["id"]

    invalid_response = await authenticated_client.put(
        f"/api/v1/triggers/{event_id}",
        json=[
            {
                "event_type": "session_start",
                "action_type": "http_callback",
                "target": "http://127.0.0.1:8000/internal",
                "enabled": True,
                "payload_template": {},
                "timeout": 10,
                "retry": 3,
            }
        ],
    )

    assert invalid_response.status_code == 400
    assert "private network" in invalid_response.json()["error"]["message"]

    list_response = await authenticated_client.get(f"/api/v1/triggers/{event_id}")
    assert list_response.status_code == 200
    assert [config["id"] for config in list_response.json()] == [existing_id]


@pytest.mark.anyio
async def test_trigger_test_rejects_localhost_callback(authenticated_client: AsyncClient):
    event_id = await _create_event(authenticated_client, "reject-localhost-test")

    response = await authenticated_client.post(
        "/api/v1/triggers/test",
        json={
            "event_id": event_id,
            "event_type": "session_start",
            "action_type": "http_callback",
            "target": "http://localhost:9999/test",
            "timeout": 1,
        },
    )

    assert response.status_code == 400
    assert "localhost" in response.json()["error"]["message"]
