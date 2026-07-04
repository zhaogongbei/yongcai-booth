from datetime import datetime, timedelta, timezone

from httpx import AsyncClient

from app.api.v1 import share_settings as share_settings_api


class FakeEmailService:
    def __init__(self):
        self.calls: list[dict] = []

    async def send_photo_email(self, **kwargs) -> bool:
        self.calls.append(kwargs)
        return True


async def _create_event(authenticated_client: AsyncClient, slug: str, settings: dict | None = None) -> str:
    team_response = await authenticated_client.post(
        "/api/v1/teams",
        json={"name": f"Share Settings {slug}", "slug": slug},
    )
    assert team_response.status_code == 201
    team_id = team_response.json()["id"]

    start_date = datetime.now(timezone.utc)
    event_response = await authenticated_client.post(
        "/api/v1/events",
        json={
            "team_id": team_id,
            "name": f"Share Settings Event {slug}",
            "start_date": start_date.isoformat(),
            "end_date": (start_date + timedelta(hours=2)).isoformat(),
            "settings": settings,
        },
    )
    assert event_response.status_code == 201
    return event_response.json()["id"]


async def test_share_settings_returns_whatsapp_number(authenticated_client: AsyncClient):
    event_id = await _create_event(authenticated_client, "share-settings-default")

    response = await authenticated_client.get(f"/api/v1/settings/sharing/{event_id}")

    assert response.status_code == 200
    data = response.json()
    assert "whatsapp_number" in data
    assert "whatssapp_number" not in data


async def test_share_settings_normalizes_legacy_whatsapp_typo(authenticated_client: AsyncClient):
    event_id = await _create_event(
        authenticated_client,
        "share-settings-legacy",
        settings={"sharing": {"whatssapp_number": "+15551234567"}},
    )

    response = await authenticated_client.get(f"/api/v1/settings/sharing/{event_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["whatsapp_number"] == "+15551234567"
    assert "whatssapp_number" not in data


async def test_update_share_settings_accepts_canonical_whatsapp_number(
    authenticated_client: AsyncClient,
):
    event_id = await _create_event(authenticated_client, "share-settings-update")

    response = await authenticated_client.put(
        f"/api/v1/settings/sharing/{event_id}",
        json={"whatsapp_number": "+8613800138000"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["whatsapp_number"] == "+8613800138000"
    assert "whatssapp_number" not in data


async def test_test_email_without_photo_urls_does_not_use_placeholder(
    authenticated_client: AsyncClient,
    monkeypatch,
):
    event_id = await _create_event(authenticated_client, "share-settings-email-test")
    fake_email_service = FakeEmailService()
    monkeypatch.setattr(share_settings_api, "email_service", fake_email_service)

    response = await authenticated_client.post(
        "/api/v1/shares/email/test",
        json={
            "to_email": "guest@example.com",
            "event_id": event_id,
            "share_url": "https://example.test/share/real",
        },
    )

    assert response.status_code == 200
    assert fake_email_service.calls[0]["photo_urls"] == []


async def test_test_email_requires_explicit_share_url(authenticated_client: AsyncClient):
    event_id = await _create_event(authenticated_client, "share-settings-email-no-url")

    response = await authenticated_client.post(
        "/api/v1/shares/email/test",
        json={"to_email": "guest@example.com", "event_id": event_id},
    )

    assert response.status_code == 422


async def test_test_sms_requires_explicit_share_url(authenticated_client: AsyncClient):
    event_id = await _create_event(authenticated_client, "share-settings-sms-no-url")

    response = await authenticated_client.post(
        "/api/v1/shares/sms/test",
        json={"to_phone": "13800138000", "event_id": event_id},
    )

    assert response.status_code == 422
