from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _create_event(client: AsyncClient, slug: str) -> dict:
    team_response = await client.post(
        "/api/v1/teams",
        json={"name": f"Config Team {slug}", "slug": f"config-team-{slug}"},
    )
    assert team_response.status_code == 201

    event_response = await client.post(
        "/api/v1/events",
        json={
            "name": f"Config Event {slug}",
            "team_id": team_response.json()["id"],
            "start_date": "2026-07-01T10:00:00Z",
            "end_date": "2026-07-01T18:00:00Z",
        },
    )
    assert event_response.status_code == 201
    return event_response.json()


@pytest.mark.anyio
async def test_survey_config_can_update_after_default_get(
    authenticated_client: AsyncClient,
):
    event = await _create_event(authenticated_client, "survey")

    get_response = await authenticated_client.get(f"/api/v1/surveys/event/{event['id']}")
    assert get_response.status_code == 200

    update_response = await authenticated_client.put(
        f"/api/v1/surveys/event/{event['id']}",
        json={
            "enabled": True,
            "title": "Visitor Feedback",
            "questions": [
                {
                    "id": "q1",
                    "type": "text_short",
                    "text": "How was the experience?",
                    "required": True,
                    "options": [],
                    "order": 0,
                }
            ],
        },
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["enabled"] is True
    assert data["title"] == "Visitor Feedback"
    assert data["questions"][0]["id"] == "q1"


@pytest.mark.anyio
async def test_survey_config_update_requires_authentication(client: AsyncClient):
    response = await client.put(
        f"/api/v1/surveys/event/{uuid4()}",
        json={"enabled": True, "title": "Visitor Feedback", "questions": []},
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_disclaimer_config_can_update_after_default_get(
    authenticated_client: AsyncClient,
):
    event = await _create_event(authenticated_client, "disclaimer")

    get_response = await authenticated_client.get(f"/api/v1/disclaimers/event/{event['id']}")
    assert get_response.status_code == 200

    update_response = await authenticated_client.put(
        f"/api/v1/disclaimers/event/{event['id']}",
        json={
            "enabled": True,
            "title": "Event Terms",
            "text": "Please accept the event terms.",
            "require_signature": True,
        },
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["enabled"] is True
    assert data["title"] == "Event Terms"
    assert data["require_signature"] is True


@pytest.mark.anyio
async def test_disclaimer_config_update_requires_authentication(client: AsyncClient):
    response = await client.put(
        f"/api/v1/disclaimers/event/{uuid4()}",
        json={
            "enabled": True,
            "title": "Event Terms",
            "text": "Please accept the event terms.",
            "require_signature": True,
        },
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_survey_and_disclaimer_config_reject_non_member(
    authenticated_client: AsyncClient,
):
    event = await _create_event(authenticated_client, "config-non-member")

    other_user_data = {
        "email": "config-other@example.com",
        "password": "OtherPass123!@",
        "full_name": "Config Other",
    }
    await authenticated_client.post("/api/v1/auth/register", json=other_user_data)
    login_response = await authenticated_client.post(
        "/api/v1/auth/login",
        data={"username": other_user_data["email"], "password": other_user_data["password"]},
    )
    other_token = login_response.json()["access_token"]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {other_token}"},
    ) as other_client:
        survey_response = await other_client.put(
            f"/api/v1/surveys/event/{event['id']}",
            json={"enabled": True, "title": "Visitor Feedback", "questions": []},
        )
        disclaimer_response = await other_client.put(
            f"/api/v1/disclaimers/event/{event['id']}",
            json={
                "enabled": True,
                "title": "Event Terms",
                "text": "Please accept the event terms.",
                "require_signature": True,
            },
        )

    assert survey_response.status_code == 403
    assert disclaimer_response.status_code == 403


@pytest.mark.anyio
async def test_survey_export_without_config_returns_404(
    authenticated_client: AsyncClient,
):
    event = await _create_event(authenticated_client, "survey-export-missing")

    response = await authenticated_client.get(f"/api/v1/surveys/responses/export/{event['id']}")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "该事件没有调查配置"


@pytest.mark.anyio
async def test_survey_export_requires_authentication(client: AsyncClient):
    response = await client.get(f"/api/v1/surveys/responses/export/{uuid4()}")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_accepting_disclaimer_twice_returns_400(
    authenticated_client: AsyncClient,
):
    event = await _create_event(authenticated_client, "disclaimer-duplicate")
    get_response = await authenticated_client.get(f"/api/v1/disclaimers/event/{event['id']}")
    assert get_response.status_code == 200

    session_response = await authenticated_client.post(
        "/api/v1/photos/sessions",
        json={"event_id": event["id"]},
    )
    assert session_response.status_code == 201

    payload = {"event_id": event["id"], "session_id": session_response.json()["id"]}

    first_response = await authenticated_client.post("/api/v1/disclaimers/accept", json=payload)
    second_response = await authenticated_client.post("/api/v1/disclaimers/accept", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    assert second_response.json()["error"]["message"] == "已经接受过免责声明"


@pytest.mark.anyio
async def test_accepting_disclaimer_without_config_returns_404(
    authenticated_client: AsyncClient,
):
    event = await _create_event(authenticated_client, "disclaimer-missing")
    session_id = str(uuid4())

    response = await authenticated_client.post(
        "/api/v1/disclaimers/accept",
        json={"event_id": event["id"], "session_id": session_id},
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "免责声明不存在"


@pytest.mark.anyio
async def test_submit_survey_response_links_existing_survey(
    authenticated_client: AsyncClient,
):
    event = await _create_event(authenticated_client, "survey-submit")
    get_response = await authenticated_client.get(f"/api/v1/surveys/event/{event['id']}")
    assert get_response.status_code == 200

    session_response = await authenticated_client.post(
        "/api/v1/photos/sessions",
        json={"event_id": event["id"]},
    )
    assert session_response.status_code == 201

    response = await authenticated_client.post(
        "/api/v1/surveys/responses",
        json={
            "event_id": event["id"],
            "session_id": session_response.json()["id"],
            "answers": {"q1": "Great"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == event["id"]
    assert data["session_id"] == session_response.json()["id"]
    assert data["answers"] == {"q1": "Great"}


@pytest.mark.anyio
async def test_submit_survey_response_twice_returns_400(
    authenticated_client: AsyncClient,
):
    event = await _create_event(authenticated_client, "survey-duplicate")
    get_response = await authenticated_client.get(f"/api/v1/surveys/event/{event['id']}")
    assert get_response.status_code == 200

    session_response = await authenticated_client.post(
        "/api/v1/photos/sessions",
        json={"event_id": event["id"]},
    )
    assert session_response.status_code == 201

    payload = {
        "event_id": event["id"],
        "session_id": session_response.json()["id"],
        "answers": {"q1": "Great"},
    }

    first_response = await authenticated_client.post("/api/v1/surveys/responses", json=payload)
    second_response = await authenticated_client.post("/api/v1/surveys/responses", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    assert second_response.json()["error"]["message"] == "已经提交过调查回答"


@pytest.mark.anyio
async def test_submit_survey_response_without_config_returns_404(
    authenticated_client: AsyncClient,
):
    event = await _create_event(authenticated_client, "survey-missing")

    response = await authenticated_client.post(
        "/api/v1/surveys/responses",
        json={
            "event_id": event["id"],
            "session_id": str(uuid4()),
            "answers": {"q1": "Great"},
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "该事件没有调查配置"
